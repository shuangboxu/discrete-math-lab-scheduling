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
