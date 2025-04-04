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
from typing import Dict, List, Optional, Sequence, Tuple


def _line_symbols(
    files: Sequence[str],
    common: str,
    merge: bool,
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

    if merge:
        old = "-"
        new = "+"
    else:
        old = "+"
        new = "-"

    for si, src in enumerate(files):
        src_lines = src.splitlines()
        for tag, i1, i2, j1, j2 in SequenceMatcher(
            None, src_lines, dest_lines
        ).get_opcodes():
            for i in range(i1, i2):
                if tag == "delete":
                    helper(src_lines[i], j1)[si] = old
                elif tag == "replace":
                    helper(src_lines[i], j1)[si] = old
                else:
                    assert tag == "equal"

            for i in range(j1, j2):
                if tag == "equal":
                    dest_line_symbols[i].append(" ")
                elif tag == "insert":
                    dest_line_symbols[i].append(new)
                elif tag == "replace":
                    dest_line_symbols[i].append(new)
                else:  # pragma: no cover
                    raise AssertionError(tag)

        # TODO no newline at eof

    result = []
    for i in range(len(dest_lines) + 1):
        if not merge:
            if i < len(dest_lines):
                result.append((dest_lines[i], *dest_line_symbols[i]))

        for t, symbols in inserted_lines[i].items():
            lst = [" "] * len(files)
            for a, b in symbols.items():
                lst[a] = b
            result.append((t, *lst))

        if merge:
            if i < len(dest_lines):
                result.append((dest_lines[i], *dest_line_symbols[i]))
    return result


def combined_diff(
    files: Sequence[str],
    basename: str = "file",
    filenames: Optional[Sequence] = None,
    merge: bool = False,
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

    buf: List[str] = []
    if not merge:
        buf.append(f"--- {filenames[0]}\n")
        for i in range(1, len(files)):
            buf.append(f"+++ {filenames[i]}\n")
    else:
        for i in range(0, len(files) - 1):
            buf.append(f"--- {filenames[i]}\n")
        buf.append(f"+++ {filenames[-1]}\n")

    if merge:
        common = files.pop(-1)
    else:
        common = files.pop(0)

    for text, *symbols in _line_symbols(files, common=common, merge=merge):
        buf.append("".join(symbols) + text + "\n")

    return "".join(buf)


if __name__ == "__main__":  # pragma: no cover
    import sys
    from pathlib import Path

    lst = [Path(f).read_text() for f in sys.argv[1:]]
    print(combined_diff(lst, merge=False))
