"""Explicit local secret loading for API commands only."""

import os
from pathlib import Path


class MissingToken(ValueError):
    """No usable TabPFN token was provided."""


def tabpfn_token(env_file: Path = Path(".env")) -> str:
    # Never search parent directories or interpolate other secret variables.
    token = os.environ.get("TABPFN_TOKEN")
    if token is None:
        from dotenv import dotenv_values

        token = dotenv_values(env_file, interpolate=False).get("TABPFN_TOKEN")
    if not isinstance(token, str) or not token.strip():
        raise MissingToken("Set TABPFN_TOKEN in the environment or local .env; no key was loaded.")
    if any(character.isspace() for character in token):
        raise MissingToken("TABPFN_TOKEN must not contain whitespace.")
    return token
