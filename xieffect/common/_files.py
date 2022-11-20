from __future__ import annotations

from os import getcwd
from os.path import join, split

current_directory = getcwd()
dir_name, base_name = split(current_directory)
if base_name == "xieffect":  # pragma: no cover
    current_directory = dir_name


def absolute_path(path: str):
    return join(current_directory, path)


def open_file(path: str, mode: str = "r", **kwargs):
    if "b" not in mode:
        kwargs["encoding"] = "utf-8"
    return open(absolute_path(path), mode, **kwargs)  # noqa: WPS515 SIM115 ENC003
