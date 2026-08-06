from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from core.config import load_settings
from ingestion.crossref import fetch_source_records, load_raw_records, parse_crossref_payload


def sample_payload() -> dict:
    return {
        "status": "ok",
        "message": {
            "items": [
                {
                    "DOI": "10.1000/ABC.123",
                    "title": ["  Agentic <i>RAG</i> systems  "],
                    "abstract": "<jats:p>A &amp; B abstract.</jats:p>",
                    "author": [
                        {"given": "Ada", "family": "Lovelace"},
                        {"name": "Research Group"},
                    ],
                    "subject": ["Artificial Intelligence", "Retrieval"],
                    "published-online": {"date-parts": [[2025, 2, 3]]},
                    "indexed": {"date-time": "2025-02-04T10:20:30Z"},
                    "URL": "https://doi.org/10.1000/ABC.123",
                    "link": [
                        {
                            "URL": "https://example.test/paper.pdf",
                            "content-type": "application/pdf",
                        }
                    ],
                    "container-title": ["Journal of RAG"],
                    "publisher": "Example Publisher",
                },
                {"DOI": "10.1000/ABC.123", "title": ["Duplicate DOI"]},
                {"DOI": "", "title": ["Missing identifier"]},
                {"DOI": "10.1000/no-title", "title": []},
            ]
        },
    }


class CrossrefTests(unittest.TestCase):
    def test_parse_normalizes_and_filters(self) -> None:
        records = parse_crossref_payload(sample_payload())

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.paper_id, "10.1000/abc.123")
        self.assertEqual(record.title, "Agentic RAG systems")
        self.assertEqual(record.summary, "A & B abstract.")
        self.assertEqual(record.authors, ["Ada Lovelace", "Research Group"])
        self.assertEqual(record.categories, ["Artificial Intelligence", "Retrieval"])
        self.assertEqual(record.primary_category, "Artificial Intelligence")
        self.assertEqual(record.published, "2025-02-03")
        self.assertEqual(record.updated, "2025-02-04T10:20:30Z")
        self.assertEqual(record.pdf_url, "https://example.test/paper.pdf")

    def test_parse_rejects_wrong_envelope(self) -> None:
        with self.assertRaisesRegex(ValueError, r"message\.items"):
            parse_crossref_payload({"message": {}})

    def test_parse_uses_source_type_when_subject_is_missing(self) -> None:
        payload = {
            "message": {
                "items": [
                    {
                        "DOI": "10.1000/preprint",
                        "title": ["A preprint"],
                        "type": "posted-content",
                        "subtype": "preprint",
                    }
                ]
            }
        }

        record = parse_crossref_payload(payload)[0]
        self.assertEqual(record.categories, ["preprint"])
        self.assertEqual(record.primary_category, "preprint")

    def test_fetch_saves_response_before_records(self) -> None:
        with TemporaryDirectory() as directory:
            settings = load_settings(Path(directory))
            response = Mock(status_code=200, headers={})
            response.json.return_value = sample_payload()
            response.raise_for_status.return_value = None

            with patch("ingestion.crossref.requests.get", return_value=response) as request:
                records = fetch_source_records(settings)

            self.assertEqual(len(records), 1)
            saved_payload = json.loads(
                settings.paths.raw_api_response.read_text(encoding="utf-8")
            )
            self.assertEqual(saved_payload, sample_payload())
            saved_records = json.loads(
                settings.paths.raw_records_json.read_text(encoding="utf-8")
            )
            self.assertEqual(saved_records[0]["paper_id"], "10.1000/abc.123")
            self.assertEqual(
                request.call_args.kwargs["params"],
                {
                    "query": settings.source_query,
                    "filter": settings.source_filter,
                    "rows": settings.max_results,
                },
            )

    def test_fetch_retries_503_then_succeeds(self) -> None:
        with TemporaryDirectory() as directory:
            settings = load_settings(Path(directory))
            unavailable = Mock(status_code=503, headers={"Retry-After": "0"})
            success = Mock(status_code=200, headers={})
            success.json.return_value = sample_payload()
            success.raise_for_status.return_value = None

            with (
                patch(
                    "ingestion.crossref.requests.get",
                    side_effect=[unavailable, success],
                ) as request,
                patch("ingestion.crossref.time.sleep") as sleep,
            ):
                fetch_source_records(settings)

            self.assertEqual(request.call_count, 2)
            sleep.assert_called_once_with(0.0)

    def test_load_raw_records_round_trip(self) -> None:
        with TemporaryDirectory() as directory:
            settings = load_settings(Path(directory))
            response = Mock(status_code=200, headers={})
            response.json.return_value = sample_payload()
            response.raise_for_status.return_value = None
            with patch("ingestion.crossref.requests.get", return_value=response):
                expected = fetch_source_records(settings)

            self.assertEqual(load_raw_records(settings.paths.raw_records_json), expected)

    def test_load_reports_missing_field(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "records.json"
            path.write_text(json.dumps([{"paper_id": "10.1/test"}]), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing fields"):
                load_raw_records(path)


if __name__ == "__main__":
    unittest.main()
