from datetime import datetime
from typing import Dict, List


class Filters:
    @classmethod
    def test_filters(cls):
        result = cls()
        result.binds = []
        result.hidden_courses = [18]
        result.started_courses = [0, 1, 2, 3]
        result.visit_datetimes = [
            datetime(2021, 3, 22, 17, 48, 0),
            datetime(1970, 3, 22, 17, 48, 0),
            datetime(2021, 2, 12, 12, 48, 0),
            datetime(2021, 3, 22, 17, 47, 59)
        ]
        result.starred_courses = [0, 2, 4, 12]
        result.pinned_courses = [0, 1, 5, 11]
        return result

    def __init__(self):
        self.binds: List[str] = list()
        self.hidden_courses: List[int] = list()
        self.pinned_courses: List[int] = list()
        self.starred_courses: List[int] = list()
        self.started_courses: List[int] = list()
        self.visit_datetimes: List[datetime] = list()

    def hide_course(self, code: int):
        self.hidden_courses.append(code)

    def unhide_course(self, code: int):
        if code in self.hidden_courses:
            self.hidden_courses.remove(code)

    def pin_course(self, code: int):
        self.pinned_courses.append(code)

    def unpin_course(self, code: int):
        if code in self.pinned_courses:
            self.pinned_courses.remove(code)

    def star_course(self, code: int):
        self.starred_courses.append(code)

    def unstar_course(self, code: int):
        if code in self.starred_courses:
            self.starred_courses.remove(code)

    def start_course(self, code: int):
        self.started_courses.append(code)
        self.visit_datetimes.append(datetime.utcnow())

    def update_binds(self, new_binds: List[str]) -> None:
        self.binds = new_binds

    def get_binds(self) -> List[str]:
        return self.binds

    def get_course_relation(self, course_id: int) -> Dict[str, bool]:
        return {"hidden": course_id in self.hidden_courses,
                "pinned": course_id in self.pinned_courses,
                "starred": course_id in self.starred_courses,
                "started": course_id in self.started_courses}

    def get_visit_date(self, code: int) -> float:
        try:
            i = self.started_courses.index(code)
            return self.visit_datetimes[i].timestamp()
        except ValueError:
            return -1
