import difflib

__all__ = ["unified_diff"]


def unified_diff(astr: str, bstr: str, filename: str, n: int = 3,) -> str:
    """
    Returns a unified diff string for the two inputs.

    Does not currently support creation or deletion where one of the filenames
    is `/dev/null` or patchlevels other than `-p1`.

    Does handle the "no newline at end of file" properly UNLIKE DIFFLIB.
    """
    buf = []
    gen = difflib.unified_diff(
        astr.splitlines(True),
        bstr.splitlines(True),
        f"a/{filename}",
        f"b/{filename}",
        n=n,
    )
    for line in gen:
        buf.append(line)
        if not line.endswith("\n"):
            # Assume this is the only case where it can happen
            buf.append("\n\\ No newline at end of file\n")

    return "".join(buf)
