from unittest import TestCase

from moreorless.combined import _contributions, combined_diff


class DivergentDiffTest(TestCase):
    def test_basic(self) -> None:
        result = combined_diff(["", "a\n", "b\n"], merge=False)
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
            ["", "a\n", "b\n"], filenames=["x", "y", "z"], merge=False
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
        result = combined_diff(
            ["a\nb\nc\nd\ne\nf\ng\n", "b\nc\nd\ne\nf\n"], merge=False
        )
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
            ["a\nb\nc\nd\ne\nf\ng\n", "b\nc\nd\ne\nf\n"], merge=False, context=1
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

    # Buggy
    def test_basic_context_final_output(self) -> None:
        result = combined_diff(["a\nb\nc\nd\n", "a\nb\nc\nd\n"], merge=False, context=1)
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
                ((1, 1), "a\n"),
                ((0, 1), "b\n"),
                ((0, 1), "c\n"),
            ],
            _contributions(["a\n"], common="a\nb\nc\n", merge=False),
        )

    def test_two_removal(self) -> None:
        self.assertEqual(
            [
                ((1, 1), "a\n"),
                ((1, 0), "b\n"),
            ],
            _contributions(["a\nb\n"], common="a\n", merge=False),
        )

    def test_two_replace(self) -> None:
        self.assertEqual(
            [
                ((0, 1), "x\n"),
                ((1, 0), "a\n"),
                ((1, 1), "b\n"),
            ],
            _contributions(["a\nb\n"], common="x\nb\n", merge=False),
        )

    def test_three(self) -> None:
        self.assertEqual(
            [
                ((1, 1, 1), "a\n"),
                ((0, 1, 1), "b\n"),
                ((0, 0, 1), "c\n"),
            ],
            _contributions(["a\n", "a\nb\n"], common="a\nb\nc\n", merge=False),
        )

    def test_three_insert_same(self) -> None:
        # this covers the path inside `helper` when we already have a matching line
        self.assertEqual(
            [
                ((1, 1, 1), "a\n"),
                ((1, 0, 1), "c\n"),
                ((1, 1, 0), "b\n"),
                ((0, 1, 0), "d\n"),
            ],
            _contributions(["a\nb\nc\n", "a\nb\nd\n"], common="a\nc\n", merge=False),
        )


class MergeDiffTest(TestCase):
    def test_basic(self) -> None:
        result = combined_diff(["a\n", "b\n", ""], merge=True)
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
            ["a\n", "b\n", ""], filenames=["x", "y", "z"], merge=True
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
                ((1, 1), "a\n"),
                ((0, 1), "b\n"),
                ((0, 1), "c\n"),
            ],
            _contributions(["a\n"], common="a\nb\nc\n", merge=True),
        )

    def test_two_removal(self) -> None:
        self.assertEqual(
            [
                ((1, 1), "a\n"),
                ((1, 0), "b\n"),
            ],
            _contributions(["a\nb\n"], common="a\n", merge=True),
        )

    def test_two_replace(self) -> None:
        self.assertEqual(
            [
                ((1, 0), "a\n"),
                ((0, 1), "x\n"),
                ((1, 1), "b\n"),
            ],
            _contributions(["a\nb\n"], common="x\nb\n", merge=True),
        )

    def test_three(self) -> None:
        self.assertEqual(
            [
                ((1, 1, 1), "a\n"),
                ((0, 1, 1), "b\n"),
                ((0, 0, 1), "c\n"),
            ],
            _contributions(["a\n", "a\nb\n"], common="a\nb\nc\n", merge=True),
        )

    def test_three_insert_same(self) -> None:
        # this covers the path inside `helper` when we already have a matching line
        self.assertEqual(
            [
                ((1, 1, 1), "a\n"),
                ((1, 1, 0), "b\n"),
                ((0, 1, 0), "d\n"),
                ((1, 0, 1), "c\n"),
            ],
            _contributions(["a\nb\nc\n", "a\nb\nd\n"], common="a\nc\n", merge=True),
        )
