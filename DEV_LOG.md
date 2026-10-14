# 后端八股刷题助手 - 开发日志

> 从零手动开发的面试刷题工具，技术栈 Python FastAPI + SQLAlchemy + SQLite + 原生 HTML/JS。

---

## 2026-10-14 阶段进展

### 一、整体架构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── core/                # 配置中心
│   │   ├── config.py        # 配置项
│   │   └── database.py      # 数据库连接/会话/Base
│   ├── models/              # ORM 数据模型
│   │   ├── question.py      # Question 题目表
│   │   ├── answer.py         # AnswerRecord 答题记录 + WrongQuestion 错题表
│   │   └── favorite.py       # Favorite 收藏表
│   ├── schemas/             # Pydantic 接口出入参定义
│   │   ├── question.py
│   │   └── answer.py
│   ├── services/            # 业务逻辑层
│   │   ├── question_service.py   # 随机抽题
│   │   ├── answer_service.py     # 判分逻辑
│   │   ├── wrong_service.py      # 错题本增删查
│   │   ├── favorite_service.py   # 收藏增删查
│   │   └── stats_service.py      # 统计分析
│   └── api/                 # 路由层
│       ├── questions.py
│       ├── answers.py
│       ├── wrong.py
│       ├── favorites.py
│       └── stats.py
├── scripts/
│   └── seed.py              # 题库种子数据
├── static/
│   └── index.html           # 前端单页应用
├── venv/                    # Python 虚拟环境
├── interview.db             # SQLite 数据库文件
└── requirements.txt         # 依赖清单
```

分层调用链：**前端请求 → api 路由 → services 业务逻辑 → models ORM → SQLite 数据库**

---

### 二、已完成功能

**1. 后端骨架**
- FastAPI + SQLAlchemy + SQLite 技术栈
- 自动生成接口文档（/docs）
- CORS 跨域配置

**2. 数据模型（4 张表）**

| 表名 | 作用 | 关键字段 |
|------|------|----------|
| `question` | 题目表 | module, chapter, type, stem, options, answer, explanation, difficulty |
| `answer_record` | 答题流水 | question_id, user_answer, is_correct |
| `wrong_question` | 错题本 | question_id, wrong_count, last_wrong_at |
| `favorite` | 收藏 | question_id, created_at |

**3. 后端接口（共 8 个）**

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/questions` | 随机抽题（支持 module 参数筛选） |
| POST | `/api/answers` | 提交答案，返回判分结果和解析 |
| GET | `/api/wrong-questions` | 查看错题本列表 |
| DELETE | `/api/wrong-questions/{question_id}` | 移除错题（已掌握） |
| GET | `/api/favorites` | 查看收藏列表 |
| POST | `/api/favorites/{question_id}` | 收藏一道题 |
| DELETE | `/api/favorites/{question_id}` | 取消收藏 |
| GET | `/api/stats` | 学习统计（总正确率 + 分模块正确率） |

**4. 判分逻辑**
- 选择题：精确匹配答案字母（A/B/C/D）
- 简答题：按顿号拆分成关键词，命中即算对
- 答错自动写入/累加错题本，答对自动从错题本移除

**5. 前端单页应用**（static/index.html）
- 四个标签页：答题 / 错题本 / 收藏 / 统计
- 模块筛选按钮：全部 / 计算机网络 / 操作系统 / MySQL / Redis
- 答题页面：选择题点选项直接提交，简答题输入框提交
- 答题结果展示：对错提示 + 正确答案 + 解析
- 答题时可收藏题目（⭐按钮）
- 错题本：显示错次和最近错误时间，可"已掌握移出"
- 统计页：总正确率 + 各模块正确率

---

### 三、题库情况

**种子脚本：scripts/seed.py**

用 `C()`（选择题）和 `S()`（简答题）两个辅助函数构造题目，幂等插入（按题干去重，重复运行不会重复插入）。

| 模块 | 模块名 | 覆盖章节 | 约题量 |
|------|--------|----------|--------|
| 计算机网络 | `network` | 网络模型、访问网页、Linux网络、HTTP、HTTPS、TCP、UDP、IP与ICMP | ~55 道 |
| 操作系统 | `os` | 硬件结构、内存管理、进程与线程、调度算法、文件系统、设备管理、网络系统 | ~45 道 |
| MySQL | `mysql` | 查询执行、行记录、索引、事务与MVCC、锁、日志、Buffer Pool、架构 | ~45 道 |
| Redis | `redis` | 基础、数据类型、底层数据结构、AOF、RDB、过期与淘汰、分布式锁、主从复制、哨兵、Cluster、缓存问题、缓存一致性 | ~55 道 |

**合计约 200 道题**，知识范围参考小林 Coding 的图解系列（图解网络、图解系统、图解 MySQL、图解 Redis）。

---

### 四、踩坑记录

1. **建表没生效** — models 写好后运行 seed，表没建出来。原因是 `main.py` 只 import 了 question 模型，没 import answer 模型。教训：**每加一张新表，都要在 main.py 的 import 里登记**，SQLAlchemy 才知道要建这张表。

2. **目录结构建错** — 最初把 services 文件夹建在了 core 里面，scripts 文件夹的 `__init__.py` 少打了一个下划线，通过 git commit 输出发现并修正。

3. **ImportError: cannot import name 'xxx'** — 加新模块（favorites）时，main.py 里 include_router 引用了 `favorites`，但 `app/api/` 目录下还没建 `favorites.py` 文件，导致启动报错。教训：**路由文件和 main.py 里的引用要成对出现**。

4. **StaticFiles 挂载位置** — `app.mount("/", StaticFiles(...))` 必须放在所有 `include_router` 之后，否则会把 API 路由也覆盖掉。

5. **简答题判分太严格** — 最初简答题要求完全一致才算对，太苛刻。改成按顿号拆分关键词匹配后更合理。

---

### 五、技术备忘

**常用命令：**
```bash
# 激活虚拟环境
venv\Scripts\activate

# 启动后端（热重载）
uvicorn app.main:app --reload

# 灌入/更新题库
python -m scripts.seed

# 查看 git 历史
git log --oneline
```

**访问地址：**
- 接口文档（Swagger UI）：http://127.0.0.1:8000/docs
- 前端页面：http://127.0.0.1:8000/

**依赖清单（requirements.txt）：**
- fastapi
- uvicorn[standard]
- sqlalchemy
- pydantic-settings

---

### 六、待做功能（路线图）

| 优先级 | 功能 | 说明 |
|--------|------|------|
| 高 | 每日一练 | 每天固定出几道题，连续打卡 |
| 中 | 用户登录 | 多用户数据隔离 |
| 中 | AI 辅助解析 | 答题后 AI 生成个性化讲解 |
| 低 | 部署上线 | 部署到云服务器，手机也能刷 |
