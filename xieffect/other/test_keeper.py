from datetime import datetime
from enum import Enum
from random import randint
from typing import Dict
from math import sqrt, ceil

from main import db


class ResultCodes(Enum):
    TimeLimitExceeded = 4
    MemoryLimitExceeded = 3
    RuntimeError = 2
    WrongAnswer = 1
    Accepted = 0


class TestPoint(db.Model):
    @staticmethod
    def test():
        TestPoint.create("S1", 0, "4 6", "6", 10)
        TestPoint.create("S1", 1, "100 3", "100", 10)
        TestPoint.create("S1", 2, "0 0", "0", 10)
        for i in range(5):
            a: int = randint(0, 999)
            b: int = randint(0, 999)
            TestPoint.create("S1", i + 3, f"{a} {b}", str(max(a, b)), 10)
        TestPoint.create("S1", 8, "999999999 999999998", "999999999", 10)
        TestPoint.create("S1", 9, "999999999 999999999", "999999999", 10)

        temp: Dict[int, int] = {1: 1, 2: 1}
        f1, f2 = 1, 1
        for i in range(3, 1001):
            f1, f2 = f2, f1 + f2
            temp[i] = f2
        inputs = [1, 10, 4, 342, 312, 12, 32, 1000, 85, 829]
        for i in range(10):
            TestPoint.create("Q1", i, str(inputs[i]), str(temp[inputs[i]]), 10)

        def div_count(n):
            count = 2
            for i in range(2, ceil(sqrt(n))):
                if n % i == 0:
                    count += 2
            if sqrt(n) % 1 == 0:
                count += 1
            return count

        for i in range(9):
            if i == 5:
                TestPoint.create("P1", i, "1", "1", 14)
            elif i == 7:
                TestPoint.create("P1", i, "1000000", "49", 14)
            else:
                num = randint(2, 99999)
                TestPoint.create("P1", i, str(num), str(div_count(num)), 9)

    task_name = db.Column(db.String(2), primary_key=True)
    test_id = db.Column(db.Integer, primary_key=True)

    input = db.Column(db.Text, nullable=False)
    output = db.Column(db.Text, nullable=False)
    points = db.Column(db.Integer, nullable=False)

    @classmethod
    def find_by_task(cls, task_name: str) -> list:
        return cls.query.filter_by(task_name=task_name).all()

    @classmethod
    def find_exact(cls, task_name: str, test_id: int):
        return cls.query.filter_by(task_name=task_name, test_id=test_id).first()

    @classmethod
    def create(cls, task_name: str, test_id: int, inp: str, out: str, points: int):
        if cls.find_exact(task_name, test_id):
            return None
        new_test_point = cls(task_name=task_name, test_id=test_id, input=inp, output=out, points=points)
        db.session.add(new_test_point)
        db.session.commit()
        return new_test_point

    @classmethod
    def create_next(cls, task_name: str, inp: str, out: str, points: int) -> int:
        temp: list = cls.find_by_task(task_name)
        test_id: int = 0
        if len(temp):
            test_id = max(temp, key=lambda x: x.test_id).test_id + 1
        cls.create(task_name, test_id, inp, out, points)
        return test_id


class UserSubmissions(db.Model):
    user_id = db.Column(db.String(100), primary_key=True)
    task_name = db.Column(db.String(2), primary_key=True)
    id = db.Column(db.Integer, primary_key=True)

    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    code = db.Column(db.Integer, nullable=False)
    points = db.Column(db.Integer, nullable=False)
    failed = db.Column(db.Integer, nullable=False)

    @classmethod
    def find_group(cls, user_id: str, task_name: str) -> list:
        return cls.query.filter_by(user_id=user_id, task_name=task_name).all()

    @classmethod
    def find_exact(cls, user_id: str, task_name: str, submission_id: int):
        return cls.query.filter_by(user_id=user_id, task_name=task_name, id=submission_id).all()

    @classmethod
    def create(cls, user_id: str, task_name: str, submission_id: int, code: int, points: int, failed: int):
        if cls.find_exact(user_id, task_name, submission_id):
            return None
        new_submission = cls(user_id=user_id, task_name=task_name, code=code,
                             id=submission_id, points=points, failed=failed)
        db.session.add(new_submission)
        db.session.commit()
        return new_submission

    @classmethod
    def create_next(cls, user_id: str, task_name: str, code: int, points: int, failed: int):
        temp: list = cls.find_group(user_id, task_name)
        current_id: int = 0
        if len(temp):
            current_id = max(temp, key=lambda x: x.id).id + 1
        return cls.create(user_id, task_name, current_id, code, points, failed)

    def to_json(self) -> dict:
        return {
            "date": str(self.date),
            "code": ResultCodes(self.code).name,
            "points": self.points,
            "failed": self.failed
        }