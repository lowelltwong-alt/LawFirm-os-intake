from __future__ import annotations

from typing import NamedTuple


class PNum(NamedTuple):
    value: float
    sources: frozenset[str]

    def add(self, other: "PNum") -> "PNum":
        return PNum(self.value + other.value, self.sources | other.sources)

    def multiply(self, factor: float, source: str | None = None) -> "PNum":
        sources = self.sources | ({source} if source else set())
        return PNum(self.value * factor, frozenset(sources))


def assert_priced_sources(values: list[PNum]) -> None:
    for value in values:
        if not value.sources or "invented" in value.sources:
            raise ValueError("priced provenance values require non-invented sources")
