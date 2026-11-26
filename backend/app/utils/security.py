"""Security helpers: input sanitization and ObjectId conversion."""

import re
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status

CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(value: str, max_length: int = 2000) -> str:
    """Strip unsafe control characters and bound text length."""
    cleaned = CONTROL_CHARS_RE.sub("", value).strip()
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned


def parse_object_id(id_str: str) -> Any:
    """Validate and return a string/ObjectId identifier."""
    if not id_str or not isinstance(id_str, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resource identifier.",
        )
    if ObjectId.is_valid(id_str):
        return ObjectId(id_str)
    # In dev in-memory mode IDs may also be 24-hex ObjectId strings; reject malformed IDs
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Malformed resource identifier.",
    )


def serialize_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert MongoDB ObjectId fields into JSON-safe strings."""
    if doc is None:
        return None
    out: dict[str, Any] = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, dict):
            out[k] = serialize_doc(v)
        elif isinstance(v, list):
            out[k] = [
                serialize_doc(item) if isinstance(item, dict) else (str(item) if isinstance(item, ObjectId) else item)
                for item in v
            ]
        else:
            out[k] = v
    if "_id" in out and "id" not in out:
        out["id"] = out["_id"]
    return out
