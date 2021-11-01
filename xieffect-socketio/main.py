from flask import Flask, send_file  # , request
from flask_socketio import SocketIO, emit
# from flask_jwt_extended import verify_jwt_in_request, JWTManager, get_jwt_identity

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")


@app.route("/")
def index():
    return send_file("index.html")


@socketio.on('connect')
def connect():
    pass


@socketio.on("message")
def handle_message(data):
    # verify_jwt_in_request()
    # print(request.headers)
    # print(get_jwt_identity())
    # print(data)
    emit("new_message", data, broadcast=True)


if __name__ == "__main__":
    socketio.run(app, debug=True)
