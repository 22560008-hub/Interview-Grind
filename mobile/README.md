# 面试八股 · Android 单机版

这是当前 Web 版的 Capacitor 包装：**没有服务器、没有域名、没有登录**，题库和学习数据都在手机本地。

## 结构

```text
mobile/
├── www/
│   ├── index.html              # 复用现有 Web UI，加了移动端样式
│   ├── js/local-api.js         # 拦截 /api/*，把业务逻辑放到本地
│   └── data/
│       ├── questions.json      # 224 道题（id 使用稳定 code）
│       ├── key_point_aliases.json
│       ├── manifest.json
│       └── user_data.json      # 个人学习数据，不提交 Git
├── scripts/smoke-local-api.mjs # Node + fake-indexeddb 冒烟测试
├── android/                    # Capacitor 生成的 Android 工程
└── capacitor.config.json
```

`local-api.js` 在页面加载时覆盖 `window.fetch`：

```text
页面 fetch('/api/answers')
        ↓
local-api.js 路由到 IndexedDB
        ↓
返回和 FastAPI 一样的 JSON
```

所以 `index.html` 的业务代码基本不用改。

## 数据是怎么来的

在 `backend/` 目录执行：

```bash
# 题库 + 关键点别名
python -m scripts.export_app_data

# 连同当前 interview.db 里的学习进度一起导出
python -m scripts.export_app_data --with-user-data
```

默认输出到 `mobile/www/data/`。题目 id 使用稳定 `code`（如 `network-0041`），
所以以后题目顺序调整不会让学习记录错位。

`user_data.json` 是个人数据，已在 `mobile/.gitignore` 里排除；不要提交。

## 本地测试

```bash
cd mobile
npm install
npm run smoke
```

冒烟测试覆盖：题库读取、简答题预判、答题、统计、收藏、每日一练、错题、复习和关键点匹配。

## 构建 APK

前置条件：

- Node.js 20+
- Android Studio（含 Android SDK、JDK）
- 可选：Android 真机或模拟器

```bash
cd mobile
npm install
npx cap sync android
npx cap open android
```

在 Android Studio 里：

1. 等待 Gradle 同步；
2. `Build → Build Bundle(s) / APK(s) → Build APK(s)` 生成 debug APK；
3. 正式分发时用 `Build → Generate Signed Bundle / APK` 创建 keystore 并打 release 包。

生成路径通常在：

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

## 数据备份

目前数据在 WebView 的 IndexedDB 里。卸载 App 或清除应用数据会丢失。
后续要加“导出 / 导入 JSON 备份”按钮，避免进度丢失。

## 当前完成度

- [x] Capacitor Android 工程
- [x] 题库 / 别名 JSON 导出
- [x] 本地 API：题目、简答预判、答题、错题、收藏、统计、复习
- [x] 本地 API：每日一练、追加题目、历史、连续打卡
- [x] 移动端基础样式
- [x] Node 冒烟测试
- [ ] Android 真机验证
- [ ] APK 签名与打包
- [ ] 导出 / 导入备份
- [ ] 本地复习提醒

## 注意

- 没有网络权限依赖，断网可用；
- 没有登录和多用户，数据只属于这台手机；
- 如果以后要做云同步，再启用 `backend/` 的服务端版本。
