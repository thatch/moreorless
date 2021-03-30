import subprocess
import tempfile
import unittest
from pathlib import Path

from parameterized import parameterized

from .. import unified_diff


class ParityTest(unittest.TestCase):
    @parameterized.expand(  # type: ignore
        [
            ("a", "a"),
            ("a", "b"),
            ("a\n", "b"),
            ("a", "b\n"),
            ("a\n", "b\n"),
        ]
    )
    def test_parity(self, a: str, b: str) -> None:
        with tempfile.TemporaryDirectory() as d:
            a_path = Path(d) / "a"
            a_path.mkdir()
            b_path = Path(d) / "b"
            b_path.mkdir()
            (a_path / "file").write_text(a)
            (b_path / "file").write_text(b)

            # Notably, diff exits 1 when the files are different :/
            # Force the labels because it would otherwise include timestamps.
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

            actual = unified_diff(a, b, "file")
            self.assertEqual(expected, actual)

    def test_absolute_paths(self) -> None:
        actual = unified_diff("a\n", "a\nb\n", "/file")
        self.assertEqual(
            """\
--- /file
+++ /file
@@ -1 +1,2 @@
 a
+b
""",
            actual,
        )
