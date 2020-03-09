import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

__all__ = ["apply_single_file"]


def apply_single_file(contents: str, patch: str) -> str:
    """
    Apply a clean patch, no fuzz, no rejects.
    """

    lines = contents.splitlines(True)
    hunks = _split_hunks(patch.splitlines(True)[2:])
    return "".join(_apply_hunks(lines, hunks))


POSITION_LINE_RE = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PatchException(Exception):
    pass


def _parse_position_line(position_line: str) -> List[int]:
    """Given an `@@` line, return the four numbers within."""
    match = POSITION_LINE_RE.match(position_line)
    if not match:
        raise PatchException(f"Position line {position_line!r} failed to parse")
    return [
        int(match.group(1)),
        int(match.group(2) or "1"),
        int(match.group(3)),
        int(match.group(4) or "1"),
    ]


# TODO store the offsets too, to make filtering easier
@dataclass
class Hunk:
    position: Optional[List[int]] = None
    lines: List[str] = field(default_factory=list)


def _split_hunks(diff_lines: Sequence[str]) -> List[Hunk]:
    """
    Splits unified diff lines (after the file header) into hunks.
    """
    hunks: List[Hunk] = []
    hunk: Optional[Hunk] = None

    for line in diff_lines:
        if line.startswith("@@"):
            # Start a new hunk
            if hunk:
                hunks.append(hunk)
            hunk = Hunk(_parse_position_line(line))
        # There should not be '---' or '+++' lines here, they are stripped off
        # in apply_single_file.
        if not hunk:
            raise PatchException("Lines without hunk header at {line!r}")
        hunk.lines.append(line)

    if hunk and hunk.lines:
        hunks.append(hunk)

    return hunks


def _apply_hunks(lines: List[str], hunks: List[Hunk]) -> List[str]:
    work = lines[:]
    file_offset = 0  # accumulation of delta
    for hunk in hunks:
        assert hunk.position is not None
        pos = hunk.position[:]

        # If length is zero, this is a no-context deletion and per
        # https://www.artima.com/weblogs/viewpost.jsp?thread=164293 the numbers
        # are off by one from being actual line numbers. :/
        if pos[3] == 0:
            pos[2] += 1
        if pos[1] == 0:
            pos[0] += 1

        cur_line = pos[0] + file_offset - 1
        # Meld "No newline at end of file" up a line
        tmp = hunk.lines[:]
        for i in range(len(tmp) - 1, 0, -1):
            if tmp[i].startswith("\\ No newline"):
                del tmp[i]
                # strips newline (including dos newlines, although we don't
                # produce a those in moreorless.unified_diff)
                if tmp[i - 1].endswith("\r\n"):
                    tmp[i - 1] = tmp[i - 1][:-2]
                else:
                    tmp[i - 1] = tmp[i - 1][:-1]

        for line in tmp[1:]:
            if line.startswith("-"):
                if line[1:] != work[cur_line]:
                    raise PatchException(f"DELETE fail at {cur_line}")
                del work[cur_line]
            elif line.startswith("+"):
                work.insert(cur_line, line[1:])
                cur_line += 1
            elif line.startswith(" "):
                if line[1:] != work[cur_line]:
                    raise PatchException(f"EQUAL fail at {cur_line}")
                cur_line += 1
            elif line.startswith("?"):  # pragma: no cover
                pass  # human readable line
            else:
                raise PatchException(f"Unknown line {line!r} at {cur_line}")
        file_offset += pos[3] - pos[1]

    return work
