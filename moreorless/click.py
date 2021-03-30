import sys
from pathlib import Path

import click

from . import unified_diff


def echo_color_unified_diff(astr: str, bstr: str, filename: str, n: int = 3) -> None:
    """
    Just like `moreorless.unified_diff` except using `click.secho`.
    """
    echo_color_precomputed_diff(unified_diff(astr, bstr, filename, n))


def echo_color_precomputed_diff(diff: str) -> None:
    """
    Like `echo_color_unified_diff`, but for precomputed diff results.
    """
    for line in diff.splitlines(True):
        # TODO benchmark and see if constructing the string up front is faster
        if line.startswith("---") or line.startswith("+++"):
            click.secho(line, bold=True, nl=False)
        elif line.startswith("@@"):
            click.secho(line, fg="cyan", nl=False)
        elif line.startswith("-"):
            click.secho(line, fg="red", nl=False)
        elif line.startswith("+"):
            click.secho(line, fg="green", nl=False)
        else:
            click.secho(line, nl=False)


def main(afile: str, bfile: str) -> None:  # pragma: no cover
    echo_color_unified_diff(Path(afile).read_text(), Path(bfile).read_text(), afile)


if __name__ == "__main__":  # pragma: no cover
    main(*sys.argv[1:])
