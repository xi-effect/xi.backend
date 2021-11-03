from flask_jwt_extended import jwt_required
from flask_socketio import Namespace


class MessagesNamespace(Namespace):
    @jwt_required()  # if not self.authenticate(request.args): raise ConnectionRefusedError("unauthorized!")
    def on_connect(self, _):
        pass

    @jwt_required()
    def on_disconnect(self):
        pass

    def on_send(self, data):
        pass

    def on_edit(self, data):
        pass

    def on_delete(self, data):
        pass

    def on_open(self, data):
        pass

    def on_close(self, data):
        pass
