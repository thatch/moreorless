"""
Computes the "combined diff format" used by git.

This is one way of showing a 3+ way diff, such as when you have a tool that
needs to show multiple diffs to a common ancestor (like input, expected
output, and actual output); or a merge that combines multiple heads into one
common descendant.  These are not intended to be applied.

Instead of a single +/- character, there are n-1 of those characters at the
start of the line, depending on which of the outputs (or inputs, in the case of
a merge) that line is present in.

If you're ever in a situation where you're analyzing a diff of diffs, this
might be helpful in reducing confusion.

Documented at https://git-scm.com/docs/diff-format#_combined_diff_format

Example of two diffs vs a common ancestor:

    $ python -m moreorless.combined a b c
    --- a/file
    +++ b/file
    +++ b/file
    @@@ -1,2 +1,2 +1,2 @@@
      def main():
    --    pass
    +     print("b")
     +    print("hi")
"""

from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Optional, Sequence, Union

from .combined_types import Hunk, Line, Snip


def combined_diff(
    from_files: List[str],
    to_files: List[str],
    basename: str = "file",
    from_filenames: Optional[List[str]] = None,
    to_filenames: Optional[List[str]] = None,
    context: int = 3,
) -> str:
    """
    Returns a combined diff representing a multiway change.
    """
    if not from_filenames:
        from_filenames = [f"a/{basename}"] * len(from_files)
    if not to_filenames:
        to_filenames = [f"b/{basename}"] * len(to_files)

    if len(from_files) != len(from_filenames):
        raise ValueError("Mismatched from_filenames length")
    if len(to_files) != len(to_filenames):
        raise ValueError("Mismatched to_filenames length")
    if len(from_files) != 1 and len(to_files) != 1:
        raise ValueError(
            f"one of from_files={len(from_files)} or to_files={len(to_files)} must be 1"
        )
    merge_mode = len(to_files) == 1

    file_header_symbols = ["-"] * len(from_files) + ["+"] * len(to_files)

    buf: List[str] = []
    for sym, fn in zip(file_header_symbols, from_filenames + to_filenames):
        buf.append(f"{sym}{sym}{sym} {fn}\n")

    for block in _group(
        _contributions(from_files, to_files, merge_mode=merge_mode), context=context
    ):
        if isinstance(block, Hunk):
            block.to_buf(buf, merge_mode)

    return "".join(buf)


def _contributions(
    from_files: Sequence[str],
    to_files: Sequence[str],
    merge_mode: bool,
) -> Sequence[Line]:
    """
    Calculate the contribution of various lines to the final result.

    Instead of storing the +/- symbols directly, we will store 1 in the
    column if the line exists in that file.

    This intermediate form is very simple to look for snip points (more than
    2*context runs of `(1, ...)`), and has the nice property that once
    you transpose to get columns, the `@@` lines for indices `i:j` start at
    `sum(col[:i])` and are `sum(col[i:j])` long.
    """
    if merge_mode:
        if len(to_files) != 1:
            raise ValueError("Can't merge_mode=True with to_files={len(to_files)}")
        common = to_files[0]
        rest = from_files
    else:
        if len(from_files) != 1:
            raise ValueError("Can't merge_mode=False with from_files={len(from_files)}")
        common = from_files[0]
        rest = to_files

    common_template = [0] * len(rest) + [1]

    common_lines = common.splitlines(True)
    common_contributions = [common_template.copy() for _ in common_lines]

    # dest_idx: {text: {idx: one_or_zero}}
    inserted_lines: List[Dict[str, Dict[int, int]]] = [
        {} for _ in range(len(common_lines) + 1)
    ]

    def helper(s: str, dest_idx: int) -> Dict[int, int]:
        if s not in inserted_lines[dest_idx]:
            inserted_lines[dest_idx][s] = {}
        return inserted_lines[dest_idx][s]

    for si, src in enumerate(rest):
        src_lines = src.splitlines(True)
        for tag, i1, i2, j1, j2 in SequenceMatcher(
            None, common_lines, src_lines
        ).get_opcodes():
            for i in range(i1, i2):
                if tag == "equal":
                    common_contributions[i][si] = 1

            for i in range(j1, j2):
                if tag == "insert":
                    helper(src_lines[i], i1)[si] = 1
                elif tag == "replace":
                    helper(src_lines[i], i1)[si] = 1

    result: List[Line] = []
    if merge_mode:
        for i in range(len(common_lines) + 1):
            for t, counts in inserted_lines[i].items():
                lst = [0] * len(rest)
                for a, b in counts.items():
                    lst[a] = b
                result.append(Line(tuple(lst) + (0,), t))

            if i < len(common_lines):
                result.append(Line(tuple(common_contributions[i]), common_lines[i]))
    else:
        for i in range(len(common_lines) + 1):
            if i < len(common_lines):
                result.append(Line(tuple(common_contributions[i]), common_lines[i]))

            for t, counts in inserted_lines[i].items():
                lst = [0] * len(rest)
                for a, b in counts.items():
                    lst[a] = b
                result.append(Line(tuple(lst) + (0,), t))

    return result


def _group(lines: Sequence[Line], context: int = 3) -> Iterable[Union[Hunk, Snip]]:
    no_change_count = [0] * len(lines)
    # Take as input the counts which represent symbols
    # + a
    #   b
    #   c
    #   d
    # + e
    for i, line in enumerate(lines):
        if line.is_context:
            no_change_count[i] = 1
    # Now we have a local which is 1 wherever it's common context
    # 0 + a
    # 1   b
    # 1   c
    # 1   d
    # 0 + e
    tmp_fwd = no_change_count.copy()
    tmp_rev = no_change_count.copy()

    for i in range(len(lines) - 1):
        if no_change_count[i] > 0 and no_change_count[i + 1] > 0:
            tmp_fwd[i + 1] = tmp_fwd[i] + 1

    for i in range(len(lines) - 1, 0, -1):
        if no_change_count[i] > 0 and no_change_count[i - 1] > 0:
            tmp_rev[i - 1] = tmp_rev[i] + 1

    result = [min(a, b) for a, b in zip(tmp_fwd, tmp_rev)]
    # Now we have the triangular count, and anywhere the count is >= context we can split
    # 0 + a
    # 1   b
    # 2   c
    # 1   d
    # 0 + e

    context_flag = 0
    buf = []
    omit_count = 0
    assert line
    starts = [1] * len(line.contributions)

    for i, line in enumerate(lines):
        if result[i] <= context:
            if omit_count:
                yield Snip(omit_count)
            omit_count = 0
            context_flag = 0
            buf.append(line)
        elif context_flag:
            omit_count += 1
            starts = [x + y for x, y in zip(starts, line.contributions)]
        else:
            if buf and not all(x.is_context for x in buf):
                hunk = Hunk(buf, starts)
                yield hunk
                starts = [x + y for x, y in zip(starts, hunk.lengths)]
            buf = []
            context_flag = 1

    if buf and not all(x.is_context for x in buf):
        yield Hunk(buf, starts)


if __name__ == "__main__":  # pragma: no cover
    import sys
    from pathlib import Path

    lst = [Path(f).read_text() for f in sys.argv[1:]]
    print(combined_diff(lst[:1], lst[1:]), end="")
