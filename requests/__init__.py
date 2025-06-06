from typing import Any, List


class RequestException(Exception):
    pass


class Response:
    ok = False

    def json(self) -> List[Any]:  # pragma: no cover - not used
        return []


def get(*_args: Any, **_kwargs: Any) -> Response:  # pragma: no cover - network disabled
    raise RequestException("network disabled")
