from functools import wraps

from flask import request
from flask_fullstack.base import AbstractAbortMixin


class ProxyAuthMixin(AbstractAbortMixin):
    auth_required_error = 401, "Authorization required"

    @classmethod
    def get_user_id(cls) -> int | None:
        try:
            return int(request.headers.get("X-User-ID"))
        except TypeError:
            return None

    def proxy_authorizer(
        self,
        result_field_name: str = "user_id",
        optional: bool = False,
        use_user_id: bool = True,
    ):
        def proxy_authorizer_wrapper(function):
            @self.doc_abort(*self.auth_required_error)
            @wraps(function)
            def proxy_authorizer_inner(*args, **kwargs):
                user_id: int | None = self.get_user_id()

                if not optional and user_id is None:
                    self.abort(*self.auth_required_error)
                if use_user_id:
                    kwargs[result_field_name] = user_id
                return function(*args, **kwargs)

            return proxy_authorizer_inner

        return proxy_authorizer_wrapper
