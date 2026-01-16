from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

from .utils import parse_period_range, parse_weekday, parse_weeks

WEEKDAY_MAP = {
    "星期一": 1,
    "星期二": 2,
    "星期三": 3,
    "星期四": 4,
    "星期五": 5,
    "星期六": 6,
    "星期日": 7,
    "星期天": 7,
    "周一": 1,
    "周二": 2,
    "周三": 3,
    "周四": 4,
    "周五": 5,
    "周六": 6,
    "周日": 7,
    "周天": 7,
}
NUM_TO_WEEKDAY = {1: "星期一", 2: "星期二", 3: "星期三", 4: "星期四", 5: "星期五", 6: "星期六", 7: "星期日"}
TIME_LABEL = {3: "上午", 8: "下午", 11: "晚上"}
COLOR_MAP = {"lab": "linear-gradient(135deg, #60a5fa, #2563eb)", "lecture": "linear-gradient(135deg, #fb923c, #f97316)"}


def _to_int(value, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _time_of_day(start_period: int) -> str:
    return TIME_LABEL.get(start_period, "其他")


def load_schedule(path: str) -> pd.DataFrame:
    ext = Path(path).suffix.lower()
    if ext in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def load_lecture_schedule(path: str) -> pd.DataFrame:
    ext = Path(path).suffix.lower()
    if ext in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def build_data(df: pd.DataFrame, lecture_df: pd.DataFrame | None = None) -> Dict[str, List[dict]]:
    entries: List[dict] = []
    session_map: Dict[str, dict] = {}
    for _, row in df.iterrows():
        weeks = sorted(parse_weeks(row.get("上课周次")))
        weeks_label = "，".join(f"{w}周" for w in weeks)
        weekday_raw = str(row.get("上课星期", "")).strip()
        weekday_num = WEEKDAY_MAP.get(weekday_raw, 0)
        weekday_label = weekday_raw or NUM_TO_WEEKDAY.get(weekday_num, "")
        start_period = _to_int(row.get("开始节次"))
        end_period = _to_int(row.get("结束节次"))
        time_of_day = _time_of_day(start_period)
        project = str(row.get("实验项目名称", "")).strip()
        teacher = str(row.get("上课教师", "")).strip()
        group_key = f"{project}|{teacher}|{weekday_num}|{start_period}|{end_period}|{weeks_label}"

        entry = {
            "studentId": str(row.get("学号", "")).strip(),
            "name": str(row.get("姓名（可能有重名）", "")).strip(),
            "dept": str(row.get("院系名称", "")).strip(),
            "major": str(row.get("专业名称", "")).strip(),
            "clazz": str(row.get("班级名称", "")).strip(),
            "project": project,
            "kind": "lab",
            "color": COLOR_MAP["lab"],
            "weeks": weeks,
            "weeksLabel": weeks_label,
            "weekday": weekday_num,
            "weekdayLabel": weekday_label,
            "timeOfDay": time_of_day,
            "startPeriod": start_period,
            "endPeriod": end_period,
            "teacher": teacher,
            "groupKey": group_key,
        }
        entries.append(entry)

        if group_key not in session_map:
            session_map[group_key] = {
                "groupKey": group_key,
                "project": project,
                "teacher": teacher,
                "weeks": weeks,
                "weeksLabel": weeks_label,
                "weekday": weekday_num,
                "weekdayLabel": weekday_label,
                "timeOfDay": time_of_day,
                "startPeriod": start_period,
                "endPeriod": end_period,
                "students": [],
            }
        session_map[group_key]["students"].append(
            {
                "studentId": entry["studentId"],
                "name": entry["name"],
                "dept": entry["dept"],
                "major": entry["major"],
                "clazz": entry["clazz"],
            }
        )

    session_list = sorted(
        session_map.values(),
        key=lambda x: (min(x["weeks"] or [99]), x["weekday"], x["startPeriod"], x["project"]),
    )

    if lecture_df is not None:
        for _, row in lecture_df.iterrows():
            weeks = sorted(parse_weeks(row.get("周次")))
            weeks_label = "，".join(f"{w}周" for w in weeks)
            raw_weekday = str(row.get("上课星期", "")).strip()
            weekday_num = parse_weekday(raw_weekday) or 0
            if weekday_num == 0:
                try:
                    weekday_num = int(raw_weekday)
                except Exception:
                    weekday_num = 0
            weekday_label = NUM_TO_WEEKDAY.get(weekday_num, raw_weekday)
            start_p, end_p = parse_period_range(row.get("上课节次"))
            start_p = start_p or 0
            end_p = end_p or 0
            time_of_day = _time_of_day(start_p)
            project = str(row.get("课程名", "理论课"))
            entry = {
                "studentId": str(row.get("学号", "")).strip(),
                "name": str(row.get("姓名（可能有重名）", "")).strip(),
                "dept": str(row.get("院系名称", "")).strip(),
                "major": str(row.get("专业名称", "")).strip(),
                "clazz": str(row.get("班级名称", "")).strip(),
                "project": project,
                "kind": "lecture",
                "color": COLOR_MAP["lecture"],
                "weeks": weeks,
                "weeksLabel": weeks_label,
                "weekday": weekday_num,
                "weekdayLabel": weekday_label,
                "timeOfDay": time_of_day,
                "startPeriod": start_p,
                "endPeriod": end_p,
                "teacher": str(row.get("课程号", "理论课")),
                "groupKey": f"lecture|{project}|{weekday_num}|{start_p}|{end_p}|{weeks_label}",
            }
            entries.append(entry)

    return {"entries": entries, "sessions": session_list}


def render_html(output: Path, data_url: str) -> None:
    template = """<!DOCTYPE html>
<html lang=\"zh\">
<head>
<meta charset=\"utf-8\" />
<title>物理实验排课可视化</title>
<style>
body { font-family: \"Segoe UI\", \"Helvetica Neue\", sans-serif; margin: 0; padding: 0; background: #f5f7fb; color: #1f2937; }
header { padding: 16px 24px; background: linear-gradient(135deg, #0f8ec7, #1b58b8); color: #fff; }
section { padding: 16px 24px; }
.card { background: #fff; border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.06); padding: 16px; margin-bottom: 16px; }
.label { font-weight: 600; color: #0f8ec7; margin-right: 8px; }
input, select { padding: 8px 10px; border-radius: 6px; border: 1px solid #d1d5db; min-width: 200px; }
button { padding: 8px 14px; border: none; border-radius: 6px; background: #0f8ec7; color: #fff; cursor: pointer; margin-left: 8px; }
button:hover { background: #0c78a8; }
#calendar-grid { display: grid; grid-template-columns: 80px repeat(16, minmax(80px, 1fr)); gap: 6px; align-items: stretch; }
.grid-header { font-weight: 700; text-align: center; padding: 6px; color: #4b5563; }
.grid-cell { background: #fff; border: 1px dashed #e5e7eb; border-radius: 8px; min-height: 90px; padding: 6px; overflow: hidden; position: relative; }
.slot-label { font-size: 13px; font-weight: 700; color: #374151; text-align: center; padding-top: 10px; }
.pill { display: block; background: linear-gradient(135deg, #60a5fa, #2563eb); color: #fff; border-radius: 8px; padding: 6px 8px; margin-bottom: 6px; font-size: 13px; box-shadow: 0 4px 12px rgba(37,99,235,0.25); }
.pill small { display: block; opacity: 0.85; }
.table { width: 100%; border-collapse: collapse; margin-top: 10px; }
.table th, .table td { border: 1px solid #e5e7eb; padding: 8px; text-align: left; }
.table th { background: #f3f4f6; }
.chip { display: inline-block; background: #e0f2fe; color: #0369a1; padding: 4px 8px; border-radius: 12px; margin: 2px; font-size: 12px; }
.stats { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.week-grid { display: grid; grid-template-columns: 80px repeat(7, minmax(140px, 1fr)); gap: 8px; align-items: start; }
.period-column { background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 10px; padding: 8px; min-height: 140px; box-shadow: 0 6px 18px rgba(0,0,0,0.04); }
.period-header { font-weight: 700; color: #6b7280; margin-bottom: 8px; text-align: center; }
.period-cell { color: #9ca3af; text-align: center; padding: 6px 0; border-bottom: 1px dashed #e5e7eb; font-size: 12px; }
.period-cell:last-child { border-bottom: none; }
.day-column { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 8px; min-height: 140px; box-shadow: 0 6px 18px rgba(0,0,0,0.04); display: grid; grid-template-rows: auto 1fr; gap: 6px; }
.day-header { font-weight: 700; color: #0f8ec7; text-align: center; }
.day-body { display: grid; grid-template-rows: repeat(13, 1fr); gap: 4px; }
.empty-slot { color: #9ca3af; text-align: center; padding: 12px 0; grid-row: 1 / 14; }
</style>
</head>
<body>
<header>
  <h2>物理实验排课可视化</h2>
  <div>支持学生课表查询与课次学生分布查看（周次 1-16，上午/下午/晚上）</div>
</header>
<section class=\"card\">
  <div><span class=\"label\">学生查询</span>输入学号或姓名，查看个人课表</div>
  <div style=\"margin-top:8px;\">
    <input id=\"student-input\" placeholder=\"学号或姓名\" />
    <button onclick=\"handleStudentSearch()\">搜索</button>
  </div>
</section>
<section class=\"card\">
  <div><span class=\"label\">课次查看</span>选择一个实验课次，查看学生名单及专业/班级分布</div>
  <div style=\"margin-top:8px;\">
    <select id=\"session-select\"></select>
    <button onclick=\"handleSessionView()\">查看</button>
  </div>
  <div id=\"session-summary\" style=\"margin-top:12px;\"></div>
  <div id=\"session-table\"></div>
</section>
<section class=\"card\">
  <div><span class=\"label\">日历视图</span>按周次 (1-16) x 上午/下午/晚上 展示排号的物理实验课</div>
  <div id=\"calendar-container\" style=\"margin-top:12px; overflow-x:auto;\"></div>
</section>
<section class=\"card\">
  <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
    <div><span class="label">周视图</span>每天按 1-13 节定位展示实验课与已有课程</div>
    <div style="color:#374151;">当前周次：<span id="week-indicator" style="font-weight:700;">1</span></div>
    <div>
      <button onclick="prevWeek()">上一周</button>
      <button onclick="nextWeek()" style="margin-left:6px;">下一周</button>
    </div>
  </div>
  <div id=\"week-container\" style=\"margin-top:12px; overflow-x:auto;\"></div>
</section>
<script>
let data = null;
const DATA_URL = '__DATA_URL__';
const times = [\"上午\", \"下午\", \"晚上\"];
const weekdayLabels = [\"星期一\", \"星期二\", \"星期三\", \"星期四\", \"星期五\", \"星期六\", \"星期日\"];
const periods = Array.from({ length: 13 }, (_, i) => i + 1);
let currentEntries = [];
let currentWeek = 1;

function initSessions() {
  const sel = document.getElementById('session-select');
  sel.innerHTML = '';
  data.sessions.forEach((s, idx) => {
    const opt = document.createElement('option');
    opt.value = s.groupKey;
    const weeks = s.weeks.length ? s.weeks.join('、') + '周' : '周次未填';
    opt.text = `${idx+1}. ${s.project} | ${s.weekdayLabel || '星期'+s.weekday} | ${s.timeOfDay} | 周次:${weeks} | 教师:${s.teacher}`;
    sel.appendChild(opt);
  });
}

function handleStudentSearch() {
  const kw = document.getElementById('student-input').value.trim();
  if (!kw) {
    currentEntries = [];
    currentWeek = 1;
    renderLabCalendar();
    renderWeekView();
    return;
  }
  currentEntries = data.entries.filter(e => e.studentId.includes(kw) || e.name.includes(kw));
  currentWeek = 1;
  renderLabCalendar();
  renderWeekView();
}

function renderLabCalendar() {
  const container = document.getElementById('calendar-container');
  const entries = currentEntries.filter(e => e.kind === 'lab');
  if (!entries.length) {
    container.innerHTML = '<div style="color:#6b7280;">输入学号或姓名后显示排号的物理实验课。</div>';
    return;
  }
  const grid = document.createElement('div');
  grid.id = 'calendar-grid';
  const headerBlank = document.createElement('div');
  headerBlank.className = 'grid-header';
  grid.appendChild(headerBlank);
  for (let w=1; w<=16; w++) {
    const h = document.createElement('div');
    h.className = 'grid-header';
    h.textContent = `第${w}周`;
    grid.appendChild(h);
  }
  times.forEach(t => {
    const rowLabel = document.createElement('div');
    rowLabel.className = 'slot-label';
    rowLabel.textContent = t;
    grid.appendChild(rowLabel);
    for (let w=1; w<=16; w++) {
      const cell = document.createElement('div');
      cell.className = 'grid-cell';
      const items = entries.filter(e => e.timeOfDay === t && e.weeks.includes(w));
      items.forEach(item => {
        const pill = document.createElement('div');
        pill.className = 'pill';
        pill.style.background = item.color || 'linear-gradient(135deg, #6b7280, #4b5563)';
        const teacherLabel = item.teacher ? ` · ${item.teacher}` : '';
        pill.innerHTML = `<strong>${item.project}</strong><small>实验课 · ${item.weekdayLabel || '星期'+item.weekday} · ${item.timeOfDay}${teacherLabel}</small>`;
        cell.appendChild(pill);
      });
      grid.appendChild(cell);
    }
  });
  container.innerHTML = '';
  container.appendChild(grid);
}

function renderWeekView() {
  const container = document.getElementById('week-container');
  document.getElementById('week-indicator').textContent = currentWeek;
  if (!currentEntries.length) {
    container.innerHTML = '<div style="color:#6b7280;">输入学号或姓名后显示按日课表。</div>';
    return;
  }
  const grid = document.createElement('div');
  grid.className = 'week-grid';

  const periodCol = document.createElement('div');
  periodCol.className = 'period-column';
  const pHead = document.createElement('div');
  pHead.className = 'period-header';
  pHead.textContent = '节次';
  periodCol.appendChild(pHead);
  periods.forEach(p => {
    const pc = document.createElement('div');
    pc.className = 'period-cell';
    pc.textContent = `第${p}节`;
    periodCol.appendChild(pc);
  });
  grid.appendChild(periodCol);

  weekdayLabels.forEach((label, idx) => {
    const dayCol = document.createElement('div');
    dayCol.className = 'day-column';
    const head = document.createElement('div');
    head.className = 'day-header';
    head.textContent = label;
    dayCol.appendChild(head);

    const body = document.createElement('div');
    body.className = 'day-body';

    const dayEntries = currentEntries
      .filter(e => e.weeks.includes(currentWeek) && e.weekday === idx + 1)
      .sort((a, b) => (a.startPeriod || 0) - (b.startPeriod || 0));

    if (!dayEntries.length) {
      const empty = document.createElement('div');
      empty.className = 'empty-slot';
      empty.textContent = '无课程';
      body.appendChild(empty);
    } else {
      dayEntries.forEach(item => {
        if (!item.startPeriod || item.startPeriod < 1 || item.startPeriod > 13) return;
        const span = Math.max(1, (item.endPeriod || item.startPeriod) - item.startPeriod + 1);
        const pill = document.createElement('div');
        pill.className = 'pill';
        pill.style.background = item.color || 'linear-gradient(135deg, #6b7280, #4b5563)';
        pill.style.gridRow = `${item.startPeriod} / ${item.startPeriod + span}`;
        const teacherLabel = item.teacher ? ` · ${item.teacher}` : '';
        const kindLabel = item.kind === 'lecture' ? '理论课' : '实验课';
        const periodLabel = `${item.startPeriod}-${item.endPeriod || item.startPeriod}节`;
        pill.innerHTML = `<strong>${item.project}</strong><small>${kindLabel} · ${periodLabel}${teacherLabel}</small>`;
        body.appendChild(pill);
      });
    }

    dayCol.appendChild(body);
    grid.appendChild(dayCol);
  });

  container.innerHTML = '';
  container.appendChild(grid);
}

function prevWeek() {
  currentWeek = currentWeek <= 1 ? 16 : currentWeek - 1;
  renderWeekView();
}

function nextWeek() {
  currentWeek = currentWeek >= 16 ? 1 : currentWeek + 1;
  renderWeekView();
}

function handleSessionView() {
  const sel = document.getElementById('session-select');
  const key = sel.value;
  const session = data.sessions.find(s => s.groupKey === key);
  const summary = document.getElementById('session-summary');
  const tableWrap = document.getElementById('session-table');
  if (!session) {
    summary.innerHTML = '<span style="color:#ef4444;">未找到该课次。</span>';
    tableWrap.innerHTML = '';
    return;
  }
  const students = session.students;
  const total = students.length;
  const majorCount = {};
  const classCount = {};
  students.forEach(s => {
    if (s.major) majorCount[s.major] = (majorCount[s.major]||0)+1;
    if (s.clazz) classCount[s.clazz] = (classCount[s.clazz]||0)+1;
  });
  const majorChips = Object.entries(majorCount).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`<span class=\"chip\">${k||'未填'} · ${v}</span>`).join('');
  const classChips = Object.entries(classCount).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`<span class=\"chip\">${k||'未填'} · ${v}</span>`).join('');
  summary.innerHTML = `
    <div><strong>${session.project}</strong> | ${session.weekdayLabel || '星期'+session.weekday} | ${session.timeOfDay} | 周次: ${session.weeksLabel || session.weeks.join('、')+'周'} | 教师: ${session.teacher}</div>
    <div class=\"stats\"><span class=\"chip\">人数 · ${total}</span>${majorChips}</div>
    <div class=\"stats\">班级分布：${classChips || '无班级数据'}</div>
  `;
  const rows = students.map(s => `<tr><td>${s.studentId}</td><td>${s.name}</td><td>${s.dept}</td><td>${s.major}</td><td>${s.clazz}</td></tr>`).join('');
  tableWrap.innerHTML = `<table class=\"table\"><thead><tr><th>学号</th><th>姓名</th><th>院系</th><th>专业</th><th>班级</th></tr></thead><tbody>${rows}</tbody></table>`;
}

fetch(DATA_URL)
  .then(resp => resp.json())
  .then(d => { data = d; initSessions(); renderLabCalendar(); renderWeekView(); })
  .catch(err => { console.error(err); document.body.innerHTML = '<div style="padding:16px;color:#ef4444;">数据加载失败</div>'; });
</script>
</body>
</html>"""
    html = template.replace("__DATA_URL__", data_url)
    output.write_text(html, encoding="utf-8")


def write_data_file(data: Dict[str, List[dict]], path: Path) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="排课结果可视化，生成可搜索的 HTML")
    parser.add_argument("--input", type=str, default="output/schedule.csv", help="排课结果文件，支持 csv/xlsx")
    parser.add_argument(
        "--lecture-file",
        type=str,
        default="raw/student_current_lecture_schedule.xlsx",
        help="学生已有理论课表，用于重叠显示避免冲突",
    )
    parser.add_argument("--output", type=str, default="output/schedule.html", help="输出 HTML 路径")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = load_schedule(args.input)
    lecture_df = load_lecture_schedule(args.lecture_file) if args.lecture_file else None
    data = build_data(df, lecture_df)
    output_path = Path(args.output)
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    data_path = output_path.with_suffix(".data.json")
    write_data_file(data, data_path)
    render_html(output_path, data_path.name)

    print(f"已生成可视化 HTML: {output_path}")
    print(f"数据文件: {data_path}")


if __name__ == "__main__":
    main()
