"""
Computes the "combined diff format" used by git.

Documented at https://git-scm.com/docs/diff-format#_combined_diff_format
but in a nutshell, lines are preceeded by more than one +/-/space symbol.

These are useful for understanding merges, divergence from a common ancestor,
or when you expect one diff and got another (to avoid displaying a
diff-of-diff, which is hard for humans to parse).
"""

from difflib import SequenceMatcher
from typing import Dict, List, Sequence, Tuple


def _line_symbols(
    files: Sequence[str],
    common: str,
) -> List[Tuple[str, ...]]:
    dest_lines = common.splitlines()
    # (file_symbol, ...)
    dest_line_symbols: List[List[str]] = [[] for _ in range(len(dest_lines))]
    # dest_idx: {text: {idx: symbol}}
    inserted_lines: List[Dict[str, Dict[int, str]]] = [
        {} for _ in range(len(dest_lines) + 1)
    ]

    def helper(s: str, dest_idx: int) -> Dict[int, str]:
        if s not in inserted_lines[dest_idx]:
            inserted_lines[dest_idx][s] = {}
        return inserted_lines[dest_idx][s]

    for si, src in enumerate(files):
        src_lines = src.splitlines()
        for tag, i1, i2, j1, j2 in SequenceMatcher(
            None, src_lines, dest_lines
        ).get_opcodes():
            for i in range(i1, i2):
                if tag == "delete":
                    helper(src_lines[i], j1)[si] = "-"
                elif tag == "replace":
                    helper(src_lines[i], j1)[si] = "-"
                else:
                    assert tag == "equal"

            for i in range(j1, j2):
                if tag == "equal":
                    dest_line_symbols[i].append(" ")
                elif tag == "insert":
                    dest_line_symbols[i].append("+")
                elif tag == "replace":
                    dest_line_symbols[i].append("+")
                else:  # pragma: no cover
                    raise AssertionError(tag)

        # TODO no newline at eof

    result = []
    for i in range(len(dest_lines) + 1):
        for t, symbols in inserted_lines[i].items():
            lst = [" "] * len(files)
            for a, b in symbols.items():
                lst[a] = b
            result.append((t, *lst))
        if i < len(dest_lines):
            result.append((dest_lines[i], *dest_line_symbols[i]))
    return result


FLIP_TABLE = {
    ord("-"): "+",
    ord("+"): "-",
}


def divergent_diff(
    original: str,
    files: Sequence[str],
    filename: str = "file",
) -> str:
    """
    Returns a combined unified diff of the changes turning `original` into each of `files`.
    """
    buf: List[str] = []
    buf.append(f"--- a/{filename}\n")
    for _ in range(len(files)):
        buf.append(f"+++ b/{filename}\n")
    for text, *symbols in _line_symbols(files, common=original):
        # flip +/-
        buf.append("".join(symbols).translate(FLIP_TABLE) + text + "\n")
    return "".join(buf)


def merge_diff(
    files: Sequence[str],
    final: str,
    filename: str = "file",
) -> str:
    """
    Returns a combined unified diff of the changes incorporating `files` heads to result in `final`.
    """
    buf: List[str] = []
    for _ in range(len(files)):
        buf.append(f"--- a/{filename}\n")
    buf.append(f"+++ b/{filename}\n")
    for text, *symbols in _line_symbols(files, common=final):
        buf.append("".join(symbols) + text + "\n")
    return "".join(buf)
