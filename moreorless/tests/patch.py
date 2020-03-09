import random
import unittest
from typing import List, Optional

from parameterized import parameterized

from .. import unified_diff
from ..patch import (
    PatchException,
    _parse_position_line,
    _split_hunks,
    apply_single_file,
)


class PatchTest(unittest.TestCase):
    @parameterized.expand(  # type: ignore
        [("a\nb\n", "a\n"), ("a\nb\n", "b\n"), ("a\nb\n", "a\nb"), ("a\nb", "a\nb\n"),]
    )
    def test_patch(self, a: str, b: str) -> None:
        diff = unified_diff(a, b, "foo")
        result = apply_single_file(a, diff)
        self.assertEqual(b, result)

    @parameterized.expand(  # type: ignore
        [(0,), (1,), (2,), (3,),]
    )
    def test_exhaustive(self, context: int) -> None:
        for i in range(100):
            a = "".join(
                [random.choice(["a\n", "b\n", "c\n", "d\n"]) for x in range(10)]
            )
            b = "".join(
                [random.choice(["a\n", "b\n", "c\n", "d\n"]) for x in range(10)]
            )

            diff = unified_diff(a, b, "file", context)
            result = apply_single_file(a, diff)
            self.assertEqual(b, result)

    @parameterized.expand(  # type: ignore
        [
            ("@@ -5 +9 @@", [5, 1, 9, 1]),
            ("@@ -5,2 +9,3 @@", [5, 2, 9, 3]),
            ("@@ invalid @@", None),
        ]
    )
    def test_parse_position_line(
        self, line: str, expected: Optional[List[int]]
    ) -> None:
        if expected is None:
            with self.assertRaises(PatchException):
                _parse_position_line(line)
        else:
            self.assertEqual(expected, _parse_position_line(line))

    @parameterized.expand(  # type: ignore
        [
            ("---\n+++\n@@ -1 +1 @@\n-invalid\n", "DELETE fail at 0"),
            ("---\n+++\n@@ -1 +1 @@\n invalid\n", "EQUAL fail at 0"),
            ("---\n+++\n@@ -1 +1 @@\nxinvalid\n", "Unknown line 'xinvalid\\\\n' at 0"),
        ]
    )
    def test_exceptions(self, diff: str, msg: str) -> None:
        with self.assertRaisesRegex(PatchException, msg):
            apply_single_file("foo\n", diff)

    def test_split_hunks_edge_cases(self) -> None:
        with self.assertRaisesRegex(PatchException, "Lines without hunk header.*"):
            _split_hunks(["foo\n"])
        self.assertEqual([], _split_hunks([]))
