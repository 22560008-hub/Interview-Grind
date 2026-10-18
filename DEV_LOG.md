# 后端八股刷题助手 - 开发日志

> 从零手动开发的面试刷题工具，技术栈 Python FastAPI + SQLAlchemy + SQLite + 原生 HTML/JS。

---

## 当前已完成功能总览

- **题库与组卷**：内置 224 道题，覆盖计算机网络、操作系统、MySQL、Redis；支持按模块和题型随机抽题
- **题库维护**：每题有稳定 `code`；seed 全字段同步，改答案 / 解析 / 选项后重跑即可生效；从 seed 删除的题软停用，学习记录不丢
- **答题与判分**：选择题自动判分；简答题先分析关键点，再由用户自评“掌握 / 模糊 / 不会”；关键点支持同义词、缩写、中英写法，能识别否定句并区分“疑似覆盖”；用户输入经过 HTML 安全转义
- **错题与收藏**：答错自动进入错题本并累计错次；支持收藏、取消收藏和将错题标记为已掌握
- **掌握度与间隔复习**：维护每题的答题次数、连续答对次数、掌握等级和下次复习时间；复习页按到期时间排序
- **每日一练**：每天固定生成一套题，按到期题、薄弱题和新题混合选题；支持逐题保存、刷新恢复和继续追加题目
- **每日练习一致性**：校验题目归属，重复提交不会重复写入答题流水或进度；追加题目后正确更新完成状态
- **练习历史**：展示最近练习的已答数量、正确率、完成率和完成状态；支持连续打卡统计与逐题详情
- **学习统计**：展示总答题量、总正确率、各模块正确率和掌握度分布
- **前端应用**：现有答题、每日一练、复习、错题本、收藏、统计、历史 7 个标签页
- **工程基础**：FastAPI 自动接口文档、分层业务结构、独立测试数据库；当前 97 个自动化测试全部通过

---

## 2026-10-18 阶段进展

### 一、题库同步机制重做

- `question` 增加 `code`（稳定标识）与 `is_active`（是否在役），旧库启动时自动补列和索引，重复执行安全
- `sync_questions()` 改为按 `code` 优先、题干兜底认领旧题，并更新模块、章节、题型、题干、选项、答案、关键点、解析、难度全部字段
- seed 中消失的题改为 `is_active=0` 软停用，答题记录、错题、收藏、掌握度全部保留
- 抽题、复习、每日一练、错题本、收藏、掌握度统计统一过滤停用题
- 新增 `scripts/legacy_questions.py`：按显式映射把旧题的答题流水、错题、收藏、进度合并到接替题，重复执行安全
- 处理历史遗留的 2 道孤儿题（进程 / 线程、TCP 握手的旧版本），共迁移 8 条答题记录，数据库回到 224 道在役题
- 同步时发现并修复一处真实内容漂移：`产生死锁的四个必要条件是什么？` 的章节、答案、解析、难度此前只改了 seed，数据库仍在发旧版答案

### 二、接口与前端收尾

- 前端 API 地址改为同源相对路径，换端口、换域名、手机访问不再需要改代码
- `setModule()` 改为显式传入按钮元素，去掉对隐式全局 `event` 的依赖
- 新增 `app/core/constants.py`：`Module` / `QuestionType` 枚举；`/api/questions` 非法参数返回 422
- 统一错误响应：不存在的题目返回 404；`/api/daily/extend` 无当日练习返回 404，不再返回 HTTP 200 + `error` 字段
- `ensure_question_schema()` 在结构已最新时不开启写事务，启动和测试不会因为数据库只读而失败
- 每日一练追加按钮在前端处理非 2xx 响应，并恢复按钮可用状态

### 三、简答题关键点匹配（Phase 1）

- 新增 `app/core/key_point_aliases.py`：为 205 个唯一关键点维护术语口径，强别名表示语义等价，弱别名表示更宽泛的说法
- 新增 `app/services/key_point_matcher.py`，匹配流程改为：归一化 → 强别名 → 否定判断 → 弱别名
- 归一化覆盖全半角、大小写、空格标点、中文数字（`三次` ↔ `3次`），中文数字只在量词前转换
- 纯英文别名按单词匹配，`TCP` 不会命中 `TCPS`，`IP` 不会命中 `IPv4`
- 否定只在同一个小句内生效：`不需要三次握手` 不算覆盖；顿号列表 `互斥、持有并等待、不可剥夺、循环等待` 不会互相误伤
- 新增“疑似覆盖”：只说了更宽泛的词（如用“索引”代替“覆盖索引”）时提示用户，但不计入覆盖率
- `/api/answers/preview` 新增 `uncertain_points` 字段，前端单独展示“疑似覆盖（不计入覆盖率）”
- 新增 `scripts/check_key_points.py` 自检工具，参考答案平均覆盖率 99.5%，40 道中 39 道 100%
- 新增 22 个匹配测试，覆盖归一化、同义词、英文词边界、否定、小句边界、疑似覆盖和参考答案回归

### 四、测试

- 新增 40 个测试（18 个题库同步 + 22 个关键点匹配），当前 **97 个测试全部通过**
- 题库侧覆盖全字段同步、软停用与恢复、按 `code` 保留进度、旧题记录合并、停用题过滤、422 / 404 语义
- 匹配侧覆盖归一化、别名、否定与小句边界、疑似覆盖、参考答案关键点回归

---

## 2026-10-16 阶段进展

### 一、简答题改为关键点预判与用户自评

- 为 `question` 增加可空的 JSON `key_points` 字段，完整参考答案和判分关键点分开维护
- 为现有 40 道简答题逐题整理 2～6 个关键点；seed 重复执行时会给已有题目补齐关键点
- 增加兼容升级逻辑，旧 SQLite 数据库自动添加 `key_points` 列，不删除题目、答题记录或学习进度
- 新增 `POST /api/answers/preview`：返回关键点覆盖率、已覆盖项、遗漏项、参考答案与解析，预判阶段不写入答题记录
- 普通答题、每日一练和复习页统一为两阶段流程，用户选择“掌握 / 模糊 / 不会”后才正式提交
- “掌握”使用原有连续答对间隔；“模糊”安排 1 天后复习；“不会”立即复习
- 覆盖率低于 50% 但选择“掌握”时进行二次确认，降低误操作概率

### 二、每日练习改为逐题持久化

- 新增 `daily_practice` 与 `daily_practice_item` 两张表，分别保存每天的练习汇总和每道题的作答状态
- `/api/daily` 会复用当天已经生成的练习，刷新页面后仍能恢复题目、用户答案和判分结果
- 提交每日练习答案时携带 `daily_practice_id`，后端校验题目是否属于本次练习
- 同一道每日练习题重复提交时直接返回已保存结果，不重复增加答题记录或进度
- 每次作答后按明细重新计算正确数量和完成状态；追加题目会重新将当天练习标记为未完成
- 兼容旧版只保存 `question_ids` 的每日练习数据，首次读取时自动补齐明细

### 三、练习历史上线

- 新增 `GET /api/daily/history`，返回最近练习的题目总数、已答数量、答对数量、已答正确率、完成率和完成状态
- 新增 `GET /api/daily/history/{day}`，按原始顺序返回指定日期的逐题作答详情
- 连续打卡按“完成整套每日练习”计算；如果今天尚未完成，则保留截至昨天的连续天数
- `days` 参数限制为 1–365，非法日期返回 422，不存在的日期返回 404
- 前端新增独立“历史”标签页，支持详情展开/收起、加载状态、失败提示和空数据提示
- 历史详情在前端缓存，重复展开不再次请求；当天继续答题或追加题目后自动清除旧缓存

### 四、安全性和历史语义修正

- 简答题用户输入由后端生成 `display_user_answer` 安全文本，前端不再直接插入原始答案，避免 HTML/XSS 注入
- 历史正确率按“答对数 / 已答数”计算，完成率按“已答数 / 总题数”计算，避免未完成练习的统计含义混淆
- 历史详情不再返回当前 `mastery_level`，避免把现在的掌握度误认为当时的历史状态
- 历史展开控件改为语义化按钮，并同步 `aria-expanded` 状态，改善键盘和读屏使用体验

### 五、测试基础完善

- 当前共有 **57 个测试，全部通过**
- 新增每日练习归属校验、重复提交、页面恢复、追加题目和安全转义测试
- 新增历史正确率/完成率、连续打卡、参数校验、404、旧数据迁移和详情安全展示测试
- 前端关键行为通过 Node 执行页面脚本，覆盖 `daily_practice_id` 传递、历史详情缓存和安全渲染

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
│   └── seed.py              # 题库种子数据（226）
├── static/
│   └── index.html           # 前端单页应用
├── venv/                    # Python 虚拟环境
├── interview.db             # SQLite 数据库文件
└── requirements.txt         # 依赖清单
```

分层调用链：**前端请求 → api 路由 → services 业务逻辑 → models ORM → SQLite 数据库**

---

### 二、截至 2026-10-14 已完成功能

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

**种子脚本：scripts/seed.py（当前共 224 道题）**

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

# 改题干前查稳定 code（把“关键词”换成题干片段）
python -c "from app.core.database import SessionLocal; from app.models.question import Question; db=SessionLocal(); [print(q.code, q.stem) for q in db.query(Question).filter(Question.stem.like('%关键词%'))]"

# 检查关键点匹配：全部参考答案
python -m scripts.check_key_points

# 检查某道简答题的自定义答案（编号用 --list 查）
python -m scripts.check_key_points --id 7 --answer "TLS 1.3 简化了握手，1RTT 完成密钥协商"

# 建新表（手动触发，需确保所有模型均已导入）
python -c "from app.core.database import Base, engine; from app.models import question, answer, favorite, progress, daily; Base.metadata.create_all(bind=engine)"

# 查看 git 历史
git log --oneline

# 新建 git
git add -A
git commit -m ""

# 推送到 github
git push

# 测试所有接口点
pytest tests/ -v

#重置每日一练
python -c "from app.core.database import SessionLocal; from app.models.daily import DailyPractice, DailyPracticeItem; db = SessionLocal(); db.query(DailyPracticeItem).delete(); db.query(DailyPractice).delete(); db.commit(); print('已清空两张表')"
```

**题库维护流程：**

1. 改答案 / 解析 / 选项 / 难度 / 章节：直接改 `seed.py`，重跑 `python -m scripts.seed` 即可生效。
2. 改题干：先查出该题的 `code`，在对应 `C()` / `S()` 条目末尾加 `code="..."`，再重跑，学习记录不会丢。
3. 删题：从 `seed.py` 移除后重跑，题目自动 `is_active=0` 停用，答题记录和错题仍保留。
4. 不要直接改 `question` 表；`seed.py` 是题库的唯一来源。

**关键点维护流程：**

1. 新增或修改简答题关键点后，必须在 `app/core/key_point_aliases.py` 补一条术语口径；测试会强制别名表与 seed 的关键点完全对应。
2. 强别名只放“同一个技术概念”的等价说法；更宽泛、只算相关的词放 `WEAK_KEY_POINT_ALIASES`，只会提示“疑似覆盖”。
3. 改完运行 `python -m scripts.check_key_points`，确认 40 道参考答案仍能覆盖自身关键点。
4. 发现真实答案漏判时，先判断是归一化问题还是缺别名，再补别名并用测试锁住。

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

#### 第一阶段：把掌握度真正接入产品（已完成）

目标：从"刷题器"变成"间隔复习工具"。

- 增加"待复习题"查询接口
- 每日一练优先选 `next_review_at <= 当前时间` 的到期题
- 选题比例：**50% 到期复习题 + 30% 薄弱题/近期错题 + 20% 从未做过的新题**
- 统计页展示薄弱/一般/熟练题目数量
- 题目卡片增加掌握度颜色标签

#### 第二阶段：持久化每日练习（已完成）

- 已新增每日练习汇总表和逐题明细表，保存日期、题目、答案、判分、完成状态与时间
- 已支持刷新后继续当天练习，并防止重复提交产生重复记录
- 已支持连续打卡、历史列表和逐题详情

#### 第三阶段：改进简答题评价（第一版已完成）

已将原来的“参考答案按顿号拆分并自动判对错”改为更适合八股复习的两阶段流程：

- 用户先自己回答
- 展示参考答案和关键点
- 标出遗漏的关键点
- 用户自评"掌握 / 模糊 / 不会"
- 根据自评结果安排复习，关键点覆盖率负责反馈与低覆盖提醒
- 关键点匹配已支持同义词、缩写、中英写法、否定句和小句边界，并区分“疑似覆盖”（2026-10-18）
- AI 判分以后再加，不现在依赖

#### 第四阶段：补工程质量

功能继续扩大前先处理技术债：

- 已修正 `.gitignore`，虚拟环境和本地数据库不再被 Git 跟踪
- 题库同步与软停用（已完成）
- 引入数据库迁移工具（待做；目前为启动时幂等补列）
- 持续扩充自动化测试，目前已有 97 个测试覆盖核心业务和关键前端行为
- 统一模块枚举（已完成）
- 继续完善接口响应 schema 与统一错误处理（错误状态码已统一，响应 schema 待收口）
- 前端 API 地址改成相对路径（已完成）

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
