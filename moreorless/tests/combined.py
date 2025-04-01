from unittest import TestCase

from moreorless.combined import _line_symbols, divergent_diff, merge_diff


class CombinedTest(TestCase):
    def test_two(self):
        self.assertEqual(
            [
                ("a", " "),
                ("b", "+"),
            ],
            _line_symbols(["a\n"], "a\nb\n"),
        )

    def test_two_removal(self):
        self.assertEqual(
            [
                ("a", " "),
                ("b", "-"),
            ],
            _line_symbols(["a\nb\n"], "a\n"),
        )

    def test_three(self):
        self.assertEqual(
            [
                #     a    ab
                ("a", " ", " "),
                ("b", "+", " "),
                ("c", "+", "+"),
            ],
            _line_symbols(["a\n", "a\nb\n"], "a\nb\nc\n"),
        )


class DivergentDiffTest(TestCase):
    def test_basic(self):
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
    def test_basic(self):
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
