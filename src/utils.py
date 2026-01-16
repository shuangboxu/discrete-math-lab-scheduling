from __future__ import annotations

import math
import re
from typing import Iterable, Optional, Set, Tuple

from .models import TimeSlot

WEEKDAY_MAP = {
    "星期一": 1,
    "周一": 1,
    "星期二": 2,
    "周二": 2,
    "星期三": 3,
    "周三": 3,
    "星期四": 4,
    "周四": 4,
    "星期五": 5,
    "周五": 5,
    "星期六": 6,
    "周六": 6,
    "星期日": 7,
    "星期天": 7,
    "周日": 7,
    "周天": 7,
}


def parse_weeks(raw: Optional[str]) -> Set[int]:
    """解析诸如“1-6周,8周”格式为周次集合。"""
    if raw is None:
        return set()
    text = str(raw).strip().replace("周", "")
    if not text:
        return set()
    parts = re.split(r"[,，]", text)
    weeks: Set[int] = set()
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                start_i, end_i = int(start), int(end)
                if start_i > end_i:
                    start_i, end_i = end_i, start_i
                weeks.update(range(start_i, end_i + 1))
            except ValueError:
                continue
        else:
            try:
                weeks.add(int(part))
            except ValueError:
                continue
    return weeks


def parse_weekday(raw: Optional[str]) -> Optional[int]:
    if raw is None:
        return None
    text = str(raw).strip()
    if text.isdigit():
        try:
            num = int(text)
            if 1 <= num <= 7:
                return num
        except Exception:
            return None
    return WEEKDAY_MAP.get(text)


def parse_period_range(raw: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """解析节次字段，支持“第3节”“3-5节”“3-5”"""
    if raw is None:
        return None, None
    text = str(raw).strip()
    nums = re.findall(r"\d+", text)
    if not nums:
        return None, None
    if len(nums) == 1:
        num = int(nums[0])
        return num, num
    start, end = int(nums[0]), int(nums[-1])
    if start > end:
        start, end = end, start
    return start, end


def make_timeslot(weeks: Iterable[int], weekday: int, start: int, end: int) -> Optional[TimeSlot]:
    # 任何字段为空都无法形成有效时间片
    if weekday is None or start is None or end is None:
        return None
    week_set = set(weeks)
    if not week_set:
        return None
    return TimeSlot(week_set, weekday, start, end)


def period_overlap(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    return not (a[1] < b[0] or b[1] < a[0])
