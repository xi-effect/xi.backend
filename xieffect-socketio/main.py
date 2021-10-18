from flask import Flask, send_file  # , request
from flask_socketio import SocketIO, emit
# from flask_jwt_extended import verify_jwt_in_request, JWTManager, get_jwt_identity

# from xieffect.webhooks import send_discord_message, WebhookURLs

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
    # send_discord_message(WebhookURLs.HEROKU, "Heroku may be online")
    socketio.run(app, port=5050, debug=True)
