class Bar:
    def __init__(
        self, value: float, label: str = "", max: float = 1.0, color: str | None = None
    ) -> None:
        self.value = value
        self.label = label
        self.max = max
        self.color = color

    def __str__(self) -> str:  # pragma: no cover - visual only
        width = 20
        filled = int(width * min(self.value, self.max) / self.max)
        bar = "#" * filled + "-" * (width - filled)
        return f"{self.label} [{bar}] {self.value:.0f}"
