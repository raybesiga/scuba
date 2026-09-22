"""Bounded, typed diagnostic fields; capture does not confer model acceptance."""

import math
import re
from urllib.parse import unquote, urlsplit, urlunsplit

SENSITIVE = re.compile(
    r"(?i)\b(?:bearer|authorization|password|passwd|secret|token|api[_-]?key|private[_-]?key)\b"
    r"|\b(?:ghp_|sk-proj-|AKIA)[A-Za-z0-9_-]+"
    r"|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
)


def diagnostic_value(value, *, present=True, secrets=(), depth=0):
    """Retain identifier-like text, not arbitrary prose or unknown object contents."""
    result = {
        "present": present,
        "type": type(value).__name__ if present else "missing",
        "status": "retained" if present else "missing",
        "value": None,
        "transformations": [],
    }
    if not present or value is None:
        return result
    if isinstance(value, str):
        result["original_length"] = len(value)
        if len(value) > 4096:
            return {**result, "status": "omitted", "reason": "string_exceeds_4096_characters"}
        decoded = unquote(unquote(value))
        if any(secret and (secret in value or secret in decoded) for secret in secrets):
            return {**result, "status": "redacted", "reason": "known_credential"}
        if any(ord(c) < 32 or ord(c) == 127 for c in decoded):
            return {**result, "status": "omitted", "reason": "control_characters"}
        try:
            parts = urlsplit(decoded)
            authority = parts.netloc
            if parts.username is not None or parts.password is not None:
                authority = authority.rsplit("@", 1)[-1]
                result["transformations"].append("removed_url_userinfo")
            if parts.query:
                result["transformations"].append("removed_query")
            if parts.fragment:
                result["transformations"].append("removed_fragment")
            clean = urlunsplit((parts.scheme, authority, parts.path, "", ""))
            if clean != decoded and not result["transformations"]:
                result["transformations"].append("uri_normalized")
        except ValueError:
            return {**result, "status": "omitted", "reason": "malformed_uri"}
        if decoded != value:
            result["transformations"].insert(0, "percent_decoded_twice")
        if SENSITIVE.search(clean):
            return {**result, "status": "redacted", "reason": "credential_marker"}
        if not clean or not re.fullmatch(r"[A-Za-z0-9_./:+@%~\\=\[\]-]+", clean):
            return {**result, "status": "omitted", "reason": "non_identifier_text"}
        result["value"] = clean[:512]
        if len(clean) > 512:
            result["transformations"].append("truncated_to_512_characters")
        if result["transformations"]:
            result["status"] = "transformed"
    elif type(value) in (int, float, bool):
        if isinstance(value, float) and not math.isfinite(value):
            return {**result, "status": "omitted", "reason": "non_finite_number"}
        # Numeric metadata should also have a bounded representation.
        if isinstance(value, int) and value.bit_length() > 64:
            return {**result, "status": "omitted", "reason": "oversize_integer"}
        result["value"] = value
    elif isinstance(value, list):
        result["original_length"] = len(value)
        if depth >= 2:
            return {**result, "status": "omitted", "reason": "nesting_limit"}
        result["value"] = [
            diagnostic_value(item, secrets=secrets, depth=depth + 1) for item in value[:8]
        ]
        if len(value) > 8:
            result.update(status="transformed", transformations=["truncated_to_8_items"])
    else:
        result.update(status="omitted", reason="unexpected_object_contents")
    return result


def reported_fields(mapping, names, *, secrets=()):
    mapping = mapping if isinstance(mapping, dict) else {}
    return {
        name: diagnostic_value(mapping.get(name), present=name in mapping, secrets=secrets)
        for name in names
    }


def field_inventory(mapping, *, secrets=()):
    """Record field presence/types without retaining unknown response values.

    This is a bounded inventory, not a raw response archive. Keep counts of
    omitted entries so absence from this inventory cannot imply server absence.
    """
    result = {"type": type(mapping).__name__, "fields": []}
    if not isinstance(mapping, dict):
        return result
    result["field_count"] = len(mapping)
    result["omitted_fields"] = 0
    for index, (name, value) in enumerate(mapping.items()):
        if index >= 128:
            result["omitted_fields"] += len(mapping) - index
            break
        safe = diagnostic_value(name, secrets=secrets)
        if (
            safe["status"] != "retained"
            or not isinstance(name, str)
            or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", name)
        ):
            result["omitted_fields"] += 1
            continue
        entry = {"name": name, "type": type(value).__name__}
        if isinstance(value, (dict, list)):
            entry["length"] = len(value)
        result["fields"].append(entry)
    return result
