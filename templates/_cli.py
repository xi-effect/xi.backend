from __future__ import annotations

from functools import wraps

from click import echo, argument, option, File
from flask import Blueprint, current_app

from common import sessionmaker
from moderation import permission_index

controller = Blueprint("...", __name__)


def cli_command(use_session: bool = True):
    def cli_command_wrapper(function):
        @controller.cli.command(function.__name__.replace("_", "-"))
        @wraps(function)
        def cli_command_inner(*args, **kwargs):
            # may be additional checks
            return function(*args, **kwargs)

        return sessionmaker.with_begin(cli_command_inner) if use_session else cli_command_inner

    return cli_command_wrapper
