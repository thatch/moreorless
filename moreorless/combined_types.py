from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass
class Line:
    # By convention, the `common` entry comes last (and typically isn't output
    # explicitly)
    contributions: Sequence[int]
    line: str

    @property
    def is_context(self) -> bool:
        return sum(self.contributions) == len(self.contributions)

    # @property
    # def is_common_only(self) -> bool:
    #     return self.contributions[-1] and sum(self.contributions) == 1

    def to_buf(self, buf: List[str], is_merge: bool) -> None:
        merge_mult = 1 if is_merge else -1

        if self.is_context:
            buf.append(" " * (len(self.contributions) - 1) + self.line)
        else:
            d = {0: " ", 1: "+", -1: "-"}
            for c in self.contributions[:-1]:
                buf.append(d[(self.contributions[-1] - c) * merge_mult])
            buf.append(self.line)
        if not self.line.endswith("\n"):
            buf.append("\n")
            buf.append("\\ no newline at end of file")

    def to_str(self, is_merge: bool) -> str:
        buf: List[str] = []
        self.to_buf(buf, is_merge)
        return "".join(buf)


@dataclass
class Hunk:
    lines: List[Line]
    starts: Sequence[int]
    lengths: Sequence[int] = ()

    def __post_init__(self) -> None:
        self.lengths = tuple([sum(col) for col in self._column_counts])

    @property
    def is_entirely_context(self) -> bool:
        return all(el.is_context for el in self.lines)

    @property
    def _column_counts(self) -> Iterable[Iterable[int]]:
        return zip(*[line.contributions for line in self.lines])

    def header(self, merge_mode: bool) -> str:
        buf: List[str] = []
        buf.append("@" * len(self.starts) + " ")
        if merge_mode:
            prefixes = ["-"] * (len(self.starts) - 1) + ["+"]
        else:
            prefixes = ["-"] + ["+"] * (len(self.starts) - 1)

        positions = list(zip(self.starts, self.lengths))
        if not merge_mode:
            positions.insert(0, positions.pop(-1))

        for p, x in zip(prefixes, positions):
            buf.append(f"{p}{x[0]},{x[1]} ")

        buf.append("@" * len(self.starts))
        buf.append("\n")
        return "".join(buf)

    def to_buf(self, buf: List[str], merge_mode: bool) -> None:
        if self.is_entirely_context:
            return

        buf.append(self.header(merge_mode))
        # print("S", self.starts)
        # print("L", self.lengths)
        for line in self.lines:
            # print("LINE", line.contributions)
            line.to_buf(buf, merge_mode)

    def to_str(self, is_merge: bool) -> str:
        buf: List[str] = []
        self.to_buf(buf, is_merge)
        return "".join(buf)


@dataclass
class Snip:
    count: int
