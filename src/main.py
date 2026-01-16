from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .data_loader import load_lab_sessions, load_students
from .scheduler import Scheduler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="物理实验排课脚本")
    parser.add_argument("--required-hours", type=int, default=30, help="每个学生需要的总学时，默认30")
    parser.add_argument("--lab-file", type=str, default="raw/lab_schedule.xlsx", help="实验排课表路径")
    parser.add_argument(
        "--student-lecture-file",
        type=str,
        default="raw/student_current_lecture_schedule.xlsx",
        help="学生已有理论课表",
    )
    parser.add_argument("--output", type=str, default="output/schedule.csv", help="输出csv路径")
    parser.add_argument("--seed", type=int, default=42, help="随机种子，保证可复现")
    parser.add_argument("--w-occupancy", type=float, default=1.0, help="容量均衡权重")
    parser.add_argument("--w-class", type=float, default=1.0, help="同班/同专业聚合权重")
    parser.add_argument("--w-hetero", type=float, default=0.5, help="组内异质度惩罚权重")
    parser.add_argument("--w-spread", type=float, default=0.2, help="周次分散权重")
    parser.add_argument("--w-slot", type=float, default=0.1, help="同一时段偏好权重")
    parser.add_argument("--swap-iterations", type=int, default=200, help="局部交换次数，用于提升同班聚合")
    return parser.parse_args()


def ensure_output_path(path: Path) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()
    lab_sessions = load_lab_sessions(args.lab_file)
    students = load_students(args.required_hours, args.student_lecture_file)

    supply_hours = sum(s.capacity * s.hours for s in lab_sessions)
    demand_hours = len(students) * args.required_hours
    print(f"学生人数: {len(students)}，需求学时: {demand_hours}，实验供给学时: {supply_hours}")
    if supply_hours < demand_hours:
        gap = demand_hours - supply_hours
        print(f"提示：实验总容量比需求少 {gap} 学时，部分同学可能无法满足要求，需要增开实验或调整学时标准。")

    scheduler = Scheduler(
        students,
        lab_sessions,
        required_hours=args.required_hours,
        seed=args.seed,
        w_occupancy=args.w_occupancy,
        w_class=args.w_class,
        w_hetero=args.w_hetero,
        w_spread=args.w_spread,
        w_slot=args.w_slot,
        swap_iterations=args.swap_iterations,
    )
    scheduler.assign()

    df = scheduler.build_output()
    output_path = Path(args.output)
    ensure_output_path(output_path)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"已生成排课结果: {output_path}")
    warnings = scheduler.report_unfilled()
    if warnings:
        print(f"共有 {len(warnings)} 位学生未满足学时，需人工关注或增补实验场次。展示前20条：")
        for msg in warnings[:20]:
            print(" - " + msg)
    else:
        print("所有学生均已满足所需学时。")


if __name__ == "__main__":
    main()
