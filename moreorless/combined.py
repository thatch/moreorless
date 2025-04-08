"""
Computes the "combined diff format" used by git.

Documented at https://git-scm.com/docs/diff-format#_combined_diff_format
but in a nutshell, lines are preceeded by more than one +/-/space symbol.

These are useful for understanding merges, divergence from a common ancestor,
or when you expect one diff and got another (to avoid displaying a
diff-of-diff, which is hard for humans to parse).

Confusing:

    $ diff -u <( diff -u a b ) <( diff -u a c)
    --- /dev/fd/11	2025-04-03 13:46:26
    +++ /dev/fd/12	2025-04-03 13:46:26
    @@ -1,6 +1,6 @@
     --- a	2025-04-03 13:12:09
    -+++ b	2025-04-03 13:35:12
    ++++ c	2025-04-03 13:12:27
     @@ -1,2 +1,2 @@
      def main():
     -    pass
    -+    print("b")
    ++    print("hi")

Better:

    $ python -m moreorless.combined a b c
    --- a/file
    +++ b/file
    +++ b/file
      def main():
    --    pass
    +     print("b")
     +    print("hi")


Another confusing example from writing tests for a thing that produces diffs:

    AssertionError: '--- a/file\n--- a/file\n+++ b/file\n- a\n -b\n' != '--- a/file\n+++ b/file\n+++ b/file\n- a\n -b\n'
      --- a/file
    - --- a/file
    + +++ b/file
      +++ b/file
      - a
       -b

"""

from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union


def _contributions(
    files: Sequence[str],
    common: str,
    merge: bool,
) -> List[Tuple[Tuple[int, ...], str]]:
    """
    Calculate the contribution of various lines to the final result.

    Instead of storing the +/- symbols directly, we will store 1 in the
    column if the line exists in that file.  We consider `common` as an
    additional column.

    This intermediate form is very simple to look for snip points (more than
    2*context runs if `[0, 0, 0, 0...]`), and has the nice property that the
    `@@` lines for indices `i:j` start at `sum(contribution[:i])` and are
    `sum(contribution[i:j])` long.

    If `merge` is true, changes from common are considered deletions; otherwise
    they are considered additions.
    """
    common_template = [0] * len(files) + [1]

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

    for si, src in enumerate(files):
        src_lines = src.splitlines(True)
        for tag, i1, i2, j1, j2 in SequenceMatcher(
            None, common_lines, src_lines
        ).get_opcodes():
            for i in range(i1, i2):
                if tag == "equal":
                    common_contributions[i][si] = 1
                else:
                    assert tag != "equal"

            for i in range(j1, j2):
                if tag == "insert":
                    helper(src_lines[i], i1)[si] = 1
                elif tag == "replace":
                    helper(src_lines[i], i1)[si] = 1
                else:
                    assert tag == "equal"

    result: List[Tuple[Tuple[int, ...], str]] = []
    for i in range(len(common_lines) + 1):
        if not merge:
            if i < len(common_lines):
                result.append((tuple(common_contributions[i]), common_lines[i]))

        for t, counts in inserted_lines[i].items():
            lst = [0] * (len(files) + 1)
            for a, b in counts.items():
                lst[a] = b
            result.append((tuple(lst), t))

        if merge:
            if i < len(common_lines):
                result.append((tuple(common_contributions[i]), common_lines[i]))
    return result


def _group(
    lines: List[Tuple[Tuple[int, ...], str]], context: int = 3
) -> Iterable[Union[int, List[Tuple[Tuple[int, ...], str]]]]:
    no_change_count = [0] * len(lines)
    # Take as input the counts which represent symbols
    # + a
    #   b
    #   c
    #   d
    # + e
    for i, (symbols, line) in enumerate(lines):
        if sum(symbols) == len(symbols):
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
    assert symbols
    context_symbols = (1,) * len(symbols)

    for i, (symbols, line) in enumerate(lines):
        if result[i] <= context:
            if omit_count:
                yield omit_count
            omit_count = 0
            context_flag = 0
            buf.append((symbols, line))
        elif context_flag:
            omit_count += 1
        else:
            if buf and not all(x == context_symbols for x, y in buf):
                yield buf
            buf = []
            context_flag = 1

    if buf and not all(x == context_symbols for x, y in buf):
        yield buf


def combined_diff(
    files: List[str],
    basename: str = "file",
    filenames: Optional[List[str]] = None,
    merge: bool = False,
    context: int = 3,
) -> str:
    """
    Returns a combined unified diff of the changes turning `original` into each of `files`.
    """
    if not filenames:
        if not merge:
            filenames = [f"a/{basename}"]
            filenames.extend([f"b/{basename}"] * (len(files) - 1))
        else:
            filenames = [f"a/{basename}"] * (len(files) - 1)
            filenames.append(f"b/{basename}")
    assert len(filenames) == len(files), filenames

    if not merge:
        file_header_symbols = ["-"] + ["+"] * (len(files) - 1)
    else:
        file_header_symbols = ["-"] * (len(files) - 1) + ["+"]

    buf: List[str] = []
    for sym, fn in zip(file_header_symbols, filenames):
        buf.append(f"{sym}{sym}{sym} {fn}\n")

    if merge:
        common = files.pop(-1)
    else:
        common = files.pop(0)

    no_change = (1,) * (len(files) + 1)
    common_only = (0,) * len(files) + (1,)
    t = {0: " ", 1: "-" if merge else "+"}
    position = [1] * (len(files) + 1)

    lengths: List[int]
    for block in _group(
        _contributions(files, common=common, merge=merge), context=context
    ):
        if isinstance(block, list):
            lengths = [sum(b[i] for (b, s) in block) for i in range(len(position))]
            counts = [f"{position[i]},{lengths[i]}" for i in range(len(position))]
            if not merge:
                counts = counts[-1:] + counts[:-1]

            buf.append(
                "@" * (len(files) + 1)
                + " "
                + " ".join(
                    f"{sym}{count}" for sym, count in zip(file_header_symbols, counts)
                )
                + " "
                + "@" * (len(files) + 1)
                + "\n"
            )
            for symbols, text in block:
                # TODO no newline
                if symbols == no_change:
                    buf.append(" " * len(files) + text)
                elif symbols == common_only:
                    buf.append("-" * len(files) + text)
                else:
                    buf.append("".join(t[x] for x in symbols[:-1]) + text)
            position = [x + y for x, y in zip(position, lengths)]
        else:
            position = [x + block for x in position]

    return "".join(buf)


if __name__ == "__main__":  # pragma: no cover
    import sys
    from pathlib import Path

    lst = [Path(f).read_text() for f in sys.argv[1:]]
    print(combined_diff(lst, merge=False), end="")
