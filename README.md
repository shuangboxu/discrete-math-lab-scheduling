# Physics Laboratory Course Scheduling Script

This project provides a Python-based tool for scheduling university physics laboratory courses.  
The scheduler strictly satisfies all **Category A hard constraints** and attempts to optimize **Category B objectives** where possible.  
All input data are read from Excel files in the `raw/` directory, and the output is generated as a CSV file that conforms to the required template format.

---

## Environment and Dependencies

- Python 3.13 (local testing environment)
- Dependency: `pandas` (the only non-standard library required)

If the dependency is not installed, run:
```bash
pip install pandas
```

---

## Directory Structure

- `raw/`  
  Input Excel files (laboratory schedule, student lecture timetable, export template)

- `src/`  
  Core source code  
  - `data_loader.py` – Load and clean Excel data  
  - `models.py` – Data structures for time slots, students, and laboratory groups  
  - `scheduler.py` – Scheduling algorithm and result assembly  
  - `main.py` – Command-line entry point  

- `output/`  
  Default output directory; `schedule.csv` will be generated after execution

- `report.md`  
  Explanation of the discrete mathematics methods

- `TASK.txt`  
  Requirement specification

---

## Usage

Run the following command in the project root directory  
(default requirement: **30 credit hours per student**):

```bash
python -m src.main
```

### Common Arguments

- `--required-hours`  
  Required laboratory credit hours per student (default: `30`)

- `--lab-file`  
  Path to the laboratory schedule file  
  (default: `raw/lab_schedule.xlsx`)

- `--student-lecture-file`  
  Path to the existing lecture timetable  
  (default: `raw/student_current_lecture_schedule.xlsx`)  
  > Only lecture conflicts are checked; existing laboratory schedules are ignored.

- `--output`  
  Output CSV path (default: `output/schedule.csv`)

- `--seed`  
  Random seed for reproducible assignment order (default: `42`)

### Example

```bash
python -m src.main --required-hours 21 --output output/schedule_21h.csv
```

---

## Visualization (HTML)

An interactive, searchable, calendar-style HTML visualization can be generated from the scheduling results.  
Existing lecture timetables can be overlaid for comparison.

```bash
python -m src.visualize \
  --input output/schedule.csv \
  --lecture-file raw/student_current_lecture_schedule.xlsx \
  --output output/schedule.html
```

### Features

- **Student Query**  
  Filter by student ID or name; display a grid view of  
  *Weeks 1–16 × Morning / Afternoon / Evening*

- **Session View**  
  Select a laboratory session to view the student list and statistics by major and class

- **Calendar View**  
  1. Weeks 1–16 × Morning / Afternoon / Evening (laboratory sessions only)  
  2. Weekly day-by-day view showing both laboratory and lecture courses, with one-click week switching

- **Course Overlay**  
  - Laboratory courses: blue gradient  
  - Lecture courses: orange gradient  
  This makes conflicts and free time easy to identify.

---

## Core Workflow

1. **Excel Parsing**  
   Standardize week ranges, weekdays, and class periods, and convert them into comparable time-slot objects.

2. **Student and Timetable Assembly**  
   Merge only lecture-course busy time to construct the conflict table  
   (existing laboratory schedules are ignored).

3. **Laboratory Group Construction**  
   Build laboratory group information, including capacity, credit hours, and time slots.

4. **Greedy Assignment**  
   Group students by class/major and iteratively assign them to laboratory groups that are conflict-free and not full.  
   The scoring function considers:
   - Capacity balance  
   - Class/major aggregation  
   - Distribution across weeks  
   - Time-slot consistency

5. **Output Generation**  
   Generate `schedule.csv` according to the export template.  
   The “laboratory capacity” column records the **actual assigned number of students**.

6. **Reporting**  
   If any students fail to meet the required credit hours, the terminal displays the total count and the first 20 cases.

---

## Output Format

The column order of `schedule.csv` strictly follows the template:

```
Index,
Faculty,
Major,
Class,
Student ID,
Student Name (may be duplicated),
Experiment Name,
Weeks,
Weekday,
Start Period,
End Period,
Instructor,
Assigned Student Count,
Credit Hours
```

---

## Local Testing Status

- Command executed:  
  `python -m src.main`

- Test data:  
  Two Excel files under `raw/`  
  (laboratory schedule and student lecture timetable)

- Result:  
  `output/schedule.csv` generated successfully

- Summary:  
  - Students: 2888  
  - Required credit hours: 86,640  
  - Available laboratory credit hours: 91,152  
  - All students satisfied the credit-hour requirement

- Visualization:  
  ```bash
  python -m src.visualize --input output/schedule.csv --output output/schedule.html
  ```
  HTML file generated successfully.

---

## Possible Manual Adjustments

If it is necessary to ensure that **all students meet the required credit hours**, consider:

1. Increasing the number of sessions or capacities in `lab_schedule.xlsx`
2. Reducing the value of `--required-hours`
3. Manually adjusting assignments for students with insufficient credit hours  
   (the first 20 cases are listed in the terminal; others can be identified via logs or filtering)

---

## Notes and FAQs

- The “assigned student count” column reflects the **actual number of assigned students**, which may differ from the original capacity.
- Rows with unparseable date or period formats in Excel files are skipped.
- Re-running the script will overwrite `output/schedule.csv` by default.

# 物理实验排课脚本

本项目提供基于 Python 的物理实验排课工具，满足 A 类硬约束，并尽量兼顾 B 类优化目标。源数据均来自 `raw/` 目录的 Excel 文件，输出为模板格式的 CSV。

## 环境与依赖
- Python 3.13（本地测试环境）
- 依赖：pandas（标准库以外仅此一项）

若未安装依赖，可执行：
```
pip install pandas
```

## 目录结构
- `raw/`：输入 Excel（排课表、学生理论课表、导出模板）
- `src/`：核心代码
  - `data_loader.py`：读取并清洗 Excel 数据
  - `models.py`：时间片、学生、实验组数据结构
  - `scheduler.py`：排课算法与结果组装
  - `main.py`：命令行入口
- `output/`：默认导出目录，运行后生成 `schedule.csv`
- `report.md`：离散数学方法说明
- `TASK.txt`：需求描述

## 运行方式
在项目根目录执行（默认每人 30 学时）：
```
python -m src.main
```
常用参数：
- `--required-hours`：每位学生需修学时，默认 30。
- `--lab-file`：实验排课表路径，默认 `raw/lab_schedule.xlsx`。
- `--student-lecture-file`：学生已有理论课表，默认 `raw/student_current_lecture_schedule.xlsx`（仅检查与理论课冲突，不再使用学生实验课表）。
- `--output`：输出 CSV 路径，默认 `output/schedule.csv`。
- `--seed`：随机种子，保证可复现的分配顺序，默认 42。

示例：
```
python -m src.main --required-hours 21 --output output/schedule_21h.csv
```

### 可视化（HTML）
根据排课结果生成可搜索、日历风格的 HTML，可叠加现有理论课表：
```
python -m src.visualize --input output/schedule.csv --lecture-file raw/student_current_lecture_schedule.xlsx --output output/schedule.html
```
功能：
- 学生查询：按学号/姓名过滤，显示 1-16 周 × 上午/下午/晚上 的网格视图。
- 课次查看：选择某个实验课次，查看学生名单，并统计专业/班级分布。
- 日历视图：① 1-16 周 × 上午/下午/晚上，仅显示排号的实验课；② 每周按天展示实验课与已有课程，一键循环周次。
- 课程叠加：实验课以蓝色渐变，理论课以橙色渐变叠加展示，便于快速识别冲突/空闲。

## 核心流程
1. 解析 Excel：标准化周次、星期、节次，并转为可比较的时间片。
2. 组装学生信息与现有课表：仅合并理论课忙碌时间，形成冲突表（忽略学生已有实验课表）。
3. 生成实验组信息：容量、课时、时段等。
4. 贪心分配：按班级/专业分组，迭代为每名学生寻找不冲突且未满员的实验组；评分函数考虑容量均衡、同班聚合、周次分散和时段一致性。
5. 输出：按照导出模板列生成 `schedule.csv`，实验人数列写入最终实际人数。
6. 报告：若存在学时不足学生，终端展示总数及前 20 条提示。

## 输出格式
`schedule.csv` 列顺序与模板一致：
`序号, 院系名称, 专业名称, 班级名称, 学号, 姓名（可能有重名）, 实验项目名称, 上课周次, 上课星期, 开始节次, 结束节次, 上课教师, 实验人数, 课时`

## 已完成本地测试
- 运行命令：`python -m src.main`
- 测试数据：`raw/` 下提供的两份课表（实验排课表、学生理论课表）。
- 结果：生成 [output/schedule.csv](output/schedule.csv)。
- 汇总：学生 2888 人，需求学时 86640，实验供给学时 91152，已全部满足学时要求。
- 可视化：`python -m src.visualize --input output/schedule.csv --output output/schedule.html` 成功生成 HTML。

## 可能的人工补充
- 如需满足所有人学时，可：
  1. 增加 `lab_schedule.xlsx` 中的场次或容量；
  2. 下调 `--required-hours`；
  3. 对未满足学时学生（终端列出前 20 条，其余可根据日志或手动过滤）进行人工调剂。

## 常见问题
- 输出人数列为“实际分配人数”，与原排课表容量可能不同。
- 如果 Excel 日期/节次格式异常，脚本会跳过无法解析的行。
- 若需重跑，直接再次执行命令会覆盖 `output/schedule.csv`。
