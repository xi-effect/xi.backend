from flask_socketio import emit, Namespace
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity


class TestNamespace(Namespace):
    def on_connect(self, *_):
        verify_jwt_in_request()
        print(get_jwt_identity())
        emit("hey", "random letters")

    def on_hello(self, data):
        print(data)

    def on_message(self, data):
        # verify_jwt_in_request()
        # print(request.headers)
        # print(get_jwt_identity())
        # print(data)
        emit("new_message", data, broadcast=True)


class MessagesNamespace(Namespace):
    pass
