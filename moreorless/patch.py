import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

__all__ = ["apply_single_file", "PatchException"]

LOG = logging.getLogger(__name__)


def apply_single_file(contents: str, patch: str, allow_offsets: bool = True) -> str:
    """
    Apply a clean patch, no fuzz, no rejects.
    """

    lines = contents.splitlines(True)
    hunks = _split_hunks(patch.splitlines(True)[2:])
    return "".join(_apply_hunks(lines, hunks, allow_offsets))


POSITION_LINE_RE = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PatchException(Exception):
    pass


class ContextException(PatchException):
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
            raise PatchException(f"Lines without hunk header at {line!r}")
        hunk.lines.append(line)

    if hunk and hunk.lines:
        hunks.append(hunk)

    return hunks


def _apply_hunks(lines: List[str], hunks: List[Hunk], allow_offsets: bool) -> List[str]:
    work = lines[:]
    file_offset = 0  # accumulation of delta
    prev_line = 0
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
        if allow_offsets:
            tmp2 = [t[1:] for t in tmp if t[0] in (" ", "-")]
            # TODO if hunks overlap, this checks against the already-modified
            # one for context, which seems wrong.  Unmodified file is something
            # like _context_match(lines, tmp2, ..., prev_line+file_offset)-file_offset

            # On a proper patch this always takes in cur_line and returns cur_line
            new_line = _context_match(work, tmp2, prev_line, len(work), cur_line)
            if new_line is None:
                raise PatchException(f"Failed to apply with offset at {cur_line}")
            if cur_line != new_line:
                LOG.info(f"Offset {new_line - cur_line}")
                cur_line = new_line

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
        prev_line = cur_line

    return work


def _context_match(
    file_lines: List[str],
    context_lines: List[str],
    range_start: int,
    range_end: int,
    start: int,
) -> Optional[int]:
    """
    Finds an offset within file_lines to match context.

    Returns i such that:
    * file_lines[i:i+len] == context_lines
    * i >= range_start
    * i <= range_end - len
    * minimizes abs(i-start)
    * minimizes i if there's a tie on abs
    """
    cl = len(context_lines)
    if not range_start >= 0:
        raise ContextException("context error 1: negative range_start")
    if not range_end >= range_start:
        raise ContextException("context error 2: flipped range")
    if not range_end <= len(file_lines):
        raise ContextException("context error 3: past end")
    if not start >= range_start:
        raise ContextException("context error 4: start before range_start")
    if not start <= range_end - cl:
        raise ContextException("context error 5: start past range_end")

    for di in range(0, max(start - range_start + 1, range_end - start - cl + 1)):
        t1 = start - di
        t2 = start + di
        if t1 >= range_start:
            if all(context_lines[j] == file_lines[t1 + j] for j in range(cl)):
                return t1
        if t2 + cl <= range_end:
            if all(context_lines[j] == file_lines[t2 + j] for j in range(cl)):
                return t2
    return None
