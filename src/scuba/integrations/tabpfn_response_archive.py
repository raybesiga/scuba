"""Private, complete prediction-response bodies with credential redaction.

Unlike filtered diagnostics, unfamiliar JSON fields and values are retained.
This archive is local evidence, never a report or a byte-exact HTTP transcript.
"""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

ARCHIVE_NAME = "prediction_response.private.json"
SECRET_KEYS = {
    "authorization",
    "proxyauthorization",
    "cookie",
    "setcookie",
    "password",
    "passwd",
    "secret",
    "clientsecret",
    "credentials",
    "token",
    "accesstoken",
    "refreshtoken",
    "idtoken",
    "apikey",
    "privatekey",
}


def archive_response(directory, response, *, secrets=()):
    """Persist a complete received body before status/JSON/model acceptance.

    Only credential redaction changes content; no allowlist, preview limit or
    list truncation is applied. HTTP request headers are never captured.
    """
    replacements = []
    for secret in secrets:
        if secret:
            replacements.extend((secret, quote(secret, safe=""), quote(quote(secret, safe=""))))
    redactions = 0

    def clean_text(text):
        nonlocal redactions
        for secret in sorted(set(replacements), key=len, reverse=True):
            redactions += text.count(secret)
            text = text.replace(secret, "[REDACTED]")
        for pattern in (
            r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+",
            r"\b(?:ghp_|sk-proj-|AKIA)[A-Za-z0-9_-]+",
            r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
            r"""(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*[^\s,;"'<>]+""",
        ):
            text, count = re.subn(pattern, "[REDACTED]", text)
            redactions += count

        def clean_url(match):
            nonlocal redactions
            original = match[0]
            try:
                parts = urlsplit(original)
                cleaned = urlunsplit(
                    (parts.scheme, parts.netloc.rsplit("@", 1)[-1], parts.path, "", "")
                )
            except ValueError:
                cleaned = "[REDACTED_URL]"
            redactions += int(cleaned != original)
            return cleaned

        return re.sub(r"""https?://[^\s"'<>]+""", clean_url, text)

    def clean(value):
        nonlocal redactions
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                name = clean_text(key)
                if re.sub(r"[^a-z0-9]", "", key.lower()) in SECRET_KEYS:
                    redactions += 1
                    result[name] = "[REDACTED]"
                else:
                    result[name] = clean(item)
            return result
        if isinstance(value, list):
            return [clean(item) for item in value]
        return clean_text(value) if isinstance(value, str) else value

    def reject_constant(value):
        raise ValueError("non-standard JSON constant")

    try:
        body = clean(json.loads(response.content, parse_constant=reject_constant))
        body_format = "json"
    except (ValueError, UnicodeError):
        body = clean_text(response.text)
        body_format = "text"
    record = {
        "schema": "scuba.private-prediction-response/v1",
        "http_status": response.status_code,
        "body_format": body_format,
        "raw_byte_exact": False,
        "redactions": redactions,
        "redaction_policy": "credentials and URL userinfo/query/fragment removed; no field filtering",
        "body": body,
    }
    payload = (json.dumps(record, ensure_ascii=True, allow_nan=False) + "\n").encode()
    path = Path(directory) / ARCHIVE_NAME
    # Publish atomically without overwriting any prior evidence; private from creation.
    with tempfile.NamedTemporaryFile(dir=directory, prefix=".response-", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
            os.link(temporary, path)
        finally:
            temporary.unlink()
    return {
        "path": path.name,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "http_status": response.status_code,
        "body_format": body_format,
        "redactions": redactions,
        "raw_byte_exact": False,
    }
