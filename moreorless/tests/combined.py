from unittest import TestCase

from moreorless.combined import _line_symbols, divergent_diff, merge_diff


class CombinedTest(TestCase):
    def test_two(self) -> None:
        self.assertEqual(
            [
                ("a", " "),
                ("b", "+"),
                ("c", "+"),
            ],
            _line_symbols(["a\n"], "a\nb\nc\n"),
        )

    def test_two_removal(self) -> None:
        self.assertEqual(
            [
                ("a", " "),
                ("b", "-"),
            ],
            _line_symbols(["a\nb\n"], "a\n"),
        )

    def test_two_replace(self) -> None:
        self.assertEqual(
            [
                ("a", "-"),
                ("x", "+"),
                ("b", " "),
            ],
            _line_symbols(["a\nb\n"], "x\nb\n"),
        )

    def test_three(self) -> None:
        self.assertEqual(
            [
                #     a    ab
                ("a", " ", " "),
                ("b", "+", " "),
                ("c", "+", "+"),
            ],
            _line_symbols(["a\n", "a\nb\n"], "a\nb\nc\n"),
        )

    def test_three_insert_same(self) -> None:
        # this covers the path inside `helper` when we already have a matching line
        self.assertEqual(
            [
                #     abc  abd
                ("a", " ", " "),
                ("b", "-", "-"),
                ("d", " ", "-"),
                ("c", " ", "+"),
            ],
            _line_symbols(["a\nb\nc\n", "a\nb\nd\n"], "a\nc\n"),
        )


class DivergentDiffTest(TestCase):
    def test_basic(self) -> None:
        result = divergent_diff("", ["a\n", "b\n"])
        self.assertEqual(
            """\
--- a/file
+++ b/file
+++ b/file
+ a
 +b
""",
            result,
        )


class MergeDiffTest(TestCase):
    def test_basic(self) -> None:
        result = merge_diff(["a\n", "b\n"], "")
        self.assertEqual(
            """\
--- a/file
--- a/file
+++ b/file
- a
 -b
""",
            result,
        )
