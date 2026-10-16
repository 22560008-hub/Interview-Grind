# Interview-Grind · 后端八股刷题助手

> 一个从零手写的计算机基础面试刷题与间隔复习 Web 应用，覆盖计算机网络、操作系统、MySQL、Redis 四大后端常考模块，内置 **224 道**原创八股题，帮助你在刷题中自动沉淀错题、追踪掌握度并安排复习。

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-框架-009688)
![Database](https://img.shields.io/badge/SQLite-3-003B57)
![Questions](https://img.shields.io/badge/题库-224%20道-orange)
![Tests](https://img.shields.io/badge/pytest-43%20用例-success)

前后端一体、开箱即用：后端基于 **FastAPI + SQLAlchemy + SQLite**，前端为零依赖的**原生 HTML/JavaScript 单页应用**，无需单独启动前端、无需 Docker、无需外部数据库。

---

## 目录

- [功能特性](#功能特性)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [使用说明](#使用说明)
- [API 接口](#api-接口)
- [核心机制](#核心机制)
- [数据模型](#数据模型)
- [测试](#测试)
- [题库说明](#题库说明)
- [开发路线图](#开发路线图)
- [致谢](#致谢)

---

## 功能特性

- **组卷刷题**：按模块、题型、题量随机抽题，支持选择题与简答题混合作答。
- **自动判分**：选择题精确匹配答案字母；简答题按顿号拆分关键词，全部关键词命中后判对，答完即出正确答案与解析。
- **错题本**：答错自动收录并累计错次，确认"已掌握"后可移出。
- **题目收藏**：一键收藏 / 取消收藏，随时回看重点题。
- **掌握度追踪**：每题维护学习档案，自动标注薄弱（红）/ 一般（橙）/ 熟练（绿）。
- **间隔复习**：参考间隔重复（Spaced Repetition）思想，答对推迟复习、答错立即再练。
- **每日一练**：按日期固定抽取 5 题，采用"复习题 + 薄弱题 + 新题"混合策略；逐题保存进度，刷新后可以继续，并支持追加题目。
- **练习历史**：按天查看已答数量、正确率、完成率与答题详情，并统计连续完成天数。
- **学习统计**：总正确率、各模块正确率、掌握度分布一目了然。
- **自动接口文档**：FastAPI 自动生成 Swagger UI，打开 `/docs` 即可在线调试。

---

## 技术栈

| 层 | 技术 |
| --- | --- |
| Web 框架 | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) |
| ORM | [SQLAlchemy](https://www.sqlalchemy.org/) |
| 数据库 | SQLite（单文件，零配置，可平滑迁移 PostgreSQL） |
| 配置管理 | pydantic-settings |
| 前端 | 原生 HTML / CSS / JavaScript（单页应用，无构建步骤） |
| 测试 | pytest + httpx（独立测试库） |

---

## 项目结构

```
interview-app/
├── README.md                     # 项目说明（本文件）
├── DEV_LOG.md                    # 开发日志：架构说明、踩坑记录、路线图
└── backend/
    ├── app/
    │   ├── main.py               # FastAPI 入口：建表、CORS、路由与静态文件挂载
    │   ├── core/                 # 基础设施
    │   │   ├── config.py         # 配置项（应用名、数据库地址）
    │   │   └── database.py       # 数据库连接 / 会话 / Base
    │   ├── models/               # ORM 数据模型（7 张表）
    │   ├── schemas/              # Pydantic 请求 / 响应模型
    │   ├── services/             # 业务逻辑层（抽题、判分、统计、复习……）
    │   └── api/                  # 路由层（题目、作答、错题、收藏、统计、每日一练、复习）
    ├── scripts/
    │   └── seed.py               # 题库种子数据（224 道，幂等写入）
    ├── static/
    │   └── index.html            # 前端单页应用
    ├── tests/                    # pytest 测试
    ├── .env.example              # 环境变量示例
    ├── requirements.txt          # 运行依赖
    └── requirements-dev.txt      # 开发 / 测试依赖
```

分层调用链：

```
前端请求 → api 路由层 → services 业务层 → models ORM → SQLite
```

> `venv/`（虚拟环境）、`interview.db`（数据库）、`.env`（密钥）与缓存文件均已通过 `.gitignore` 排除，不会进入版本库。

---

## 快速开始

### 环境要求

- **Python 3.10 或更高版本**（代码使用了 `X | None` 类型语法）

### 1. 获取代码

```bash
git clone https://github.com/22560008-hub/Interview-Grind.git
cd Interview-Grind/backend
```

### 2. 创建并激活虚拟环境

Windows（PowerShell / CMD）：

```bash
python -m venv venv
venv\Scripts\activate
```

macOS / Linux：

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 初始化题库（首次运行必做）

```bash
python -m scripts.seed
```

该脚本会自动建表并写入 224 道题；**幂等**设计，重复运行不会产生重复题目。

### 5. 启动服务

```bash
uvicorn app.main:app --reload
```

启动后访问：

- 前端页面：<http://127.0.0.1:8000/>
- 接口文档（Swagger UI）：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/health>

> 数据库文件 `interview.db` 在首次启动时自动创建于 `backend/` 目录下。

---

## 使用说明

前端为单页应用，包含七个标签页：

| 标签页 | 用途 |
| --- | --- |
| **答题** | 选择模块（全部 / 计算机网络 / 操作系统 / MySQL / Redis）随机抽题，选择题点选项作答、简答题输入答案，实时判分并展示解析，可随时收藏。 |
| **每日一练** | 当天固定 5 道题，同一天反复打开题目不变；每道题的答案都会持久化，刷新后可以继续，可点"再来 5 题"追加且不重复。 |
| **复习** | 展示所有"到期且未熟练"的题目，按最久未复习排序，配合间隔重复算法巩固。 |
| **错题本** | 汇总答错的题与错次，确认掌握后可移出。 |
| **收藏** | 查看收藏的重点题目。 |
| **统计** | 总正确率、各模块正确率、掌握度（薄弱 / 一般 / 熟练）分布。 |
| **历史** | 查看最近 30 天每日练习的已答数量、正确率、完成率、完成状态和逐题作答详情，以及当前连续完成天数。 |

---

## API 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查 |
| GET | `/api/questions` | 组卷抽题，支持 `module`、`type`、`limit`（1–50）参数 |
| POST | `/api/answers` | 提交答案（每日练习额外传入 `daily_practice_id`），返回判分结果与解析 |
| GET | `/api/wrong-questions` | 查看错题本列表 |
| DELETE | `/api/wrong-questions/{question_id}` | 将错题标记为已掌握并移出 |
| GET | `/api/favorites` | 查看收藏列表 |
| POST | `/api/favorites/{question_id}` | 收藏一道题 |
| DELETE | `/api/favorites/{question_id}` | 取消收藏 |
| GET | `/api/stats` | 学习统计：总正确率、各模块正确率、掌握度分布 |
| GET | `/api/daily` | 获取或创建当天每日练习，并返回已保存的作答进度 |
| POST | `/api/daily/extend` | 为当天每日练习追加最多 5 道不重复题目 |
| GET | `/api/daily/history` | 获取最近练习记录；`days` 参数支持 1–365 天 |
| GET | `/api/daily/history/{day}` | 获取指定日期的逐题练习详情 |
| GET | `/api/review` | 查看当前到期、待复习的题目 |

完整的请求 / 响应结构与在线调试见启动后的 `/docs`。

---

## 核心机制

### 判分规则

- **选择题**：与标准答案字母（A / B / C / D）精确匹配。
- **简答题**：将参考答案按顿号拆分为关键词，用户答案包含全部关键词时判定正确，不要求与参考答案逐字一致。
- 每次作答都会自动更新错题本与题目进度。

### 掌握度（mastery_level）

| 等级 | 含义 | 前端标签 |
| --- | --- | --- |
| 0 | 尚未做过 | 无 |
| 1 | 薄弱 | 红色 |
| 2 | 一般 | 橙色 |
| 3 | 熟练 | 绿色 |

### 间隔复习策略

- 连续答对后，下次复习间隔按 **1 → 3 → 7 → 14 天** 逐级拉长；
- 一旦答错，立即重置为"马上复习"；
- "复习"页只展示 `next_review_at <= 现在` 且 `mastery_level < 3` 的题目。

### 每日一练选题策略

默认 5 题按 **2 道到期复习题 + 2 道薄弱题 + 1 道全新题** 组卷，不足部分随机补足；以当天日期作为随机种子，并将题目写入每日练习记录，保证同一天打开题目一致。

每道作答会单独写入每日练习明细。重复提交同一道每日练习题不会重复累计答题记录；答完全部题目后记录完成时间，历史页据此计算连续完成天数。

---

## 数据模型

应用共使用 7 张表：

| 表名 | 作用 | 关键字段 |
| --- | --- | --- |
| `question` | 题目库 | `module`、`chapter`、`type`、`stem`、`options`、`answer`、`explanation`、`difficulty` |
| `answer_record` | 答题流水 | `question_id`、`user_answer`、`is_correct` |
| `wrong_question` | 错题本 | `question_id`、`wrong_count`、`last_wrong_at` |
| `favorite` | 收藏 | `question_id`、`created_at` |
| `question_progress` | 每题学习档案 | `attempt_count`、`correct_count`、`consecutive_correct`、`mastery_level`、`last_answered_at`、`next_review_at` |
| `daily_practice` | 每日练习汇总 | `date`、`question_ids`、`total`、`correct`、`is_completed`、`started_at`、`completed_at` |
| `daily_practice_item` | 每日练习题目明细 | `practice_id`、`question_id`、`position`、`user_answer`、`is_correct`、`answered_at` |

---

## 测试

测试使用独立的测试数据库，不会污染真实数据。

```bash
pip install -r requirements-dev.txt
pytest
```

当前共 **43 个测试用例**，覆盖答题判分与间隔复习、收藏 / 错题本、统计接口、每日一练选题与持久化、重复提交、历史统计与详情、旧数据兼容、参数校验、HTML 安全转义，以及关键前端交互。当前测试全部通过。

---

## 题库说明

题库由 `backend/scripts/seed.py` 维护，共 **224 道**（184 道选择题 + 40 道简答题），题干、答案与解析均为独立编写：

| 模块 | 代码 | 题量 | 覆盖章节 |
| --- | --- | --- | --- |
| 计算机网络 | `network` | 60 | 网络模型、访问网页、Linux 网络、HTTP / HTTPS、TCP / UDP、IP 与 ICMP |
| 操作系统 | `os` | 51 | 硬件结构、内存管理、进程与线程、调度算法、文件系统、设备管理、网络系统 |
| MySQL | `mysql` | 54 | 查询执行、行记录、索引、事务与 MVCC、锁、日志、Buffer Pool、架构 |
| Redis | `redis` | 59 | 数据类型与底层结构、AOF / RDB、过期与淘汰、分布式锁、主从复制、哨兵、Cluster、缓存问题与一致性 |

> 知识范围参考了小林 Coding《图解网络》《图解系统》《图解 MySQL》《图解 Redis》的目录组织，内容为重新编写。

---

## 开发路线图

详见 [DEV_LOG.md](DEV_LOG.md)，规划方向包括：

1. 改进简答题评价（自评 + 关键点遗漏提示）；
2. 补齐工程质量（数据库迁移、统一模块枚举、统一错误响应等）；
3. 丰富学习分析（历史筛选、趋势统计与薄弱知识点聚合）；
4. 用户体系与上线（登录、多用户隔离、PostgreSQL、部署）；
5. AI 能力（简答题点评、个性化追问、模拟面试）。

---

## 致谢

- 知识体系参考自 [小林 Coding](https://xiaolincoding.com/) 的图解系列，特此致谢。
- 本题库内容、代码与解析均为学习用途原创整理，如有疏漏欢迎提 Issue 指正。

---

> 本项目为个人学习项目，仅供学习与求职复习使用。
