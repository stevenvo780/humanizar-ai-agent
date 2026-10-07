"""Accent- and case-insensitive text normalization shared by tools and the agent."""

import unicodedata


def normalized(text: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(char)
    )
