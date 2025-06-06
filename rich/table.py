class Table:
    def __init__(self, title: str | None = None):
        self.title = title
        self.columns: list[str] = []
        self.rows: list[list[str]] = []

    def add_column(self, header: str) -> None:
        self.columns.append(header)

    def add_row(self, *values: str) -> None:
        self.rows.append(list(values))

    def __str__(self) -> str:  # pragma: no cover
        lines = []
        if self.title:
            lines.append(self.title)
        header = " | ".join(self.columns)
        lines.append(header)
        lines.append("-" * len(header))
        for row in self.rows:
            lines.append(" | ".join(row))
        return "\n".join(lines)
