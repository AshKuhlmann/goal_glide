class Tree:
    def __init__(self, label: str) -> None:
        self.label = label
        self.children: list[tuple[str, "Tree"]] = []

    def add(self, label: str) -> "Tree":
        child = Tree(label)
        self.children.append((label, child))
        return child

    def __str__(self) -> str:  # pragma: no cover - visual only
        lines = [self.label]
        for i, (label, child) in enumerate(self.children):
            self._render_child(lines, label, child, "", i == len(self.children) - 1)
        return "\n".join(lines)

    def _render_child(
        self, out: list[str], label: str, node: "Tree", prefix: str, last: bool
    ) -> None:
        connector = "└─ " if last else "├─ "
        out.append(prefix + connector + label)
        child_prefix = prefix + ("   " if last else "│  ")
        for i, (lbl, child) in enumerate(node.children):
            self._render_child(
                out, lbl, child, child_prefix, i == len(node.children) - 1
            )
