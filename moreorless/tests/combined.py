from unittest import TestCase

from moreorless.combined import _line_symbols

class CombinedTest(TestCase):
    def test_two(self):
        self.assertEqual(
            [
                ("a", " "),
                ("b", "+"),
            ],
            _line_symbols(["a\n", "a\nb\n"]),
        )

    def test_two_removal(self):
        self.assertEqual(
            [
                ("a", " "),
                ("b", "-"),
            ],
            _line_symbols(["a\nb\n", "a\n"]),
        )
        

    def test_three(self):
        self.assertEqual(
            [
                #     a    ab
                ("a", " ", " "),
                ("b", "+", " "),
                ("c", "+", "+"),
            ],
            _line_symbols(["a\n", "a\nb\n", "a\nb\nc\n"]),
        )
        
