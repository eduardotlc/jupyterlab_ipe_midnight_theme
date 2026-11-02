"""Check the design rules of the theme on every variant."""

import re
from itertools import combinations, pairwise
from pathlib import Path

import pytest
from theme_css import VARIANTS, contrast, distance, load_variant, resolve

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = ROOT / "node_modules/@jupyterlab/theme-dark-extension/style/variables.css"

AA_TEXT = 4.5  # WCAG AA, body text.
AA_UI = 3.0  # WCAG AA, large text and non-text interface elements.

# Where code is read: active cell, inactive cell, and text selections.
EDITOR_BACKGROUNDS = ("--jp-layout-color0", "--jp-layout-color1")

# The tokens readers tell apart in ordinary code, with the bold/italic JupyterLab adds noted.
SYNTAX = {
    "--jp-mirror-editor-keyword-color": "bold",
    "--jp-mirror-editor-def-color": "",
    "--jp-mirror-editor-builtin-color": "",
    "--jp-mirror-editor-string-color": "",
    "--jp-mirror-editor-number-color": "",
    "--jp-mirror-editor-comment-color": "italic",
    "--jp-mirror-editor-operator-color": "bold",
    "--jp-mirror-editor-property-color": "",
    "--jp-mirror-editor-variable-color": "",
    "--jp-mirror-editor-meta-color": "",
    "--jp-mirror-editor-atom-color": "",
}
OTHER_CODE = (
    "--jp-mirror-editor-variable-2-color",
    "--jp-mirror-editor-string-2-color",
    "--jp-mirror-editor-tag-color",
    "--jp-mirror-editor-attribute-color",
    "--jp-mirror-editor-header-color",
    "--jp-mirror-editor-quote-color",
    "--jp-mirror-editor-link-color",
    "--jp-mirror-editor-error-color",
)
MIN_SYNTAX_DISTANCE = 0.04  # Between two tokens that differ in weight or slant too.
MIN_PLAIN_SYNTAX_DISTANCE = 0.05  # Between two tokens that differ by color alone.

# Foreground and background pairs, with the minimum contrast each must reach.
PAIRS = [
    # Interface text on the surfaces it appears on.
    *[
        (f"--jp-ui-font-color{font}", f"--jp-layout-color{layout}", AA_TEXT)
        for font in (0, 1)
        for layout in (0, 1, 2, 3)
    ],
    ("--jp-ui-font-color2", "--jp-layout-color0", AA_TEXT),
    ("--jp-ui-font-color2", "--jp-layout-color1", AA_TEXT),
    ("--jp-ui-font-color2", "--jp-layout-color2", AA_UI),
    ("--jp-ui-font-color3", "--jp-layout-color1", AA_UI),
    # Document text.
    ("--jp-content-font-color1", "--jp-layout-color0", AA_TEXT),
    ("--jp-content-font-color2", "--jp-layout-color0", AA_TEXT),
    ("--jp-content-link-color", "--jp-layout-color0", AA_TEXT),
    ("--jp-content-link-visited-color", "--jp-layout-color0", AA_TEXT),
    # Selected items print the inverse font on the brand color.
    ("--jp-ui-inverse-font-color1", "--jp-brand-color1", AA_TEXT),
    ("--jp-ui-inverse-font-color2", "--jp-brand-color2", AA_TEXT),
    # JupyterLab hard-codes white text on these.
    *[("white", f"--jp-accept-color-{state}", AA_TEXT) for state in ("normal", "hover", "active")],
    *[("white", f"--jp-warn-color-{state}", AA_TEXT) for state in ("normal", "hover", "active")],
    *[("white", f"--jp-reject-color-{state}", AA_TEXT) for state in ("normal", "hover", "active")],
    *[("white", f"--jp-completer-type-background{index}", AA_UI) for index in range(1, 11)],
    *[("white", f"--jp-collaborator-color{index}", AA_UI) for index in range(1, 8)],
    # Search matches.
    (
        "--jp-search-selected-match-color",
        "--jp-search-selected-match-background-color",
        AA_TEXT,
    ),
    (
        "--jp-search-unselected-match-color",
        "--jp-search-unselected-match-background-color",
        AA_TEXT,
    ),
    # State colors used as text and icons.
    *[
        (f"--jp-{state}-color1", f"--jp-layout-color{layout}", AA_TEXT)
        for state in ("warn", "error", "success", "info")
        for layout in (0, 1)
    ],
    # Things that must be seen, but are not text.
    ("--jp-focus-outline-color", "--jp-layout-color0", AA_UI),
    ("--jp-focus-outline-color", "--jp-layout-color2", AA_UI),
    ("--jp-editor-cursor-color", "--jp-layout-color0", AA_UI),
    ("--jp-brand-color1", "--jp-layout-color1", AA_UI),
    ("--jp-inverse-layout-color3", "--jp-layout-color1", AA_UI),
    ("--jp-cell-inprompt-font-color", "--jp-layout-color0", AA_TEXT),
    ("--jp-cell-outprompt-font-color", "--jp-layout-color0", AA_TEXT),
    ("--jp-cell-prompt-not-active-font-color", "--jp-layout-color0", AA_TEXT),
]


@pytest.fixture(params=VARIANTS)
def values(request: pytest.FixtureRequest) -> dict[str, str]:
    """
    Provide the custom properties of each variant in turn.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Carries the variant name.

    Returns
    -------
    dict of {str: str}
        The unresolved values by property name.

    """
    return load_variant(request.param)


def test_every_value_resolves(values: dict[str, str]) -> None:
    """Fail on a reference to a palette token or variable that does not exist."""
    missing = {
        reference
        for value in values.values()
        for reference in re.findall(r"var\((--[\w-]+)", value)
        if reference not in values
    }
    assert not missing


@pytest.mark.parametrize(("foreground", "background", "minimum"), PAIRS)
def test_contrast_pairs(
    values: dict[str, str], foreground: str, background: str, minimum: float
) -> None:
    """Check the text and interface pairs JupyterLab actually renders."""
    base = resolve("--jp-layout-color0", values)
    back = resolve(background, values).over(base)
    assert contrast(resolve(foreground, values).over(back), back) >= minimum


@pytest.mark.parametrize("token", [*SYNTAX, *OTHER_CODE])
@pytest.mark.parametrize("background", EDITOR_BACKGROUNDS)
def test_code_is_readable(values: dict[str, str], token: str, background: str) -> None:
    """Hold every syntax color to AA body text, on active and inactive cells alike."""
    assert contrast(resolve(token, values), resolve(background, values)) >= AA_TEXT


@pytest.mark.parametrize("token", SYNTAX)
def test_code_is_readable_when_selected(values: dict[str, str], token: str) -> None:
    """Keep selected code legible, in focused and unfocused editors."""
    base = resolve("--jp-layout-color0", values)
    for selection in ("--jp-editor-selected-focused-background", "--jp-editor-selected-background"):
        back = resolve(selection, values).over(base)
        assert contrast(resolve(token, values), back) >= AA_UI


def test_syntax_tokens_are_distinct(values: dict[str, str]) -> None:
    """Keep syntax colors apart, so that highlighting carries information."""
    for first, second in combinations(SYNTAX, 2):
        minimum = (
            MIN_PLAIN_SYNTAX_DISTANCE
            if not SYNTAX[first] and not SYNTAX[second]
            else MIN_SYNTAX_DISTANCE
        )
        gap = distance(resolve(first, values), resolve(second, values))
        assert gap >= minimum, f"{first} / {second}: {gap:.3f}"


def test_state_colors_are_distinct(values: dict[str, str]) -> None:
    """Keep warning, error, success and info recognizable from each other."""
    states = [f"--jp-{state}-color1" for state in ("warn", "error", "success", "info")]
    for first, second in combinations(states, 2):
        gap = distance(resolve(first, values), resolve(second, values))
        assert gap >= 0.08, f"{first} / {second}: {gap:.3f}"


def test_layout_gets_lighter_in_order(values: dict[str, str]) -> None:
    """Keep the elevation order of the surfaces, each visibly above the previous."""
    layers = [resolve(f"--jp-layout-color{index}", values) for index in range(5)]
    for lower, upper in pairwise(layers):
        assert upper.luminance() > lower.luminance()
        assert distance(lower, upper) >= 0.02


def test_font_colors_recede_in_order(values: dict[str, str]) -> None:
    """Keep the text hierarchy: lower numbers are stronger on the background."""
    base = resolve("--jp-layout-color0", values)
    for family in ("ui", "content"):
        ratios = [
            contrast(resolve(f"--jp-{family}-font-color{index}", values), base)
            for index in range(4)
        ]
        assert ratios == sorted(ratios, reverse=True)


def test_defines_every_upstream_variable(values: dict[str, str]) -> None:
    """Fail when JupyterLab adds a color or size this theme does not define yet."""
    if not UPSTREAM.exists():
        pytest.skip("run jlpm first: needs @jupyterlab/theme-dark-extension in node_modules")
    theme = (ROOT / "style" / "variables.css").read_text(encoding="utf-8")
    names = re.findall(r"^\s*(--jp-[\w-]+)\s*:", UPSTREAM.read_text(encoding="utf-8"), re.MULTILINE)
    missing = [name for name in names if f"{name}:" not in theme]
    assert not missing


def test_ansi_rules_outrank_jupyterlab() -> None:
    """Match the specificity of the JupyterLab ANSI rules, or they silently win."""
    css = (ROOT / "style" / "overrides.css").read_text(encoding="utf-8")
    rules = re.findall(r"^.*\.ansi-[a-z-]+.*$", css, re.MULTILINE)
    assert rules
    assert all(rule.startswith(".jp-RenderedText pre .ansi-") for rule in rules)
