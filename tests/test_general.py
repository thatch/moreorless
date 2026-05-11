import subprocess
import tempfile
from pathlib import Path

import pytest

from moreorless import unified_diff


@pytest.mark.parametrize(
    "a,b",
    [
        ("a", "a"),
        ("a", "b"),
        ("a\n", "b"),
        ("a", "b\n"),
        ("a\n", "b\n"),
    ],
)
def test_parity(a: str, b: str) -> None:
    with tempfile.TemporaryDirectory() as d:
        a_path = Path(d) / "a"
        a_path.mkdir()
        b_path = Path(d) / "b"
        b_path.mkdir()
        (a_path / "file").write_text(a)
        (b_path / "file").write_text(b)

        proc = subprocess.run(
            ["diff", "--label", "a/file", "--label", "b/file", "-u", "a", "b"],
            cwd=d,
            encoding="utf-8",
            stdout=subprocess.PIPE,
        )
        if "\n" in proc.stdout:
            expected = proc.stdout[proc.stdout.index("\n") + 1 :]
        else:
            expected = ""

        assert unified_diff(a, b, "file") == expected


def test_absolute_paths() -> None:
    actual = unified_diff("a\n", "a\nb\n", "/file")
    assert actual == """\
--- /file
+++ /file
@@ -1 +1,2 @@
 a
+b
"""
