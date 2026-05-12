from unittest.mock import call, patch

from moreorless import unified_diff
from moreorless.click import echo_color_precomputed_diff, echo_color_unified_diff

_EXPECTED_CALLS = [
    call("--- a/x\n", bold=True, nl=False),
    call("+++ b/x\n", bold=True, nl=False),
    call("@@ -1,2 +1,2 @@\n", fg="cyan", nl=False),
    call(" a\n", nl=False),
    call("-b\n", fg="red", nl=False),
    call("+c\n", fg="green", nl=False),
]


@patch("click.secho")
def test_echo_color_unified_diff(secho: object) -> None:
    echo_color_unified_diff("a\nb\n", "a\nc\n", "x")
    secho.assert_has_calls(_EXPECTED_CALLS)  # type: ignore[attr-defined]


@patch("click.secho")
def test_echo_color_precomputed_diff(secho: object) -> None:
    echo_color_precomputed_diff(unified_diff("a\nb\n", "a\nc\n", "x"))
    secho.assert_has_calls(_EXPECTED_CALLS)  # type: ignore[attr-defined]
