from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from email.utils import parsedate_to_datetime
import html
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


CROSSREF_API_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_FETCH_ATTEMPTS = 4
REQUEST_TIMEOUT_SECONDS = (10, 60)
USER_AGENT = "day10-data-observability-lab/0.1 (Crossref metadata exercise)"


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        value = next((item for item in value if item), "")
    return normalize_whitespace(str(value)) if value is not None else ""


def _plain_text(value: Any) -> str:
    """Convert Crossref's JATS/XML snippets into readable plain text."""
    text = _first_text(value)
    text = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(html.unescape(text))


def _date_from_parts(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    parts = value.get("date-parts")
    if not isinstance(parts, list) or not parts or not isinstance(parts[0], list):
        return ""
    try:
        numbers = [int(part) for part in parts[0][:3]]
    except (TypeError, ValueError):
        return ""
    if not numbers:
        return ""
    year = numbers[0]
    month = numbers[1] if len(numbers) > 1 else 1
    day = numbers[2] if len(numbers) > 2 else 1
    if year < 1 or not 1 <= month <= 12 or not 1 <= day <= 31:
        return ""
    return f"{year:04d}-{month:02d}-{day:02d}"


def _first_date(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, dict):
            date_time = _first_text(value.get("date-time"))
            if date_time:
                return date_time
            parsed_parts = _date_from_parts(value)
            if parsed_parts:
                return parsed_parts
    return ""


def _author_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for author in value:
        if not isinstance(author, dict):
            continue
        literal = _plain_text(author.get("name"))
        given = _plain_text(author.get("given"))
        family = _plain_text(author.get("family"))
        name = literal or normalize_whitespace(" ".join(part for part in (given, family) if part))
        if name and name not in names:
            names.append(name)
    return names


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        cleaned = _plain_text(item)
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _pdf_url(item: dict[str, Any]) -> str:
    links = item.get("link")
    if not isinstance(links, list):
        return ""
    for link in links:
        if not isinstance(link, dict):
            continue
        content_type = _first_text(link.get("content-type")).lower()
        url = _first_text(link.get("URL"))
        if url and (content_type == "application/pdf" or url.lower().endswith(".pdf")):
            return url
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref REST payload into stable, pipeline-ready records.

    DOI is the source's persistent identifier, so its normalized lower-case value
    is used as ``paper_id``. Items without a DOI or title are deliberately skipped;
    downstream cleaning must never have to invent either field.
    """
    if not isinstance(payload, dict):
        raise TypeError("Crossref payload must be a JSON object.")
    message = payload.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("items"), list):
        raise ValueError("Crossref payload must contain message.items as a list.")

    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in message["items"]:
        if not isinstance(item, dict):
            continue
        doi = _first_text(item.get("DOI")).lower()
        title = _plain_text(item.get("title"))
        if not doi or not title or doi in seen_ids:
            continue

        categories = _string_list(item.get("subject"))
        if not categories:
            # Crossref often omits subjects even when the rest of the metadata is
            # complete. ``type`` is still source-provided taxonomy and gives the
            # cleaning/evaluation owners an auditable fallback category.
            source_type = _plain_text(item.get("subtype")) or _plain_text(item.get("type"))
            categories = [source_type] if source_type else []
        published = _first_date(
            item,
            ("published-print", "published-online", "published", "issued", "created"),
        )
        updated = _first_date(item, ("indexed", "deposited", "created"))
        abs_url = _first_text(item.get("URL")) or f"https://doi.org/{doi}"
        container = _first_text(item.get("container-title"))
        publisher = _plain_text(item.get("publisher"))

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=_plain_text(item.get("abstract")),
                authors=_author_names(item.get("author")),
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=_pdf_url(item),
                comment="; ".join(part for part in (container, publisher) if part),
            )
        )
        seen_ids.add(doi)
    return records


def _retry_delay_seconds(response: requests.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After", "").strip()
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), 60.0)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                return min(max(retry_at.timestamp() - time.time(), 0.0), 60.0)
            except (TypeError, ValueError, OverflowError):
                pass
    return float(2 ** (attempt - 1))


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref data, preserving the response before parsing any records."""
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    response: requests.Response | None = None
    last_error: requests.RequestException | None = None

    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        try:
            response = requests.get(
                CROSSREF_API_URL,
                params=params,
                headers={"Accept": "application/json", "User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            last_error = exc
            if attempt == MAX_FETCH_ATTEMPTS:
                raise RuntimeError(
                    f"Crossref request failed after {MAX_FETCH_ATTEMPTS} attempts."
                ) from exc
            time.sleep(float(2 ** (attempt - 1)))
            continue

        if response.status_code not in RETRYABLE_STATUS_CODES:
            break
        if attempt == MAX_FETCH_ATTEMPTS:
            response.raise_for_status()
        time.sleep(_retry_delay_seconds(response, attempt))

    if response is None:
        raise RuntimeError("Crossref request produced no response.") from last_error
    response.raise_for_status()
    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        raise ValueError("Crossref returned a non-JSON response.") from exc
    if not isinstance(payload, dict):
        raise ValueError("Crossref response must be a JSON object.")

    # Raw source evidence is persisted before parsing, even when the schema is bad.
    write_json(settings.paths.raw_api_response, payload)
    records = parse_crossref_payload(payload)
    if not records:
        raise ValueError("Crossref response contained no usable records with DOI and title.")
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def _record_from_json(value: Any, index: int) -> PaperRecord:
    if not isinstance(value, dict):
        raise ValueError(f"Raw record at index {index} must be a JSON object.")
    required_fields = {field.name for field in fields(PaperRecord)}
    missing = required_fields.difference(value)
    if missing:
        raise ValueError(
            f"Raw record at index {index} is missing fields: {', '.join(sorted(missing))}."
        )
    paper_id = _first_text(value["paper_id"]).lower()
    title = _plain_text(value["title"])
    if not paper_id or not title:
        raise ValueError(f"Raw record at index {index} has an empty paper_id or title.")
    return PaperRecord(
        paper_id=paper_id,
        title=title,
        summary=_plain_text(value["summary"]),
        authors=_string_list(value["authors"]),
        categories=_string_list(value["categories"]),
        primary_category=_plain_text(value["primary_category"]),
        published=_first_text(value["published"]),
        updated=_first_text(value["updated"]),
        abs_url=_first_text(value["abs_url"]),
        pdf_url=_first_text(value["pdf_url"]),
        comment=_plain_text(value["comment"]),
    )


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load and validate the parsed-record snapshot used by later checkpoints."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Raw records file must contain a JSON list: {path}")
    records = [_record_from_json(value, index) for index, value in enumerate(payload)]
    duplicate_ids = sorted(
        paper_id
        for paper_id in {record.paper_id for record in records}
        if sum(record.paper_id == paper_id for record in records) > 1
    )
    if duplicate_ids:
        raise ValueError(f"Raw records contain duplicate paper_id values: {duplicate_ids}")
    return records
