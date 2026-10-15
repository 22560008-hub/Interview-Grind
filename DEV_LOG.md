# 后端八股刷题助手 - 开发日志

> 从零手动开发的面试刷题工具，技术栈 Python FastAPI + SQLAlchemy + SQLite + 原生 HTML/JS。

---

## 2026-10-15 阶段进展

### 一、复习功能上线

- 新增 `review_service.py`：查询 `next_review_at <= 现在` 且 `mastery_level < 3` 的题，按最久没复习排序
- 新增 `GET /api/review` 接口
- 前端新增"复习"标签页，展示待复习题目，带掌握程度标签（薄弱红/一般橙），支持选择/简答题答题和得分统计

### 二、掌握度全面接入产品

- 出题接口 `/api/questions` 和每日一练 `/api/daily` 均返回 `mastery_level` 字段
- 题目卡片旁边显示掌握程度标签：红色薄弱、橙色一般、绿色熟练
- 统计页新增掌握度分布：薄弱/一般/熟练各多少道

### 三、每日一练选题升级

- 选题策略改为：**50% 到期复习题 + 30% 薄弱题 + 20% 新题**，不够则随机补
- 新增"再来5题"功能：答完一批后可无限追加，已出过的题不会重复
- 接口支持 `?exclude=id1,id2` 参数排除已做过的题

### 四、工程质量：引入 pytest 测试

- 新建 `tests/` 目录，使用独立测试数据库，不污染真实数据
- 共 25 条测试全部通过，覆盖：
  - 答题判分逻辑（答错进错题本、间隔复习策略、简答题关键词匹配）
  - API 接口（出题、答题、复习、每日一练）
  - 收藏/错题本服务
  - 统计接口（正确率、模块分布、掌握度）
- 2 条 xfail 标记已知待改进项：
  1. 出题接口提前返回了答案和解析，待拆分出题与判题响应
  2. 每日一练选题比例未严格做到 50/30/20，复习题可能挤掉新题

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
│   │   ├── favorite.py       # Favorite 收藏表
│   │   └── progress.py       # QuestionProgress 题目进度表
│   ├── schemas/             # Pydantic 接口出入参定义
│   │   ├── question.py
│   │   └── answer.py
│   ├── services/            # 业务逻辑层
│   │   ├── question_service.py   # 随机抽题
│   │   ├── answer_service.py     # 判分 + 更新进度
│   │   ├── wrong_service.py      # 错题本增删查
│   │   ├── favorite_service.py   # 收藏增删查
│   │   ├── stats_service.py      # 统计分析
│   │   └── daily_service.py      # 每日一练抽题
│   └── api/                 # 路由层
│       ├── questions.py
│       ├── answers.py
│       ├── wrong.py
│       ├── favorites.py
│       ├── stats.py
│       └── daily.py
├── scripts/
│   └── seed.py              # 题库种子数据（229道）
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

**2. 数据模型（6 张表）**

| 表名                | 作用     | 关键字字段                                                                                                      |
| ------------------- | -------- | --------------------------------------------------------------------------------------------------------------- |
| `question`          | 题目表   | module, chapter, type, stem, options, answer, explanation, difficulty                                           |
| `answer_record`     | 答题流水 | question_id, user_answer, is_correct                                                                            |
| `wrong_question`    | 错题本   | question_id, wrong_count, last_wrong_at                                                                         |
| `favorite`          | 收藏     | question_id, created_at                                                                                         |
| `question_progress` | 题目进度 | question_id, attempt_count, correct_count, consecutive_correct, mastery_level, last_answered_at, next_review_at |

**3. 后端接口（共 9 个）**

| 方法   | 路径                                 | 功能                                |
| ------ | ------------------------------------ | ----------------------------------- |
| GET    | `/api/questions`                     | 随机抽题（支持 module 参数筛选）    |
| POST   | `/api/answers`                       | 提交答案，返回判分结果和解析        |
| GET    | `/api/wrong-questions`               | 查看错题本列表                      |
| DELETE | `/api/wrong-questions/{question_id}` | 移除错题（已掌握）                  |
| GET    | `/api/favorites`                     | 查看收藏列表                        |
| POST   | `/api/favorites/{question_id}`       | 收藏一道题                          |
| DELETE | `/api/favorites/{question_id}`       | 取消收藏                            |
| GET    | `/api/stats`                         | 学习统计（总正确率 + 分模块正确率） |
| GET    | `/api/daily`                         | 每日一练（当天固定5道题）           |

**4. 判分逻辑**

- 选择题：精确匹配答案字母（A/B/C/D）
- 简答题：按顿号拆分成关键词，命中即算对
- 答错自动写入/累加错题本
- 每次答题自动更新题目进度（答题次数、正确率、掌握程度、下次复习时间）

**5. 题目进度模型（QuestionProgress）**

每道题维护一条学习档案：

- `attempt_count`：累计答题次数
- `correct_count`：累计答对次数
- `consecutive_correct`：连续答对次数
- `mastery_level`：掌握程度（0=没做过 1=薄弱 2=一般 3=熟练）
- `next_review_at`：下次建议复习时间（答对了往后推，答错了马上再练）

间隔复习策略：连续答对 0→1→3→7→14 天后再复习，答错了立即复习。

**6. 每日一练（基础版）**

- 用当天日期当随机种子，同一天每次打开都是同一套5道题
- 支持选择题和简答题混合答题
- 逐题作答，全部答完后显示今日得分

**7. 前端单页应用**（static/index.html）

- 五个标签页：答题 / 每日一练 / 错题本 / 收藏 / 统计
- 模块筛选按钮：全部 / 计算机网络 / 操作系统 / MySQL / Redis
- 答题页面：选择题点选项直接提交，简答题输入框提交
- 答题结果展示：对错提示 + 正确答案 + 解析
- 答题时可收藏题目（⭐按钮）
- 错题本：显示错次，可"已掌握移出"
- 统计页：总正确率 + 各模块正确率
- 每日一练：一次性展示5道题，答完显示得分

---

### 三、题库情况

**种子脚本：scripts/seed.py（共 226 道题）**

用 `C()`（选择题）和 `S()`（简答题）两个辅助函数构造题目，幂等插入（按题干去重，重复运行不会重复插入）。

| 模块       | 模块名    | 覆盖章节                                                                                                    | 约题量 |
| ---------- | --------- | ----------------------------------------------------------------------------------------------------------- | ------ |
| 计算机网络 | `network` | 网络模型、访问网页、Linux网络、HTTP、HTTPS、TCP、UDP、IP与ICMP                                              | ~55 道 |
| 操作系统   | `os`      | 硬件结构、内存管理、进程与线程、调度算法、文件系统、设备管理、网络系统                                      | ~45 道 |
| MySQL      | `mysql`   | 查询执行、行记录、索引、事务与MVCC、锁、日志、Buffer Pool、架构                                             | ~60 道 |
| Redis      | `redis`   | 基础、数据类型、底层数据结构、AOF、RDB、过期与淘汰、分布式锁、主从复制、哨兵、Cluster、缓存问题、缓存一致性 | ~69 道 |

知识范围参考小林 Coding 的图解系列（图解网络、图解系统、图解 MySQL、图解 Redis）。

---

### 四、踩坑记录

1. **建表没生效** — models 写好后运行 seed，表没建出来。原因是 `main.py` 只 import 了 question 模型，没 import answer 模型。教训：**每加一张新表，都要在会触发 create_all 的地方 import**。

2. **目录结构建错** — 最初把 services 文件夹建在了 core 里面，scripts 文件夹的 `__init__.py` 少打了一个下划线，通过 git commit 输出发现并修正。

3. **ImportError: cannot import name 'xxx'** — 加新模块时，main.py 里 include_router 引用了新路由文件，但 `app/api/` 目录下还没建对应文件，导致启动报错。教训：**路由文件和 main.py 里的引用要成对出现**。

4. **StaticFiles 挂载位置** — `app.mount("/", StaticFiles(...))` 必须放在所有 `include_router` 之后，否则会把 API 路由也覆盖掉。

5. **简答题判分太严格** — 最初简答题要求完全一致才算对，太苛刻。改成按顿号拆分关键词匹配后更合理。

6. **ORM default 不生效** — SQLAlchemy 的 `Column(default=0)` 是 INSERT 时才填的默认值，刚 new 出来的 Python 对象实例属性还是 None。新建对象时要显式赋初始值，否则 `+=` 会报 NoneType 错误。

7. **只 import 一个模型导致 relationship 报错** — 查询带 relationship 的表时，如果只 import 了当前模型没 import 关联的模型，会报 `NoReferencedTableError`。查询命令里要把关联模型一起 import。

8. **前端 DOM 嵌套错误** — 每日一练的容器 div 被误放进了答题页的容器里，切换标签时父容器隐藏导致子元素看不见。各视图容器要平级放在 body 下。

---

### 五、技术备忘

**常用命令：**

```bash
cd interview-app\backend

# 激活虚拟环境
venv\Scripts\activate

#退出虚拟环境
deactivate

# 启动后端（热重载）
uvicorn app.main:app --reload

# 灌入/更新题库
python -m scripts.seed

# 建新表（手动触发）
python -c "from app.core.database import Base, engine; from app.models import question, progress; Base.metadata.create_all(bind=engine)"

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

### 六、开发路线图

#### 第一阶段：把掌握度真正接入产品（最高优先级）

目标：从"刷题器"变成"间隔复习工具"。

- 增加"待复习题"查询接口
- 每日一练优先选 `next_review_at <= 当前时间` 的到期题
- 选题比例：**50% 到期复习题 + 30% 薄弱题/近期错题 + 20% 从未做过的新题**
- 统计页展示薄弱/一般/熟练题目数量
- 题目卡片增加掌握度颜色标签

#### 第二阶段：持久化每日练习

- 新增每日练习记录表，保存：日期、题目列表、是否完成、正确数量、开始时间、完成时间、用时
- 刷新页面后仍能继续当天练习，不能重新生成另一套
- 支持连续打卡和历史记录

#### 第三阶段：改进简答题评价

当前关键词全包含判分容易误判，改为更适合八股复习的方式：

- 用户先自己回答
- 展示参考答案和关键点
- 标出遗漏的关键点
- 用户自评"掌握 / 模糊 / 不会"
- 根据自评和关键词结果共同安排复习
- AI 判分以后再加，不现在依赖

#### 第四阶段：补工程质量

功能继续扩大前先处理技术债：

- 修正 .gitignore，从 Git 中移除已跟踪的 venv（当前 1750 个受 Git 管理文件中 1717 个来自虚拟环境）
- 引入数据库迁移工具
- 给判分、进度更新、每日选题写测试
- 统一模块枚举
- 区分出题响应和答案响应的 schema
- 为接口增加错误处理
- 前端 API 地址改成相对路径

#### 第五阶段：用户与上线

单用户复习闭环稳定后再做：

- 用户注册与登录
- 每个用户独立的进度、错题和收藏
- SQLite 切换 PostgreSQL
- 部署和数据备份
- 手机端适配
- 管理端录题和修改题目

#### 第六阶段：AI 能力

AI 最适合放在这些位置：

- 简答题关键点点评，根据用户答案指出遗漏
- 用更容易理解的方式重新解释
- 针对薄弱知识点生成追问
- 模拟真实面试连续追问

注意：不要让 AI 负责基础选择题判分，也不要把 AI 放在间隔复习系统之前做。
