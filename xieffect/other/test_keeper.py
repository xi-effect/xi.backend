from __future__ import annotations

from datetime import datetime
from enum import Enum
from math import sqrt, ceil
from random import randint
from typing import Union

from sqlalchemy import Column, select
from sqlalchemy.sql.sqltypes import Integer, String, DateTime, Text

from main import Base, Session


class ResultCodes(Enum):
    TimeLimitExceeded = 4
    MemoryLimitExceeded = 3
    RuntimeError = 2
    WrongAnswer = 1
    Accepted = 0


class TestPoint(Base):
    @staticmethod
    def test(session: Session):
        TestPoint.create(session, "S1", 0, "4 6", "6", 10)
        TestPoint.create(session, "S1", 1, "100 3", "100", 10)
        TestPoint.create(session, "S1", 2, "0 0", "0", 10)
        for i in range(5):
            a: int = randint(0, 999)
            b: int = randint(0, 999)
            TestPoint.create(session, "S1", i + 3, f"{a} {b}", str(max(a, b)), 10)
        TestPoint.create(session, "S1", 8, "999999999 999999998", "999999999", 10)
        TestPoint.create(session, "S1", 9, "999999999 999999999", "999999999", 10)

        temp: dict[int, int] = {1: 1, 2: 1}
        f1, f2 = 1, 1
        for i in range(3, 1001):
            f1, f2 = f2, f1 + f2
            temp[i] = f2
        inputs = [1, 10, 4, 342, 312, 12, 32, 1000, 85, 829]
        for i in range(10):
            TestPoint.create(session, "Q1", i, str(inputs[i]), str(temp[inputs[i]]), 10)

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
                TestPoint.create(session, "P1", i, "1", "1", 14)
            elif i == 7:
                TestPoint.create(session, "P1", i, "1000000", "49", 14)
            else:
                num = randint(2, 99999)
                TestPoint.create(session, "P1", i, str(num), str(div_count(num)), 9)

    __tablename__ = "test-points"

    task_name = Column(String(2), primary_key=True)
    test_id = Column(Integer, primary_key=True)

    input = Column(Text, nullable=False)
    output = Column(Text, nullable=False)
    points = Column(Integer, nullable=False)

    @classmethod
    def find_by_task(cls, session: Session, task_name: str) -> list[TestPoint]:
        return session.execute(select(cls).where(cls.task_name == task_name)).scalars().all()

    @classmethod
    def find_exact(cls, session: Session, task_name: str, test_id: int) -> Union[TestPoint, None]:
        return session.execute(select(cls).where(cls.task_name == task_name, cls.test_id == test_id)).scalars().first()

    @classmethod
    def create(cls, session: Session, task_name: str, test_id: int, inp: str,
               out: str, points: int) -> Union[TestPoint, None]:
        if cls.find_exact(session, task_name, test_id):
            return None
        new_test_point = cls(task_name=task_name, test_id=test_id, input=inp, output=out, points=points)
        session.add(new_test_point)
        return new_test_point

    @classmethod
    def create_next(cls, session: Session, task_name: str, inp: str, out: str, points: int) -> int:
        temp: list = cls.find_by_task(session, task_name)
        test_id: int = 0
        if len(temp):
            test_id = max(temp, key=lambda x: x.test_id).test_id + 1
        cls.create(session, task_name, test_id, inp, out, points)
        return test_id


class UserSubmissions(Base):
    __tablename__ = "user-submissions"

    user_id = Column(String(100), primary_key=True)
    task_name = Column(String(2), primary_key=True)
    id = Column(Integer, primary_key=True)

    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    code = Column(Integer, nullable=False)
    points = Column(Integer, nullable=False)
    failed = Column(Integer, nullable=False)

    @classmethod
    def find_group(cls, session: Session, user_id: str, task_name: str) -> list[UserSubmissions]:
        return session.execute(select(cls).where(cls.user_id == user_id, cls.task_name == task_name)).scalars().all()

    @classmethod
    def find_exact(cls, session: Session, user_id: str, task_name: str, submission_id: int) -> list[UserSubmissions]:
        return session.execute(select(cls).where(
            cls.user_id == user_id, cls.task_name == task_name, cls.id == submission_id)).scalars().all()

    @classmethod
    def create(cls, session: Session, user_id: str, task_name: str, submission_id: int, code: int, points: int,
               failed: int) -> Union[UserSubmissions, None]:
        if cls.find_exact(session, user_id, task_name, submission_id):
            return None
        new_submission = cls(user_id=user_id, task_name=task_name, code=code,
                             id=submission_id, points=points, failed=failed)
        session.add(new_submission)
        return new_submission

    @classmethod
    def create_next(cls, session: Session, user_id: str, task_name: str, code: int,
                    points: int, failed: int) -> Union[UserSubmissions, None]:
        temp: list = cls.find_group(session, user_id, task_name)
        current_id: int = 0
        if len(temp):
            current_id = max(temp, key=lambda x: x.id).id + 1
        return cls.create(session, user_id, task_name, current_id, code, points, failed)

    def to_json(self) -> dict:
        return {
            "date": str(self.date),
            "code": ResultCodes(self.code).name,
            "points": self.points,
            "failed": self.failed
        }
