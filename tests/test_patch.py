import random
from typing import List, Optional
from unittest.mock import patch

import pytest

from moreorless import unified_diff
from moreorless.patch import (
    PatchException,
    _context_match,
    _parse_position_line,
    _split_hunks,
    apply_single_file,
)


@pytest.mark.parametrize(
    "a,b",
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
    ],
)
def test_patch(a: str, b: str) -> None:
    diff = unified_diff(a, b, "foo")
    assert apply_single_file(a, diff) == b

    if "No newline" in diff:
        dos_diff = diff.replace("\n\\ No newline", "\r\n\\ No newline")
        assert apply_single_file(a, dos_diff) == b


@pytest.mark.parametrize(
    "a,b",
    [
        ("", "b\r\n"),
        ("a\r\n", ""),
        ("a\r\nb\r\n", "a\r\n"),
        ("a\r\nb\r\n", "b\r\n"),
        ("a\r\nb\r\n", "a\r\nb"),
        ("a\r\nb", "a\r\nb\r\n"),
    ],
)
def test_patch_crlf(a: str, b: str) -> None:
    diff = unified_diff(a, b, "foo")
    assert apply_single_file(a, diff) == b


@pytest.mark.parametrize("context", [0, 1, 2, 3])
def test_exhaustive(context: int) -> None:
    for _ in range(100):
        a = "".join([random.choice(["a\n", "b\n", "c\n", "d\n"]) for _ in range(10)])
        b = "".join([random.choice(["a\n", "b\n", "c\n", "d\n"]) for _ in range(10)])
        assert apply_single_file(a, unified_diff(a, b, "file", context)) == b


@pytest.mark.parametrize(
    "line,expected",
    [
        ("@@ -5 +9 @@", [5, 1, 9, 1]),
        ("@@ -5,2 +9,3 @@", [5, 2, 9, 3]),
        ("@@ invalid @@", None),
    ],
)
def test_parse_position_line(line: str, expected: Optional[List[int]]) -> None:
    if expected is None:
        with pytest.raises(PatchException):
            _parse_position_line(line)
    else:
        assert _parse_position_line(line) == expected


@pytest.mark.parametrize(
    "diff,msg",
    [
        ("---\n+++\n@@ -1 +1 @@\n-invalid\n", "Failed to apply with offset at 0"),
        ("---\n+++\n@@ -1 +1 @@\n invalid\n", "Failed to apply with offset at 0"),
        ("---\n+++\n@@ -1 +1 @@\nxinvalid\n", "Unknown line 'xinvalid\\\\n' at 0"),
    ],
)
def test_exceptions(diff: str, msg: str) -> None:
    with pytest.raises(PatchException, match=msg):
        apply_single_file("foo\n", diff)


@pytest.mark.parametrize(
    "diff,msg",
    [
        ("---\n+++\n@@ -1 +1 @@\n-invalid\n", "DELETE fail at 0"),
        ("---\n+++\n@@ -1 +1 @@\n invalid\n", "EQUAL fail at 0"),
        ("---\n+++\n@@ -1 +1 @@\nxinvalid\n", "Unknown line 'xinvalid\\\\n' at 0"),
    ],
)
def test_exceptions_no_offset(diff: str, msg: str) -> None:
    with pytest.raises(PatchException, match=msg):
        apply_single_file("foo\n", diff, allow_offsets=False)


def test_split_hunks_edge_cases() -> None:
    with pytest.raises(PatchException, match="Lines without hunk header.*"):
        _split_hunks(["foo\n"])
    assert _split_hunks([]) == []


@patch("moreorless.patch.LOG.info")
def test_patch_small_offset(log_info: object) -> None:
    a = "a\nb\nc\n"
    b = "a\nB\nc\n"
    result = apply_single_file("x\n" + a, unified_diff(a, b, "foo"))
    assert result == "x\n" + b
    log_info.assert_called_with("Offset 1")  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "args,expected",
    [
        ((["0", "1", "2", "3"], 0, 5, 0), 0),  # can match at start
        ((["0", "1", "2", "3"], 0, 5, 1), 0),  # can match earlier
        ((["1", "2", "3", "4"], 0, 5, 0), 1),  # can match later
        ((["4"], 0, 5, 0), 4),  # can match later
        ((["5"], 0, 4, 3), None),  # no possible match, starts past mid
    ],
)
def test_context_match(args: tuple, expected: Optional[int]) -> None:
    assert _context_match(["0", "1", "2", "3", "4"], *args) == expected


def test_context_match_tie() -> None:
    # ties resolve earlier
    assert _context_match(["0", "1", "0"], ["0"], 0, 3, 1) == 0


def test_edge_cases() -> None:
    with pytest.raises(PatchException, match="negative range_start"):
        _context_match(["0", "1", "2"], ["0"], -1, 3, 0)
    with pytest.raises(PatchException, match="flipped range"):
        _context_match(["0", "1", "2"], ["0"], 3, 0, 0)
    with pytest.raises(PatchException, match="past end"):
        _context_match(["0", "1", "2"], ["0"], 0, 4, 0)
    with pytest.raises(PatchException, match="start before range_start"):
        _context_match(["0", "1", "2"], ["0"], 1, 3, 0)
    with pytest.raises(PatchException, match="start past range_end"):
        _context_match(["0", "1", "2"], ["0"], 0, 3, 3)
