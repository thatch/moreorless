import random
import unittest
from typing import Any, List, Optional
from unittest.mock import patch

from parameterized import parameterized

from .. import unified_diff
from ..patch import (
    _context_match,
    _parse_position_line,
    _split_hunks,
    apply_single_file,
    PatchException,
)


class PatchTest(unittest.TestCase):
    @parameterized.expand(  # type: ignore
        [
            ("a", "b"),
            ("", "b"),
            ("a", ""),
            ("", "b\n"),
            ("a\n", ""),
            ("a\nb\n", "a\n"),
            ("a\nb\n", "b\n"),
            ("a\nb\n", "a\nb"),
            ("a\nb", "a\nb\n"),
        ]
    )
    def test_patch(self, a: str, b: str) -> None:
        diff = unified_diff(a, b, "foo")
        result = apply_single_file(a, diff)
        self.assertEqual(b, result)

        # Although we don't produce these, allow CRLF on the "No newline" line
        # to strip the full previous newline.
        if "No newline" in diff:
            dos_diff = diff.replace("\n\\ No newline", "\r\n\\ No newline")
            result = apply_single_file(a, dos_diff)
            self.assertEqual(b, result)

    @parameterized.expand(  # type: ignore
        [
            ("", "b\r\n"),
            ("a\r\n", ""),
            ("a\r\nb\r\n", "a\r\n"),
            ("a\r\nb\r\n", "b\r\n"),
            ("a\r\nb\r\n", "a\r\nb"),
            ("a\r\nb", "a\r\nb\r\n"),
        ]
    )
    def test_patch_crlf(self, a: str, b: str) -> None:
        diff = unified_diff(a, b, "foo")
        result = apply_single_file(a, diff)
        self.assertEqual(b, result)

    @parameterized.expand(  # type: ignore
        [
            (0,),
            (1,),
            (2,),
            (3,),
        ]
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
            ("---\n+++\n@@ -1 +1 @@\n-invalid\n", "Failed to apply with offset at 0"),
            ("---\n+++\n@@ -1 +1 @@\n invalid\n", "Failed to apply with offset at 0"),
            ("---\n+++\n@@ -1 +1 @@\nxinvalid\n", "Unknown line 'xinvalid\\\\n' at 0"),
        ]
    )
    def test_exceptions(self, diff: str, msg: str) -> None:
        with self.assertRaisesRegex(PatchException, msg):
            apply_single_file("foo\n", diff)

    @parameterized.expand(  # type: ignore
        [
            ("---\n+++\n@@ -1 +1 @@\n-invalid\n", "DELETE fail at 0"),
            ("---\n+++\n@@ -1 +1 @@\n invalid\n", "EQUAL fail at 0"),
            ("---\n+++\n@@ -1 +1 @@\nxinvalid\n", "Unknown line 'xinvalid\\\\n' at 0"),
        ]
    )
    def test_exceptions_no_offset(self, diff: str, msg: str) -> None:
        with self.assertRaisesRegex(PatchException, msg):
            apply_single_file("foo\n", diff, allow_offsets=False)

    def test_split_hunks_edge_cases(self) -> None:
        with self.assertRaisesRegex(PatchException, "Lines without hunk header.*"):
            _split_hunks(["foo\n"])
        self.assertEqual([], _split_hunks([]))

    @patch("moreorless.patch.LOG.info")
    def test_patch_small_offset(self, log_info: Any) -> None:
        a = "a\nb\nc\n"
        b = "a\nB\nc\n"
        modified = "x\n" + a
        expected = "x\n" + b

        diff = unified_diff(a, b, "foo")
        result = apply_single_file(modified, diff)
        self.assertEqual(expected, result)
        log_info.assert_called_with("Offset 1")

    @parameterized.expand(  # type: ignore
        [
            ((["0", "1", "2", "3"], 0, 5, 0), 0),  # can match at start
            ((["0", "1", "2", "3"], 0, 5, 1), 0),  # can match earlier
            ((["1", "2", "3", "4"], 0, 5, 0), 1),  # can match later
            ((["4"], 0, 5, 0), 4),  # can match later
            ((["5"], 0, 4, 3), None),  # no possible match, starts past mid
        ]
    )
    def test_context_match(self, args: Any, expected: Optional[int]) -> None:
        self.assertEqual(expected, _context_match(["0", "1", "2", "3", "4"], *args))

    def test_context_match_tie(self) -> None:
        # ties resolve earlier
        self.assertEqual(0, _context_match(["0", "1", "0"], ["0"], 0, 3, 1))

    def test_edge_cases(self) -> None:
        with self.assertRaisesRegex(PatchException, "negative range_start"):
            _context_match(["0", "1", "2"], ["0"], -1, 3, 0)
        with self.assertRaisesRegex(PatchException, "flipped range"):
            _context_match(["0", "1", "2"], ["0"], 3, 0, 0)
        with self.assertRaisesRegex(PatchException, "past end"):
            _context_match(["0", "1", "2"], ["0"], 0, 4, 0)
        with self.assertRaisesRegex(PatchException, "start before range_start"):
            _context_match(["0", "1", "2"], ["0"], 1, 3, 0)
        with self.assertRaisesRegex(PatchException, "start past range_end"):
            _context_match(["0", "1", "2"], ["0"], 0, 3, 3)
