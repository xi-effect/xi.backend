from os import path
from subprocess import call, TimeoutExpired
from typing import IO

from flask import request, send_file
from flask_restful import Resource

from api_resources.base.checkers import jwt_authorizer
from api_resources.base.discorder import send_discord_message, WebhookURLs
from database import User, TestPoint, UserSubmissions, ResultCodes


def check_one(inp: str, out: str) -> ResultCodes:
    fin: IO = open("oct/input", "wb")
    fin.write(inp.encode("utf-8"))
    fout: IO = open("oct/output", "wb")
    ferr: IO = open("oct/error", "wb")

    try:
        call(["python3", "oct/submission.py"], stdin=fin, stdout=fout, stderr=ferr, timeout=1)
    except TimeoutExpired:
        return ResultCodes.TimeLimitExceeded

    if path.exists("oct/error") and path.getsize("oct/error"):
        return ResultCodes.RuntimeError
    if not path.exists("oct/output"):
        return ResultCodes.WrongAnswer

    map(lambda x: x.close(), [fin, fout, ferr])

    with open("oct/output", "rb") as f:
        result: str = f.read().decode("utf-8")
    return ResultCodes.Accepted if result.split() == out.split() else ResultCodes.WrongAnswer


class SubmitTask(Resource):  # POST (JWT) /tasks/<task_name>/attempts/new/
    # parser: reqparse.RequestParser = reqparse.RequestParser()
    # parser.add_argument("", type=FileStorage, location="file_system", required=True)

    @jwt_authorizer(User)
    def post(self, task_name: str, user: User):
        if not TestPoint.find_by_task(task_name):
            return {"a": "Task doesn't exist"}

        with open("oct/submission.py", "wb") as f:
            f.write(request.data)

        test: TestPoint
        points: int = 0
        code: int = 0
        failed: int = -1

        for test in TestPoint.find_by_task(task_name):
            code = check_one(test.input, test.output).value
            if code == ResultCodes.Accepted.value:
                points += test.points
            else:
                failed = test.test_id
                break

        send_discord_message(WebhookURLs.WEIRDO, f"Hey, {user.email} just send in a task submission!\n"
                                         f"Task: {task_name}, code: {ResultCodes(code).name}, "
                                         f"points: {points}, failed after: {failed}")

        return UserSubmissions.create_next(user.id, task_name, code, points, failed).to_json()


class GetTaskSummary(Resource):  # GET (JWT) /tasks/<task_name>/attempts/all/
    @jwt_authorizer(User)
    def get(self, task_name: str, user: User):
        if not TestPoint.find_by_task(task_name):
            return {"a": "Task doesn't exist"}

        result: list = UserSubmissions.find_group(user.id, task_name)
        if not result:
            return []
        else:
            return list(map(lambda x: x.to_json(), result))


class UpdateRequest(Resource):  # /oct/update/
    def get(self):
        return send_file(r"OlimpCheck.jar")


pass  # api for creating remotely

# if __name__ == "__main__":
#     with open("submission.py", "wb") as f:
#         f.write("".encode("utf-8"))
#     print(check_one("", "3 4 6"))
