import re

from ..exceptions import InvalidTagError

_TAG_RE = re.compile(r"^[a-z0-9][a-z0-9-_]{0,29}$")


def validate_tag(tag: str) -> str:
    if not _TAG_RE.fullmatch(tag):
        raise InvalidTagError(f"Invalid tag '{tag}'. Tags must match {_TAG_RE.pattern}")
    return tag.lower()
