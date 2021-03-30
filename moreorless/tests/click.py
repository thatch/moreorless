import unittest
from typing import Any
from unittest.mock import call, patch

from .. import unified_diff
from ..click import echo_color_precomputed_diff, echo_color_unified_diff


class ColorTest(unittest.TestCase):
    @patch("click.secho")
    def test_echo_color_unified_diff(self, secho: Any) -> None:
        echo_color_unified_diff("a\nb\n", "a\nc\n", "x")
        secho.assert_has_calls(
            [
                call("--- a/x\n", bold=True, nl=False),
                call("+++ b/x\n", bold=True, nl=False),
                call("@@ -1,2 +1,2 @@\n", fg="cyan", nl=False),
                call(" a\n", nl=False),
                call("-b\n", fg="red", nl=False),
                call("+c\n", fg="green", nl=False),
            ]
        )

    @patch("click.secho")
    def test_echo_color_precomputed_diff(self, secho: Any) -> None:
        diff = unified_diff("a\nb\n", "a\nc\n", "x")
        echo_color_precomputed_diff(diff)
        secho.assert_has_calls(
            [
                call("--- a/x\n", bold=True, nl=False),
                call("+++ b/x\n", bold=True, nl=False),
                call("@@ -1,2 +1,2 @@\n", fg="cyan", nl=False),
                call(" a\n", nl=False),
                call("-b\n", fg="red", nl=False),
                call("+c\n", fg="green", nl=False),
            ]
        )
