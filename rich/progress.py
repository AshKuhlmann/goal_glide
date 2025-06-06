class SpinnerColumn:
    pass


class TextColumn:
    def __init__(self, text: str) -> None:
        self.text = text


class Progress:
    def __init__(self, *columns: object) -> None:
        self.columns = columns

    def __enter__(self) -> "Progress":
        return self

    def __exit__(
        self, exc_type: type | None, exc: BaseException | None, tb: object | None
    ) -> None:  # pragma: no cover
        pass

    def add_task(self, description: str, total: int | None = None) -> None:
        print(description)
