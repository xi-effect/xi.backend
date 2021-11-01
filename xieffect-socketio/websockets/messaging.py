from flask_socketio import emit, Namespace

from setup import socketio


class TestNamespace(Namespace):
    def on_connect(self):
        pass

    def on_message(self, data):
        # verify_jwt_in_request()
        # print(request.headers)
        # print(get_jwt_identity())
        # print(data)
        emit("new_message", data, broadcast=True)
