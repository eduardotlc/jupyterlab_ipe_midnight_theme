"""Provide the Ipe Midnight themes for the IPython terminal and Jupyter Console."""

import json
from importlib.resources import files
from typing import Any

from pygments.style import Style
from pygments.token import _TokenType, string_to_tokentype

THEME_NAMES = ("ipe-midnight", "ipe-midnight-soft", "ipe-midnight-cold")

# Jupyter Console hard-codes these over the Pygments style it is given.
_CONSOLE_PROMPT_TOKENS = ("Prompt", "PromptNum", "OutPrompt", "OutPromptNum", "RemotePrompt")


def load_theme(name: str) -> dict[str, Any]:
    """
    Read a terminal theme.

    Parameters
    ----------
    name : str
        One of `THEME_NAMES`.

    Returns
    -------
    dict
        The JSON theme, in the format IPython reads.

    Raises
    ------
    ValueError
        If `name` is not one of the themes.

    Examples
    --------
    >>> load_theme("ipe-midnight")["background"]
    '#101018'

    """
    if name not in THEME_NAMES:
        raise ValueError(f"unknown theme {name!r}, expected one of {THEME_NAMES}")
    resource = files(__package__) / "terminal_themes" / f"{name}.json"
    return json.loads(resource.read_text(encoding="utf-8"))


def theme_styles(name: str) -> dict[_TokenType, str]:
    """
    Return the style of each token of a terminal theme.

    Parameters
    ----------
    name : str
        One of `THEME_NAMES`.

    Returns
    -------
    dict of {pygments.token._TokenType: str}
        The Pygments style strings by token.

    Examples
    --------
    >>> from pygments.token import Keyword
    >>> theme_styles("ipe-midnight")[Keyword]
    '#7fb0ff bold'

    """
    extra_style = load_theme(name)["extra_style"]
    return {string_to_tokentype(token): style for token, style in extra_style.items()}


def console_prompt_styles(name: str) -> dict[_TokenType, str]:
    """
    Return the prompt styles to set as Jupyter Console style overrides.

    Parameters
    ----------
    name : str
        One of `THEME_NAMES`.

    Returns
    -------
    dict of {pygments.token._TokenType: str}
        A value for ``ZMQTerminalInteractiveShell.highlighting_style_overrides``.

    Examples
    --------
    >>> from pygments.token import Token
    >>> console_prompt_styles("ipe-midnight")[Token.Prompt]
    '#b18aff'

    """
    styles = theme_styles(name)
    return {
        token: styles[token]
        for token in (string_to_tokentype(token) for token in _CONSOLE_PROMPT_TOKENS)
    }


def register_ipython_themes() -> None:
    """
    Add the themes to the theme table of IPython versions without theme discovery.

    IPython 9.18 and later find the themes through their entry points, so this does nothing there.

    Examples
    --------
    >>> register_ipython_themes()  # doctest: +SKIP

    """
    from IPython.utils.PyColorize import Theme, theme_table

    if not isinstance(theme_table, dict):
        return
    for name in THEME_NAMES:
        symbols = load_theme(name)["symbols"]
        theme_table[name] = Theme(name, None, theme_styles(name), symbols=symbols)


class IpeMidnightStyle(Style):
    """Style Pygments output with the default Ipe Midnight variant."""

    name = "ipe-midnight"
    background_color = load_theme(name)["background"]
    styles = theme_styles(name)


class IpeMidnightSoftStyle(Style):
    """Style Pygments output with the soft Ipe Midnight variant."""

    name = "ipe-midnight-soft"
    background_color = load_theme(name)["background"]
    styles = theme_styles(name)


class IpeMidnightColdStyle(Style):
    """Style Pygments output with the cold Ipe Midnight variant."""

    name = "ipe-midnight-cold"
    background_color = load_theme(name)["background"]
    styles = theme_styles(name)
