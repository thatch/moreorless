import pytest

from moreorless.combined import _contributions, combined_diff
from moreorless.combined_types import Hunk, Line


def test_line_common_only() -> None:
    li = Line((0, 0, 0, 1), "foo\n")
    assert not li.is_context
    assert li.to_str(is_merge=True) == "+++foo\n"
    assert li.to_str(is_merge=False) == "---foo\n"


def test_line_context_only() -> None:
    li = Line((1, 1, 1, 1), "foo\n")
    assert li.is_context
    assert li.to_str(is_merge=True) == "   foo\n"
    assert li.to_str(is_merge=False) == "   foo\n"


def test_line_mixed() -> None:
    li = Line((1, 1, 0, 0), "foo\n")
    assert not li.is_context
    assert li.to_str(is_merge=True) == "-- foo\n"
    assert li.to_str(is_merge=False) == "++ foo\n"


def test_line_no_newline() -> None:
    li = Line((1, 1, 0, 0), "foo")
    assert li.to_str(is_merge=True) == "-- foo\n\\ No newline at end of file"
    assert li.to_str(is_merge=False) == "++ foo\n\\ No newline at end of file"


def test_hunk_context() -> None:
    li = Line((1, 1, 1, 1), "foo\n")
    h = Hunk([li], (1, 1, 1, 1))
    assert h.is_entirely_context
    assert h.lengths == (1, 1, 1, 1)
    assert h.to_str(is_merge=True) == ""


def test_hunk_mixed() -> None:
    a = Line((0, 0, 0, 1), "foo\n")
    b = Line((1, 1, 1, 1), "bar\n")
    h = Hunk([a, b], (1, 1, 1, 1))
    assert not h.is_entirely_context
    assert h.lengths == (1, 1, 1, 2)
    assert h.to_str(is_merge=True) == """\
@@@@ -1,1 -1,1 -1,1 +1,2 @@@@
+++foo
   bar
"""
    assert h.to_str(is_merge=False) == """\
@@@@ -1,2 +1,1 +1,1 +1,1 @@@@
---foo
   bar
"""


def test_combined_diff_exceptions() -> None:
    with pytest.raises(ValueError):
        combined_diff(["a", "b"], ["c", "d"])
    with pytest.raises(ValueError):
        combined_diff([], [])


def test_contributions_exceptions() -> None:
    with pytest.raises(ValueError):
        _contributions([], [], False)
    with pytest.raises(ValueError):
        _contributions(["a", "b"], ["c", "d"], False)


def test_divergent_basic() -> None:
    assert combined_diff([""], ["a\n", "b\n"]) == """\
--- a/file
+++ b/file
+++ b/file
@@@ -1,0 +1,1 +1,1 @@@
+ a
 +b
"""


def test_divergent_basic_explicit_names() -> None:
    result = combined_diff(
        [""], ["a\n", "b\n"], from_filenames=["x"], to_filenames=["y", "z"]
    )
    assert result == """\
--- x
+++ y
+++ z
@@@ -1,0 +1,1 +1,1 @@@
+ a
 +b
"""


def test_divergent_context() -> None:
    assert combined_diff(["a\nb\nc\nd\ne\nf\ng\n"], ["b\nc\nd\ne\nf\n"]) == """\
--- a/file
+++ b/file
@@ -1,7 +1,5 @@
-a
 b
 c
 d
 e
 f
-g
"""


def test_divergent_context1() -> None:
    result = combined_diff(["a\nb\nc\nd\ne\nf\ng\n"], ["b\nc\nd\ne\nf\n"], context=1)
    assert result == """\
--- a/file
+++ b/file
@@ -1,2 +1,1 @@
-a
 b
@@ -5,2 +4,1 @@
 f
-g
"""


def test_divergent_context_final_output() -> None:
    assert combined_diff(["a\nb\nc\nd\n"], ["a\nb\nc\nd\n"], context=1) == """\
--- a/file
+++ b/file
"""


def test_divergent_two_contributions() -> None:
    assert _contributions(["a\n"], ["a\nb\nc\n"], False) == [
        Line((1, 1), "a\n"),
        Line((1, 0), "b\n"),
        Line((1, 0), "c\n"),
    ]


def test_divergent_three_contributions() -> None:
    assert _contributions(["a\nb\nc\n"], ["a\n", "a\nb\n"], False) == [
        Line((1, 1, 1), "a\n"),
        Line((0, 1, 1), "b\n"),
        Line((0, 0, 1), "c\n"),
    ]


def test_divergent_three_insert_same() -> None:
    # covers the path inside `helper` when we already have a matching line
    assert _contributions(["a\nc\n"], ["a\nb\nc\n", "a\nb\nd\n"], False) == [
        Line((1, 1, 1), "a\n"),
        Line((1, 0, 1), "c\n"),
        Line((1, 1, 0), "b\n"),
        Line((0, 1, 0), "d\n"),
    ]


def test_merge_not_actually_merge() -> None:
    assert combined_diff(["a\nc\n"], ["b\nc\n"]) == """\
--- a/file
+++ b/file
@@ -1,2 +1,2 @@
-a
+b
 c
"""


def test_merge_basic() -> None:
    assert combined_diff(["a\n", "b\n"], [""]) == """\
--- a/file
--- a/file
+++ b/file
@@@ -1,1 -1,1 +1,0 @@@
- a
 -b
"""


def test_merge_basic_explicit_names() -> None:
    result = combined_diff(
        ["a\n", "b\n"], [""], from_filenames=["x", "y"], to_filenames=["z"]
    )
    assert result == """\
--- x
--- y
+++ z
@@@ -1,1 -1,1 +1,0 @@@
- a
 -b
"""


def test_merge_two_contributions() -> None:
    assert _contributions(["a\n"], ["a\nb\nc\n"], True) == [
        Line((1, 1), "a\n"),
        Line((0, 1), "b\n"),
        Line((0, 1), "c\n"),
    ]


def test_merge_two_removal() -> None:
    assert _contributions(["a\nb\n"], ["a\n"], True) == [
        Line((1, 1), "a\n"),
        Line((1, 0), "b\n"),
    ]


def test_merge_two_replace() -> None:
    assert _contributions(["a\nb\n"], ["x\nb\n"], True) == [
        Line((1, 0), "a\n"),
        Line((0, 1), "x\n"),
        Line((1, 1), "b\n"),
    ]


def test_merge_three_contributions() -> None:
    assert _contributions(["a\n", "a\nb\n"], ["a\nb\nc\n"], True) == [
        Line((1, 1, 1), "a\n"),
        Line((0, 1, 1), "b\n"),
        Line((0, 0, 1), "c\n"),
    ]


def test_merge_three_insert_same() -> None:
    # covers the path inside `helper` when we already have a matching line
    assert _contributions(["a\nb\nc\n", "a\nb\nd\n"], ["a\nc\n"], True) == [
        Line((1, 1, 1), "a\n"),
        Line((1, 1, 0), "b\n"),
        Line((0, 1, 0), "d\n"),
        Line((1, 0, 1), "c\n"),
    ]
