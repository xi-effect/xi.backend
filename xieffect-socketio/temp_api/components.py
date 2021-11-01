from functools import wraps

from flask_restx.reqparse import RequestParser


def argument_parser(namespace, parser: RequestParser):
    """
    - Parses request parameters and adds them to kwargs used to call the decorated function.
    - Automatically updates endpoint's parameters with arguments from the parser.
    """

    def argument_wrapper(function):
        @namespace.expect(parser)
        @wraps(function)
        def argument_inner(*args, **kwargs):
            kwargs.update(parser.parse_args())
            return function(*args, **kwargs)

        return argument_inner

    return argument_wrapper
