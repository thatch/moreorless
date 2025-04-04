from unittest import TestCase

from moreorless.combined import _line_symbols, combined_diff


class DivergentDiffTest(TestCase):
    def test_basic(self) -> None:
        result = combined_diff(["", "a\n", "b\n"], merge=False)
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

    def test_basic_with_explicit_names(self) -> None:
        result = combined_diff(
            ["", "a\n", "b\n"], filenames=["x", "y", "z"], merge=False
        )
        self.assertEqual(
            """\
--- x
+++ y
+++ z
+ a
 +b
""",
            result,
        )

    def test_two(self) -> None:
        self.assertEqual(
            [
                ("a", " "),
                ("b", "-"),
                ("c", "-"),
            ],
            _line_symbols(["a\n"], common="a\nb\nc\n", merge=False),
        )

    def test_two_removal(self) -> None:
        self.assertEqual(
            [
                ("a", " "),
                ("b", "+"),
            ],
            _line_symbols(["a\nb\n"], common="a\n", merge=False),
        )

    def test_two_replace(self) -> None:
        self.assertEqual(
            [
                ("x", "-"),
                ("a", "+"),
                ("b", " "),
            ],
            _line_symbols(["a\nb\n"], common="x\nb\n", merge=False),
        )

    def test_three(self) -> None:
        self.assertEqual(
            [
                #     a    ab
                ("a", " ", " "),
                ("b", "-", " "),
                ("c", "-", "-"),
            ],
            _line_symbols(["a\n", "a\nb\n"], common="a\nb\nc\n", merge=False),
        )

    def test_three_insert_same(self) -> None:
        # this covers the path inside `helper` when we already have a matching line
        self.assertEqual(
            [
                #     abc  abd
                ("a", " ", " "),
                ("c", " ", "-"),
                ("b", "+", "+"),
                ("d", " ", "+"),
            ],
            _line_symbols(["a\nb\nc\n", "a\nb\nd\n"], common="a\nc\n", merge=False),
        )


class MergeDiffTest(TestCase):
    def test_basic(self) -> None:
        result = combined_diff(["a\n", "b\n", ""], merge=True)
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

    def test_basic_with_explicit_names(self) -> None:
        result = combined_diff(
            ["a\n", "b\n", ""], filenames=["x", "y", "z"], merge=True
        )
        self.assertEqual(
            """\
--- x
--- y
+++ z
- a
 -b
""",
            result,
        )

    def test_two(self) -> None:
        self.assertEqual(
            [
                ("a", " "),
                ("b", "+"),
                ("c", "+"),
            ],
            _line_symbols(["a\n"], common="a\nb\nc\n", merge=True),
        )

    def test_two_removal(self) -> None:
        self.assertEqual(
            [
                ("a", " "),
                ("b", "-"),
            ],
            _line_symbols(["a\nb\n"], common="a\n", merge=True),
        )

    def test_two_replace(self) -> None:
        self.assertEqual(
            [
                ("a", "-"),
                ("x", "+"),
                ("b", " "),
            ],
            _line_symbols(["a\nb\n"], common="x\nb\n", merge=True),
        )

    def test_three(self) -> None:
        self.assertEqual(
            [
                #     a    ab
                ("a", " ", " "),
                ("b", "+", " "),
                ("c", "+", "+"),
            ],
            _line_symbols(["a\n", "a\nb\n"], common="a\nb\nc\n", merge=True),
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
            _line_symbols(["a\nb\nc\n", "a\nb\nd\n"], common="a\nc\n", merge=True),
        )
