"""Check the IPython and Jupyter Console themes on every variant."""

import re
from itertools import combinations
from pathlib import Path

import pytest
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments.token import Comment, Keyword, Name, Number, Operator, String, Token
from theme_css import VARIANTS, Color, contrast, distance, load_variant, resolve

from jupyterlab_ipe_midnight_theme.terminal import (
    THEME_NAMES,
    IpeMidnightColdStyle,
    IpeMidnightSoftStyle,
    IpeMidnightStyle,
    console_prompt_styles,
    load_theme,
    register_ipython_themes,
    theme_styles,
)

ROOT = Path(__file__).resolve().parent.parent
AA_TEXT = 4.5
AA_UI = 3.0

THEME_BY_VARIANT = dict(zip(VARIANTS, THEME_NAMES, strict=True))

# Theme token -> JupyterLab variable that must hold the same color.
SHARED_ROLES = {
    "Keyword": "--jp-mirror-editor-keyword-color",
    "Keyword.Constant": "--jp-mirror-editor-atom-color",
    "Number": "--jp-mirror-editor-number-color",
    "Name.Function": "--jp-mirror-editor-def-color",
    "Name": "--jp-mirror-editor-variable-color",
    "Name.Builtin.Pseudo": "--jp-mirror-editor-variable-2-color",
    "Name.Namespace": "--jp-mirror-editor-variable-3-color",
    "Punctuation": "--jp-mirror-editor-punctuation-color",
    "Name.Attribute": "--jp-mirror-editor-property-color",
    "Operator": "--jp-mirror-editor-operator-color",
    "Comment": "--jp-mirror-editor-comment-color",
    "String": "--jp-mirror-editor-string-color",
    "String.Doc": "--jp-mirror-editor-string-2-color",
    "Name.Decorator": "--jp-mirror-editor-meta-color",
    "Name.Builtin": "--jp-mirror-editor-builtin-color",
    "Name.Tag": "--jp-mirror-editor-tag-color",
    "Generic.Heading": "--jp-mirror-editor-header-color",
    "Error": "--jp-mirror-editor-error-color",
    "Prompt": "--jp-cell-inprompt-font-color",
    "OutPrompt": "--jp-cell-outprompt-font-color",
    "ExcName": "--jp-error-color1",
    "Line": "--jp-warn-color1",
    "Generic.Inserted": "--jp-success-color1",
    "Filename": "--jp-info-color1",
}

# The tokens readers tell apart in ordinary code.
SYNTAX = (Keyword, Name.Function, Name.Builtin, String, Number, Comment, Operator, Name)
MIN_SYNTAX_DISTANCE = 0.04

# Tracebacks are always printed with the 256 color palette, whatever the terminal supports.
MIN_256_CONTRAST = AA_UI

_HEX = re.compile(r"(?<!bg:)#[0-9a-f]{6}")
_ANY_HEX = re.compile(r"#[0-9a-f]{6}")


def foreground(style: str) -> Color | None:
    """
    Return the foreground of a Pygments style string.

    Parameters
    ----------
    style : str
        The style string.

    Returns
    -------
    Color or None
        The foreground, if the style sets one.

    Examples
    --------
    >>> foreground("#ff0000 bold").red
    1.0
    >>> foreground("bg:#ff0000") is None
    True

    """
    match = _HEX.search(style)
    return Color.from_hex(match[0]) if match else None


@pytest.fixture(params=VARIANTS)
def variant(request: pytest.FixtureRequest) -> str:
    """
    Provide each variant in turn.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Carries the variant name.

    Returns
    -------
    str
        The name of the variant.

    """
    return request.param


def test_theme_colors_come_from_the_palette(variant: str) -> None:
    """Fail when a terminal theme uses a color outside the palette of its variant."""
    values = load_variant(variant)
    palette = {value for name, value in values.items() if name.startswith("--ipe-")}
    theme = load_theme(THEME_BY_VARIANT[variant])
    assert theme["name"] == THEME_BY_VARIANT[variant]
    assert theme["background"] == values["--ipe-bg"]
    used = set(_ANY_HEX.findall(" ".join(theme["extra_style"].values())))
    assert used <= palette, sorted(used - palette)


@pytest.mark.parametrize(("token", "css"), SHARED_ROLES.items())
def test_colors_match_jupyterlab(variant: str, token: str, css: str) -> None:
    """Give each terminal role the color of the same role in JupyterLab."""
    extra_style = load_theme(THEME_BY_VARIANT[variant])["extra_style"]
    assert foreground(extra_style[token]) == resolve(css, load_variant(variant))


def test_text_is_readable(variant: str) -> None:
    """Hold every terminal color to AA body text on the background of the variant."""
    theme = load_theme(THEME_BY_VARIANT[variant])
    background = Color.from_hex(theme["background"])
    for token, style in theme["extra_style"].items():
        if (color := foreground(style)) is not None:
            assert contrast(color, background) >= AA_TEXT, token


def test_code_is_readable_on_traceback_highlight(variant: str) -> None:
    """Keep code legible on the background that marks the failing expression."""
    theme = load_theme(THEME_BY_VARIANT[variant])
    extra_style = theme["extra_style"]
    highlight = Color.from_hex(extra_style["TbHighlight"].removeprefix("bg:"))
    for token, style in extra_style.items():
        if (color := foreground(style)) is not None:
            assert contrast(color, highlight) >= AA_UI, token


def test_syntax_tokens_are_distinct(variant: str) -> None:
    """Keep syntax colors apart, so that highlighting carries information."""
    styles = theme_styles(THEME_BY_VARIANT[variant])
    for first, second in combinations(SYNTAX, 2):
        gap = distance(foreground(styles[first]), foreground(styles[second]))
        assert gap >= MIN_SYNTAX_DISTANCE, f"{first} / {second}: {gap:.3f}"


def test_tokens_stay_readable_in_256_colors(variant: str) -> None:
    """Keep the approximated colors readable, as tracebacks and the fallback mode use them."""
    theme = load_theme(THEME_BY_VARIANT[variant])
    background = Color.from_hex(theme["background"])
    formatter = Terminal256Formatter(style=_STYLES[variant])
    for token, style in theme["extra_style"].items():
        if foreground(style) is None:
            continue
        code = int(re.search(r"38;5;(\d+)", formatter.style_string[str(_token(token))][0])[1])
        red, green, blue = formatter.xterm_colors[code]
        color = Color(red / 255, green / 255, blue / 255)
        assert contrast(color, background) >= MIN_256_CONTRAST, token


def test_pygments_styles_are_complete() -> None:
    """Expose one Pygments style per theme, under the name of the theme."""
    assert {style.name for style in _STYLES.values()} == set(THEME_NAMES)
    for variant, style in _STYLES.items():
        theme = load_theme(THEME_BY_VARIANT[variant])
        assert style.background_color == theme["background"]
        assert style.style_for_token(Keyword)["bold"]
        assert not style.style_for_token(Keyword.Constant)["bold"]


def test_entry_points_name_every_theme() -> None:
    """Advertise every theme to IPython and Pygments."""
    tomllib = pytest.importorskip("tomllib")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    entry_points = project["entry-points"]
    assert set(entry_points["ipython.themes"]) == set(THEME_NAMES)
    assert set(entry_points["pygments.styles"]) == set(THEME_NAMES)
    for name, target in entry_points["pygments.styles"].items():
        assert _STYLES_BY_CLASS[target.rpartition(":")[2]].name == name


def test_console_prompt_styles_cover_hard_coded_tokens() -> None:
    """Override every prompt color that Jupyter Console hard-codes."""
    assert set(console_prompt_styles("ipe-midnight")) == {
        Token.Prompt,
        Token.PromptNum,
        Token.OutPrompt,
        Token.OutPromptNum,
        Token.RemotePrompt,
    }


def test_register_ipython_themes_makes_every_theme_available() -> None:
    """Make the themes loadable by name, with or without IPython theme discovery."""
    pytest.importorskip("IPython", minversion="9")
    from IPython.utils.PyColorize import theme_table

    register_ipython_themes()
    if not isinstance(theme_table, dict) and "ipe-midnight" not in theme_table:
        pytest.skip("the package is not installed, so IPython cannot discover its entry points")
    for name in THEME_NAMES:
        assert "\x1b[" in theme_table[name].format([(Keyword, "def")])


def test_unknown_theme_is_rejected() -> None:
    """Report an unknown theme name clearly."""
    with pytest.raises(ValueError, match="unknown theme"):
        load_theme("ipe-noon")


_STYLES = {
    "default": IpeMidnightStyle,
    "soft": IpeMidnightSoftStyle,
    "cold": IpeMidnightColdStyle,
}
_STYLES_BY_CLASS = {style.__name__: style for style in _STYLES.values()}


def _token(dotted: str) -> object:
    """
    Resolve a dotted theme token.

    Parameters
    ----------
    dotted : str
        The dotted token path.

    Returns
    -------
    pygments.token._TokenType
        The token.

    Examples
    --------
    >>> _token("Name.Function") is Name.Function
    True

    """
    node = Token
    for part in dotted.split("."):
        node = getattr(node, part)
    return node
