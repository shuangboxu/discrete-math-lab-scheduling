from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Set

import pandas as pd

from .models import LabSession, Student, TimeSlot
from .utils import make_timeslot, parse_period_range, parse_weekday, parse_weeks


def _clean_str(value: Optional[str]) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def load_lab_sessions(path: str) -> List[LabSession]:
    df = pd.read_excel(path)
    sessions: List[LabSession] = []
    for idx, row in df.iterrows():
        weeks = parse_weeks(row.get("上课周次"))
        weekday = parse_weekday(row.get("上课星期"))
        start_period, _ = parse_period_range(row.get("开始节次"))
        end_period, _ = parse_period_range(row.get("结束节次"))
        teacher = _clean_str(row.get("上课教师"))
        capacity = int(row.get("实验人数", 0)) if not pd.isna(row.get("实验人数")) else 0
        hours = int(row.get("课时", 0)) if not pd.isna(row.get("课时")) else 0
        session = LabSession(
            session_id=idx,
            group_name=_clean_str(row.get("实验组名称")),
            project_name=_clean_str(row.get("实验项目名称")),
            weeks=weeks,
            weekday=weekday or 0,
            start_period=start_period or 0,
            end_period=end_period or 0,
            teacher=teacher,
            capacity=capacity,
            hours=hours,
        )
        sessions.append(session)
    return sessions


def _busy_from_lecture_schedule(df: pd.DataFrame) -> Dict[str, List[TimeSlot]]:
    busy: Dict[str, List[TimeSlot]] = defaultdict(list)
    for _, row in df.iterrows():
        sid = _clean_str(row.get("学号"))
        if not sid:
            continue
        weeks = parse_weeks(row.get("周次"))
        weekday = parse_weekday(row.get("上课星期"))
        start, end = parse_period_range(row.get("上课节次"))
        slot = make_timeslot(weeks, weekday or 0, start or 0, end or 0)
        if slot:
            busy[sid].append(slot)
    return busy


def _collect_meta_from_lecture(df: pd.DataFrame) -> Dict[str, Dict[str, str]]:
    meta: Dict[str, Dict[str, str]] = {}
    for _, row in df.iterrows():
        sid = _clean_str(row.get("学号"))
        if not sid:
            continue
        meta[sid] = {
            "name": _clean_str(row.get("姓名（可能有重名）")),
            "dept": _clean_str(row.get("院系名称")),
            "major": _clean_str(row.get("专业名称")),
            "clazz": _clean_str(row.get("班级名称")),
        }
    return meta


def load_students(
    required_hours: int,
    lecture_schedule_path: str,
) -> Dict[str, Student]:
    lecture_df = pd.read_excel(lecture_schedule_path)

    busy = _busy_from_lecture_schedule(lecture_df)
    meta = _collect_meta_from_lecture(lecture_df)

    students: Dict[str, Student] = {}
    all_ids: Set[str] = set(busy.keys()) | set(meta.keys())
    for sid in all_ids:
        info = meta.get(sid, {})
        student = Student(
            student_id=sid,
            name=info.get("name", ""),
            dept=info.get("dept", ""),
            major=info.get("major", ""),
            clazz=info.get("clazz", ""),
            required_hours=required_hours,
            busy_slots=busy.get(sid, []),
        )
        students[sid] = student
    return students
