from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .models import LabSession, Student

WEEKDAY_LABEL = {
    1: "星期一",
    2: "星期二",
    3: "星期三",
    4: "星期四",
    5: "星期五",
    6: "星期六",
    7: "星期日",
}


class Scheduler:
    """简单的贪心排课器，满足 A 类硬约束并兼顾部分 B 类优化。"""

    def __init__(
        self,
        students: Dict[str, Student],
        sessions: List[LabSession],
        required_hours: int = 30,
        seed: int = 42,
        w_occupancy: float = 1.0,
        w_class: float = 1.0,
        w_hetero: float = 0.5,
        w_spread: float = 0.2,
        w_slot: float = 0.1,
        swap_iterations: int = 200,
    ) -> None:
        self.students = students
        self.sessions = sessions
        self.required_hours = required_hours
        self.session_lookup: Dict[int, LabSession] = {s.session_id: s for s in sessions}
        self.w_occupancy = w_occupancy
        self.w_class = w_class
        self.w_hetero = w_hetero
        self.w_spread = w_spread
        self.w_slot = w_slot
        self.swap_iterations = swap_iterations
        random.seed(seed)

    def _student_hours(self, student: Student) -> int:
        return sum(self.session_lookup[sid].hours for sid in student.assigned)

    def _target_hours(self, student: Student) -> int:
        return student.required_hours or self.required_hours

    def _same_slot_count(self, student: Student, session: LabSession) -> int:
        # 同一学生已分配的课程中，与当前时段相同的数量，用于 B9 偏好
        count = 0
        new_slot = session.to_timeslot()
        for sid in student.assigned:
            other_slot = self.session_lookup[sid].to_timeslot()
            if (
                other_slot.weekday == new_slot.weekday
                and other_slot.start_period == new_slot.start_period
                and other_slot.end_period == new_slot.end_period
            ):
                count += 1
        return count

    def _spread_distance(self, student: Student, session: LabSession) -> int:
        # 计算与学生已分配课程在周次上的最小距离，用于 B7 均匀分布
        if not student.assigned:
            return 0
        target_week = session.main_week
        distances = [abs(target_week - self.session_lookup[sid].main_week) for sid in student.assigned]
        return min(distances) if distances else 0

    def _class_match_ratio(self, student: Student, session: LabSession) -> float:
        # 同班/同专业已在该组的占比，鼓励聚类
        if not session.assigned_students:
            return 0.0
        same = 0
        for sid in session.assigned_students:
            peer = self.students.get(sid)
            if not peer:
                continue
            if peer.clazz and student.clazz and peer.clazz == student.clazz:
                same += 1
            elif peer.major and student.major and peer.major == student.major:
                same += 1
        return same / (len(session.assigned_students) + 1)

    def _hetero_level(self, session: LabSession, incoming: Optional[Student] = None) -> float:
        # 组内班级/专业的异质度（比例越高越“杂”）
        classes = set()
        majors = set()
        for sid in session.assigned_students:
            peer = self.students.get(sid)
            if not peer:
                continue
            if peer.clazz:
                classes.add(peer.clazz)
            if peer.major:
                majors.add(peer.major)
        if incoming:
            if incoming.clazz:
                classes.add(incoming.clazz)
            if incoming.major:
                majors.add(incoming.major)
        size = len(session.assigned_students) + (1 if incoming else 0)
        if size == 0:
            return 0.0
        distinct = max(len(classes), len(majors))
        return distinct / size

    def _score(self, student: Student, session: LabSession) -> Tuple[float, float, float, float]:
        occupancy_ratio = (session.capacity - session.remaining) / session.capacity if session.capacity else 1.0
        spread_bonus = -self._spread_distance(student, session)  # 越分散分数越低（更优）
        class_bonus = -self.w_class * self._class_match_ratio(student, session)
        hetero_penalty = self.w_hetero * self._hetero_level(session, student)
        slot_bonus = -self.w_slot * self._same_slot_count(student, session)
        return (
            occupancy_ratio * self.w_occupancy,
            class_bonus + hetero_penalty,
            self.w_spread * spread_bonus,
            slot_bonus,
        )

    def _candidate_sessions(self, student: Student) -> List[LabSession]:
        candidates: List[LabSession] = []
        for session in self.sessions:
            if session.remaining <= 0:
                continue
            if session.project_name in student.taken_projects:
                continue
            slot = session.to_timeslot()
            if student.has_conflict(slot, self.session_lookup):
                continue
            candidates.append(session)
        return candidates

    def assign(self) -> List[Tuple[str, int]]:
        # 返回 (student_id, session_id)
        assignments: List[Tuple[str, int]] = []
        # 先按班级/专业分组，组内顺序随机打散，提升 B8
        class_groups: Dict[str, List[str]] = defaultdict(list)
        for sid, stu in self.students.items():
            key = stu.clazz or stu.major or "_misc"
            class_groups[key].append(sid)
        ordered_students: List[str] = []
        for _, sids in sorted(class_groups.items(), key=lambda item: -len(item[1])):
            random.shuffle(sids)
            ordered_students.extend(sids)

        for sid in ordered_students:
            student = self.students[sid]
            while self._student_hours(student) < self._target_hours(student):
                candidates = self._candidate_sessions(student)
                if not candidates:
                    break
                candidates.sort(key=lambda s: self._score(student, s))
                chosen = candidates[0]
                chosen.assigned_students.append(student.student_id)
                student.assigned.append(chosen.session_id)
                student.taken_projects.add(chosen.project_name)
                assignments.append((student.student_id, chosen.session_id))
                # 若刚好满足或超出要求则停止
                if self._student_hours(student) >= self._target_hours(student):
                    break
        if self.swap_iterations > 0:
            self._local_optimize()
        return assignments

    def _has_project(self, student: Student, project_name: str, exclude_session_id: Optional[int] = None) -> bool:
        for sid in student.assigned:
            if exclude_session_id is not None and sid == exclude_session_id:
                continue
            if self.session_lookup[sid].project_name == project_name:
                return True
        return False

    def _conflicts_with_other_assignments(
        self,
        student: Student,
        target_session: LabSession,
        exclude_session_id: Optional[int] = None,
    ) -> bool:
        slot = target_session.to_timeslot()
        for sid in student.assigned:
            if exclude_session_id is not None and sid == exclude_session_id:
                continue
            if self.session_lookup[sid].to_timeslot().conflicts_with(slot):
                return True
        for busy in student.busy_slots:
            if busy.conflicts_with(slot):
                return True
        return False

    def _session_diversity(
        self,
        session: LabSession,
        swap_out: Optional[Student] = None,
        swap_in: Optional[Student] = None,
    ) -> float:
        classes = set()
        majors = set()
        for sid in session.assigned_students:
            if swap_out and sid == swap_out.student_id:
                continue
            peer = self.students.get(sid)
            if not peer:
                continue
            if peer.clazz:
                classes.add(peer.clazz)
            if peer.major:
                majors.add(peer.major)
        if swap_in:
            if swap_in.clazz:
                classes.add(swap_in.clazz)
            if swap_in.major:
                majors.add(swap_in.major)
        size = len(session.assigned_students)
        if swap_out and swap_out.student_id in session.assigned_students:
            size -= 1
        if swap_in:
            size += 1
        if size <= 0:
            return 0.0
        distinct = max(len(classes), len(majors))
        return distinct / size

    def _can_swap(
        self,
        student_a: Student,
        session_a: LabSession,
        student_b: Student,
        session_b: LabSession,
    ) -> bool:
        if session_a.session_id == session_b.session_id:
            return False
        # 项目唯一性
        if self._has_project(student_a, session_b.project_name, exclude_session_id=session_a.session_id):
            return False
        if self._has_project(student_b, session_a.project_name, exclude_session_id=session_b.session_id):
            return False
        # 时间冲突
        if self._conflicts_with_other_assignments(student_a, session_b, exclude_session_id=session_a.session_id):
            return False
        if self._conflicts_with_other_assignments(student_b, session_a, exclude_session_id=session_b.session_id):
            return False
        # 学时不降档
        new_hours_a = self._student_hours(student_a) - session_a.hours + session_b.hours
        new_hours_b = self._student_hours(student_b) - session_b.hours + session_a.hours
        if new_hours_a < self._target_hours(student_a):
            return False
        if new_hours_b < self._target_hours(student_b):
            return False
        return True

    def _drop_project_if_unused(self, student: Student, project_name: str, removed_session_id: int) -> None:
        for sid in student.assigned:
            if sid == removed_session_id:
                continue
            if self.session_lookup[sid].project_name == project_name:
                return
        student.taken_projects.discard(project_name)

    def _perform_swap(
        self,
        student_a: Student,
        session_a: LabSession,
        student_b: Student,
        session_b: LabSession,
    ) -> None:
        # 更新 session 成员
        if student_a.student_id in session_a.assigned_students:
            session_a.assigned_students.remove(student_a.student_id)
        if student_b.student_id in session_b.assigned_students:
            session_b.assigned_students.remove(student_b.student_id)
        session_a.assigned_students.append(student_b.student_id)
        session_b.assigned_students.append(student_a.student_id)

        # 更新学生的 session 列表
        if session_a.session_id in student_a.assigned:
            student_a.assigned.remove(session_a.session_id)
        student_a.assigned.append(session_b.session_id)

        if session_b.session_id in student_b.assigned:
            student_b.assigned.remove(session_b.session_id)
        student_b.assigned.append(session_a.session_id)

        # 更新项目集合
        self._drop_project_if_unused(student_a, session_a.project_name, removed_session_id=session_a.session_id)
        self._drop_project_if_unused(student_b, session_b.project_name, removed_session_id=session_b.session_id)
        student_a.taken_projects.add(session_b.project_name)
        student_b.taken_projects.add(session_a.project_name)

    def _local_optimize(self) -> None:
        # 简单的局部交换，降低组内班级/专业异质度
        student_ids = [sid for sid, stu in self.students.items() if stu.assigned]
        if len(student_ids) < 2:
            return
        for _ in range(self.swap_iterations):
            sid_a, sid_b = random.sample(student_ids, 2)
            student_a = self.students[sid_a]
            student_b = self.students[sid_b]
            if not student_a.assigned or not student_b.assigned:
                continue
            session_a_id = random.choice(student_a.assigned)
            session_b_id = random.choice(student_b.assigned)
            if session_a_id == session_b_id:
                continue
            session_a = self.session_lookup[session_a_id]
            session_b = self.session_lookup[session_b_id]
            if not self._can_swap(student_a, session_a, student_b, session_b):
                continue
            before_div = self._session_diversity(session_a) + self._session_diversity(session_b)
            after_div = self._session_diversity(session_a, swap_out=student_a, swap_in=student_b)
            after_div += self._session_diversity(session_b, swap_out=student_b, swap_in=student_a)
            if after_div < before_div:
                self._perform_swap(student_a, session_a, student_b, session_b)

    def build_output(self) -> pd.DataFrame:
        rows = []
        # 预先计算每个实验组的最终人数
        group_size = {s.session_id: len(s.assigned_students) for s in self.sessions}
        seq = 1
        for session in self.sessions:
            for sid in session.assigned_students:
                student = self.students[sid]
                weekday_label = WEEKDAY_LABEL.get(session.weekday, str(session.weekday))
                rows.append(
                    {
                        "序号": seq,
                        "院系名称": student.dept,
                        "专业名称": student.major,
                        "班级名称": student.clazz,
                        "学号": student.student_id,
                        "姓名（可能有重名）": student.name,
                        "实验项目名称": session.project_name,
                        "上课周次": "，".join(sorted(str(w) + "周" for w in sorted(session.weeks))),
                        "上课星期": weekday_label,
                        "开始节次": session.start_period,
                        "结束节次": session.end_period,
                        "上课教师": session.teacher,
                        "实验人数": group_size[session.session_id],
                        "课时": session.hours,
                    }
                )
                seq += 1
        df = pd.DataFrame(rows, columns=[
            "序号",
            "院系名称",
            "专业名称",
            "班级名称",
            "学号",
            "姓名（可能有重名）",
            "实验项目名称",
            "上课周次",
            "上课星期",
            "开始节次",
            "结束节次",
            "上课教师",
            "实验人数",
            "课时",
        ])
        return df

    def report_unfilled(self) -> List[str]:
        msgs = []
        for sid, stu in self.students.items():
            need = self.required_hours - self._student_hours(stu)
            if need > 0:
                msgs.append(f"学生 {sid} 还缺少 {need} 学时，可考虑手动调整或增加实验场次")
        return msgs
