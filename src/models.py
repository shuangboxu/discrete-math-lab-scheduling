from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional


@dataclass
class TimeSlot:
    """表示一段具体的上课时间，用于冲突检测。"""
    weeks: Set[int]
    weekday: int
    start_period: int
    end_period: int

    def conflicts_with(self, other: "TimeSlot") -> bool:
        # 周次有交集且星期相同，并且节次区间有重叠即视为冲突
        if not (self.weeks and other.weeks):
            return False
        if self.weekday != other.weekday:
            return False
        if not (self.weeks & other.weeks):
            return False
        return not (self.end_period < other.start_period or other.end_period < self.start_period)


@dataclass
class LabSession:
    """实验排课表中的一个具体实验组。"""
    session_id: int
    group_name: str
    project_name: str
    weeks: Set[int]
    weekday: int
    start_period: int
    end_period: int
    teacher: str
    capacity: int
    hours: int
    assigned_students: List[str] = field(default_factory=list)

    @property
    def remaining(self) -> int:
        return max(self.capacity - len(self.assigned_students), 0)

    @property
    def main_week(self) -> int:
        # 用于排序与离散度计算，取最小周次代表本次实验位置
        return min(self.weeks) if self.weeks else 0

    def to_timeslot(self) -> TimeSlot:
        return TimeSlot(self.weeks, self.weekday, self.start_period, self.end_period)


@dataclass
class Student:
    """学生实体，保存基本信息与课表。"""
    student_id: str
    name: str
    dept: Optional[str]
    major: Optional[str]
    clazz: Optional[str]
    required_hours: int
    busy_slots: List[TimeSlot]
    assigned: List[int] = field(default_factory=list)
    taken_projects: Set[str] = field(default_factory=set)

    def add_busy_slot(self, slot: TimeSlot) -> None:
        self.busy_slots.append(slot)

    def has_conflict(self, slot: TimeSlot, session_lookup: Dict[int, LabSession]) -> bool:
        # 与已有课程或已分配实验的时间冲突则返回 True
        for busy in self.busy_slots:
            if busy.conflicts_with(slot):
                return True
        for sid in self.assigned:
            if session_lookup[sid].to_timeslot().conflicts_with(slot):
                return True
        return False
