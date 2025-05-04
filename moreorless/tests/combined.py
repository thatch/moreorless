from unittest import TestCase

from moreorless.combined import _contributions, combined_diff
from moreorless.combined_types import Hunk, Line


class LineTest(TestCase):
    def test_common_only(self) -> None:
        li = Line((0, 0, 0, 1), "foo\n")
        self.assertFalse(li.is_context)
        self.assertEqual("+++foo\n", li.to_str(is_merge=True))
        self.assertEqual("---foo\n", li.to_str(is_merge=False))

    def test_context_only(self) -> None:
        li = Line((1, 1, 1, 1), "foo\n")
        self.assertTrue(li.is_context)
        self.assertEqual("   foo\n", li.to_str(is_merge=True))
        self.assertEqual("   foo\n", li.to_str(is_merge=False))

    def test_mixed(self) -> None:
        li = Line((1, 1, 0, 0), "foo\n")
        self.assertFalse(li.is_context)
        self.assertEqual("-- foo\n", li.to_str(is_merge=True))
        self.assertEqual("++ foo\n", li.to_str(is_merge=False))

    def test_no_newline(self) -> None:
        li = Line((1, 1, 0, 0), "foo")
        self.assertEqual(
            "-- foo\n\\ no newline at end of file", li.to_str(is_merge=True)
        )
        self.assertEqual(
            "++ foo\n\\ no newline at end of file", li.to_str(is_merge=False)
        )


class HunkTest(TestCase):
    def test_context_hunk(self) -> None:
        li = Line((1, 1, 1, 1), "foo\n")
        h = Hunk(
            [li],
            (1, 1, 1, 1),
        )
        assert h.is_entirely_context
        assert h.lengths == (1, 1, 1, 1)
        assert h.to_str(is_merge=True) == ""

    def test_mixed_hunk(self) -> None:
        a = Line((0, 0, 0, 1), "foo\n")
        b = Line((1, 1, 1, 1), "bar\n")
        h = Hunk(
            [a, b],
            (1, 1, 1, 1),
        )
        assert not h.is_entirely_context
        assert h.lengths == (1, 1, 1, 2)
        self.assertEqual(
            """\
@@@@ -1,1 -1,1 -1,1 +1,2 @@@@
+++foo
   bar
""",
            h.to_str(is_merge=True),
        )

        self.assertEqual(
            """\
@@@@ -1,2 +1,1 +1,1 +1,1 @@@@
---foo
   bar
""",
            h.to_str(is_merge=False),
        )


class DivergentDiffTest(TestCase):
    def test_combined_diff_exceptions(self) -> None:
        with self.assertRaises(ValueError):
            combined_diff(["a", "b"], ["c", "d"])
        with self.assertRaises(ValueError):
            combined_diff([], [])

    def test_basic(self) -> None:
        result = combined_diff([""], ["a\n", "b\n"])
        self.assertEqual(
            """\
--- a/file
+++ b/file
+++ b/file
@@@ -1,0 +1,1 +1,1 @@@
+ a
 +b
""",
            result,
        )

    def test_basic_with_explicit_names(self) -> None:
        result = combined_diff(
            [""], ["a\n", "b\n"], from_filenames=["x"], to_filenames=["y", "z"]
        )
        self.assertEqual(
            """\
--- x
+++ y
+++ z
@@@ -1,0 +1,1 +1,1 @@@
+ a
 +b
""",
            result,
        )

    def test_basic_context(self) -> None:
        result = combined_diff(["a\nb\nc\nd\ne\nf\ng\n"], ["b\nc\nd\ne\nf\n"])
        self.assertEqual(
            """\
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
""",
            result,
        )

    def test_basic_context1(self) -> None:
        result = combined_diff(
            ["a\nb\nc\nd\ne\nf\ng\n"], ["b\nc\nd\ne\nf\n"], context=1
        )
        self.assertEqual(
            """\
--- a/file
+++ b/file
@@ -1,2 +1,1 @@
-a
 b
@@ -5,2 +4,1 @@
 f
-g
""",
            result,
        )

    def test_basic_context_final_output(self) -> None:
        result = combined_diff(["a\nb\nc\nd\n"], ["a\nb\nc\nd\n"], context=1)
        self.assertEqual(
            """\
--- a/file
+++ b/file
""",
            result,
        )

    def test_two(self) -> None:
        self.assertEqual(
            [
                Line((1, 1), "a\n"),
                Line((1, 0), "b\n"),
                Line((1, 0), "c\n"),
            ],
            _contributions(["a\n"], ["a\nb\nc\n"], False),
        )

    def test_contributions_exceptions(self) -> None:
        with self.assertRaises(ValueError):
            _contributions([], [], False)
        with self.assertRaises(ValueError):
            _contributions(["a", "b"], ["c", "d"], False)

    def test_three(self) -> None:
        self.assertEqual(
            [
                Line((1, 1, 1), "a\n"),
                Line((0, 1, 1), "b\n"),
                Line((0, 0, 1), "c\n"),
            ],
            _contributions(["a\nb\nc\n"], ["a\n", "a\nb\n"], False),
        )

    def test_three_insert_same(self) -> None:
        # this covers the path inside `helper` when we already have a matching line
        self.assertEqual(
            [
                Line((1, 1, 1), "a\n"),
                Line((1, 0, 1), "c\n"),
                Line((1, 1, 0), "b\n"),
                Line((0, 1, 0), "d\n"),
            ],
            _contributions(["a\nc\n"], ["a\nb\nc\n", "a\nb\nd\n"], False),
        )


class MergeDiffTest(TestCase):
    def test_not_actually_merge(self) -> None:
        result = combined_diff(["a\nc\n"], ["b\nc\n"])
        self.assertEqual(
            """\
--- a/file
+++ b/file
@@ -1,2 +1,2 @@
-a
+b
 c
""",
            result,
        )

    def test_basic(self) -> None:
        result = combined_diff(["a\n", "b\n"], [""])
        self.assertEqual(
            """\
--- a/file
--- a/file
+++ b/file
@@@ -1,1 -1,1 +1,0 @@@
- a
 -b
""",
            result,
        )

    def test_basic_with_explicit_names(self) -> None:
        result = combined_diff(
            ["a\n", "b\n"],
            [""],
            from_filenames=["x", "y"],
            to_filenames=["z"],
        )
        self.assertEqual(
            """\
--- x
--- y
+++ z
@@@ -1,1 -1,1 +1,0 @@@
- a
 -b
""",
            result,
        )

    def test_two(self) -> None:
        self.assertEqual(
            [
                Line((1, 1), "a\n"),
                Line((0, 1), "b\n"),
                Line((0, 1), "c\n"),
            ],
            _contributions(["a\n"], ["a\nb\nc\n"], True),
        )

    def test_two_removal(self) -> None:
        self.assertEqual(
            [
                Line((1, 1), "a\n"),
                Line((1, 0), "b\n"),
            ],
            _contributions(["a\nb\n"], ["a\n"], True),
        )

    def test_two_replace(self) -> None:
        self.assertEqual(
            [
                Line((1, 0), "a\n"),
                Line((0, 1), "x\n"),
                Line((1, 1), "b\n"),
            ],
            _contributions(["a\nb\n"], ["x\nb\n"], True),
        )

    def test_three(self) -> None:
        self.assertEqual(
            [
                Line((1, 1, 1), "a\n"),
                Line((0, 1, 1), "b\n"),
                Line((0, 0, 1), "c\n"),
            ],
            _contributions(["a\n", "a\nb\n"], ["a\nb\nc\n"], True),
        )

    def test_three_insert_same(self) -> None:
        # this covers the path inside `helper` when we already have a matching line
        self.assertEqual(
            [
                Line((1, 1, 1), "a\n"),
                Line((1, 1, 0), "b\n"),
                Line((0, 1, 0), "d\n"),
                Line((1, 0, 1), "c\n"),
            ],
            _contributions(["a\nb\nc\n", "a\nb\nd\n"], ["a\nc\n"], True),
        )
