"""Resolve the theme stylesheets to concrete colors and measure them."""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import hypot
from pathlib import Path

STYLE_DIR = Path(__file__).resolve().parent.parent / "style"
VARIANTS = ("default", "soft", "cold")

_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
_DECLARATION = re.compile(r"(--[\w-]+)\s*:\s*([^;]+);")
_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_VAR = re.compile(r"^var\((--[\w-]+)\)$")
_MIX = re.compile(r"^color-mix\(in srgb,\s*(.+?)\s+(\d+)%,\s*(.+)\)$")


@dataclass(frozen=True)
class Color:
    """
    An sRGB color with alpha, with channels between 0 and 1.

    Parameters
    ----------
    red, green, blue : float
        The channels.
    alpha : float, default 1.0
        The opacity.

    Examples
    --------
    >>> Color(1.0, 0.0, 0.0).alpha
    1.0

    """

    red: float
    green: float
    blue: float
    alpha: float = 1.0

    @classmethod
    def from_hex(cls, value: str) -> Color:
        """
        Build a color from ``#rrggbb``.

        Parameters
        ----------
        value : str
            The hexadecimal color.

        Returns
        -------
        Color
            The opaque color.

        Examples
        --------
        >>> Color.from_hex("#ff0000").red
        1.0

        """
        return cls(*(int(value[i : i + 2], 16) / 255 for i in (1, 3, 5)))

    def over(self, background: Color) -> Color:
        """
        Composite this color over an opaque background.

        Parameters
        ----------
        background : Color
            The color underneath.

        Returns
        -------
        Color
            The opaque visible color.

        Examples
        --------
        >>> Color(1.0, 1.0, 1.0, 0.5).over(Color(0.0, 0.0, 0.0)).red
        0.5

        """
        keep = 1 - self.alpha
        return Color(
            self.red * self.alpha + background.red * keep,
            self.green * self.alpha + background.green * keep,
            self.blue * self.alpha + background.blue * keep,
        )

    def _linear(self) -> tuple[float, float, float]:
        """Return the channels in linear light."""
        return tuple(
            c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
            for c in (self.red, self.green, self.blue)
        )

    def luminance(self) -> float:
        """
        Return the WCAG relative luminance.

        Returns
        -------
        float
            The luminance, between 0 and 1.

        Examples
        --------
        >>> Color.from_hex("#ffffff").luminance()
        1.0

        """
        red, green, blue = self._linear()
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue

    def oklab(self) -> tuple[float, float, float]:
        """
        Return the color in the perceptual OKLab space.

        Returns
        -------
        tuple of float
            The ``L``, ``a`` and ``b`` coordinates.

        Examples
        --------
        >>> round(Color.from_hex("#ffffff").oklab()[0], 3)
        1.0

        """
        red, green, blue = self._linear()
        long = (0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue) ** (1 / 3)
        medium = (0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue) ** (1 / 3)
        short = (0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue) ** (1 / 3)
        return (
            0.2104542553 * long + 0.7936177850 * medium - 0.0040720468 * short,
            1.9779984951 * long - 2.4285922050 * medium + 0.4505937099 * short,
            0.0259040371 * long + 0.7827717662 * medium - 0.8086757660 * short,
        )


def contrast(first: Color, second: Color) -> float:
    """
    Compute the WCAG contrast ratio of two opaque colors.

    Parameters
    ----------
    first, second : Color
        The colors to compare, in any order.

    Returns
    -------
    float
        The ratio, from 1 to 21.

    Examples
    --------
    >>> round(contrast(Color.from_hex("#000000"), Color.from_hex("#ffffff")), 1)
    21.0

    """
    high, low = sorted((first.luminance(), second.luminance()), reverse=True)
    return (high + 0.05) / (low + 0.05)


def distance(first: Color, second: Color) -> float:
    """
    Compute the perceptual OKLab distance of two opaque colors.

    Parameters
    ----------
    first, second : Color
        The colors to compare.

    Returns
    -------
    float
        The distance: ``0`` is identical, ``0.08`` is clearly different at a glance.

    Examples
    --------
    >>> distance(Color.from_hex("#101018"), Color.from_hex("#101018"))
    0.0

    """
    return hypot(*(a - b for a, b in zip(first.oklab(), second.oklab(), strict=True)))


def declarations(selector_filter: str, css: str) -> dict[str, str]:
    """
    Collect the custom properties of the rules whose selector matches exactly.

    Parameters
    ----------
    selector_filter : str
        The selector to look for.
    css : str
        The stylesheet source.

    Returns
    -------
    dict of {str: str}
        Values by property name, with whitespace normalized.

    Examples
    --------
    >>> declarations(":root", ":root { --a: #fff; } .b { --a: #000; }")
    {'--a': '#fff'}

    """
    found: dict[str, str] = {}
    for selector, body in _RULE.findall(_COMMENT.sub("", css)):
        if selector.strip() == selector_filter:
            for name, value in _DECLARATION.findall(body):
                # Formatters may break long values over lines inside the parentheses.
                found[name] = re.sub(
                    r"\(\s+|\s+\)", lambda m: m[0].strip(), " ".join(value.split())
                )
    return found


def load_variant(variant: str) -> dict[str, str]:
    """
    Return the custom properties in effect for a theme variant.

    Parameters
    ----------
    variant : str
        One of `VARIANTS`.

    Returns
    -------
    dict of {str: str}
        The unresolved values by property name.

    Examples
    --------
    >>> load_variant("soft")["--ipe-bg"]
    '#111117'

    """
    scoped = f":root[data-ipe-variant='{variant}']"
    values: dict[str, str] = {}
    for name in ("palette.css", "variables.css"):
        css = (STYLE_DIR / name).read_text(encoding="utf-8")
        values |= declarations(":root", css) | declarations(".jp-Completer", css)
        values |= declarations(scoped, css)
    return values


def resolve(value: str, values: dict[str, str]) -> Color:
    """
    Resolve a CSS color expression to a concrete color.

    Supports what the theme uses: hex colors, keywords, ``var()`` and ``color-mix()``.

    Parameters
    ----------
    value : str
        The expression, or a custom property name such as ``--jp-layout-color0``.
    values : dict of {str: str}
        The custom properties in effect.

    Returns
    -------
    Color
        The color, possibly translucent.

    Examples
    --------
    >>> resolve("color-mix(in srgb, var(--a) 50%, black)", {"--a": "#ffffff"}).alpha
    1.0

    """
    value = value.strip()
    if value.startswith("--"):
        return resolve(values[value], values)
    if value.startswith("#"):
        return Color.from_hex(value)
    keywords = {
        "black": Color(0.0, 0.0, 0.0),
        "white": Color(1.0, 1.0, 1.0),
        "transparent": Color(0.0, 0.0, 0.0, 0.0),
    }
    if value in keywords:
        return keywords[value]
    if match := _VAR.match(value):
        return resolve(values[match[1]], values)
    if match := _MIX.match(value):
        return _mix(resolve(match[1], values), int(match[2]) / 100, resolve(match[3], values))
    raise ValueError(f"unsupported color expression: {value}")


def _mix(first: Color, weight: float, second: Color) -> Color:
    """
    Apply the premultiplied interpolation of CSS ``color-mix(in srgb, ...)``.

    Parameters
    ----------
    first : Color
        The first color.
    weight : float
        The share of `first`, between 0 and 1.
    second : Color
        The second color.

    Returns
    -------
    Color
        The mixture.

    Examples
    --------
    >>> _mix(Color(1.0, 1.0, 1.0), 0.25, Color(0.0, 0.0, 0.0, 0.0)).alpha
    0.25

    """
    alpha = first.alpha * weight + second.alpha * (1 - weight)
    channels = (
        (a * first.alpha * weight + b * second.alpha * (1 - weight)) / alpha
        for a, b in zip(
            (first.red, first.green, first.blue),
            (second.red, second.green, second.blue),
            strict=True,
        )
    )
    return Color(*channels, alpha)
