"""Ipe Midnight: a comfy dark JupyterLab theme adapted from the Neovim colorscheme."""

try:
    from ._version import __version__
except ImportError:
    # Only reached when the package is imported from a source tree without being installed.
    import warnings

    warnings.warn(
        "Importing 'jupyterlab_ipe_midnight_theme' outside a proper installation.",
        stacklevel=2,
    )
    __version__ = "dev"

__all__ = ["__version__"]


def _jupyter_labextension_paths() -> list[dict[str, str]]:
    """
    Return the labextension paths JupyterLab uses to locate the theme.

    Returns
    -------
    list of dict of {str: str}
        One entry with the ``src`` directory of the prebuilt labextension,
        relative to this package, and its ``dest`` name in JupyterLab.

    Examples
    --------
    >>> from jupyterlab_ipe_midnight_theme import _jupyter_labextension_paths
    >>> _jupyter_labextension_paths()
    [{'src': 'labextension', 'dest': 'jupyterlab_ipe_midnight_theme'}]

    """
    return [{"src": "labextension", "dest": "jupyterlab_ipe_midnight_theme"}]
