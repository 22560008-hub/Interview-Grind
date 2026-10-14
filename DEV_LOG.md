# 后端八股刷题助手 - 开发日志

## 2026-10-14 阶段进展

### 已完成功能

**1. 后端骨架**
- FastAPI + SQLAlchemy + SQLite 技术栈搭建
- 分层架构：api（路由）→ services（业务逻辑）→ models（ORM）→ SQLite
- 目录结构：app/core、app/models、app/schemas、app/services、app/api、scripts

**2. 数据模型（4 张表）**
- `question`：题目表（模块、章节、题型、题干、选项、答案、解析、难度）
- `answer_record`：答题流水记录
- `wrong_question`：错题本（错次、最近错误时间）
- `favorite`：收藏表

**3. 后端接口**
- `GET /api/questions` — 随机抽题（支持模块筛选）
- `POST /api/answers` — 提交答案判分
- `GET /api/wrong-questions` — 查看错题本
- `DELETE /api/wrong-questions/{id}` — 移除错题
- `GET /api/favorites` — 查看收藏列表
- `POST /api/favorites/{id}` — 收藏题目
- `DELETE /api/favorites/{id}` — 取消收藏
- `GET /api/stats` — 学习统计（总正确率 + 分模块）

**4. 判分逻辑**
- 选择题：精确匹配答案字母
- 简答题：按顿号拆分关键词，命中即算对

**5. 前端单页应用**（static/index.html）
- 四个标签页：答题 / 错题本 / 收藏 / 统计
- 模块筛选按钮：全部 / 计算机网络 / 操作系统 / MySQL / Redis
- 答题时可收藏题目（⭐按钮）
- FastAPI 通过 StaticFiles 挂载，直接访问 http://127.0.0.1:8000/

**6. 题库扩充**
- 种子脚本 scripts/seed.py 约 200 道题
- 覆盖四大模块：
  - network（计算机网络）：网络模型、HTTP、HTTPS、TCP、UDP、IP/ICMP、Linux网络
  - os（操作系统）：硬件结构、内存管理、进程线程、调度、文件系统、设备管理、网络系统
  - mysql：查询执行、行记录、索引、事务与MVCC、锁、日志、Buffer Pool、架构
  - redis：基础、数据类型、底层数据结构、AOF、RDB、过期与淘汰、分布式锁、主从复制、哨兵、Cluster、缓存问题、缓存一致性

### 技术备忘

- 后端启动：`uvicorn app.main:app --reload`
- 灌题库：`python -m scripts.seed`
- 接口文档：http://127.0.0.1:8000/docs
- 前端页面：http://127.0.0.1:8000/
- 数据库文件：backend/interview.db
- venv 激活：`venv\Scripts\activate`

### 待做功能（路线图）
- 每日一练
- 用户登录（多用户隔离）
- AI 辅助解析
- 部署上线
