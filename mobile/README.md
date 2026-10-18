# 面试八股 · Android 单机版

这是 Android 单机版（Capacitor）：**没有服务器、没有域名、没有登录**，题库和学习数据都在手机本地。

## 结构

```text
mobile/
├── www/
│   ├── index.html              # 移动端界面
│   ├── css/app.css             # 主题、底部导航、环形进度
│   ├── js/local-api.js         # 拦截 /api/*，把业务逻辑放到本地
│   └── data/
│       ├── questions.json      # 224 道题（id 使用稳定 code）
│       ├── key_point_aliases.json
│       └── manifest.json
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

## 界面

- 底部 5 个 Tab：答题 / 每日 / 复习 / 错题 / 我的
- 每日一练顶部有环形进度，实时显示完成题数和正确率
- “我的”页有总正确率环形图、掌握度分布、各模块正确率
- 打卡记录改为月历：已完成绿色、进行中黄色、今天描边，点日期看当天答题详情
- 收藏夹和打卡日历收进“我的”，避免底部导航过挤
- 颜色按模块区分：计网蓝、操作系统紫、MySQL 金、Redis 红

## 数据是怎么来的

在 `backend/` 目录执行：

```bash
# 题库 + 关键点别名
python -m scripts.export_app_data
```

当前 APK **不打包学习数据**，首次安装或从旧版本升级时，会清空一次本地答题/错题/收藏/进度/每日练习，从“没做过”的状态开始。

`local-api.js` 里的 `USER_DATA_VERSION` 控制这次清理；以后如果要再次清空，改这个值即可。

`--with-user-data` 仍可用于导出当前后端数据库里的学习数据作为备份，但当前 APK 不会自动导入它。

旧版导出命令（可选，仅备份）：

```bash
python -m scripts.export_app_data --with-user-data
```

默认输出到 `mobile/www/data/`。题目 id 使用稳定 `code`（如 `network-0041`），
所以以后题目顺序调整不会让学习记录错位。

如果手动运行 `--with-user-data` 生成 `user_data.json`，它包含个人数据，已被 `.gitignore` 排除；当前 APK 不会打包或自动导入它。

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
- Android Studio（含 Android SDK Platform 36）
- JDK 21（Android Studio 的 JBR 21 即可）
- 可选：Android 真机或模拟器

```bash
cd mobile
npm install
npx cap sync android
npx cap open android
```

如果命令行构建，先设置 JDK 21，再执行：

```powershell
$env:JAVA_HOME = "$env:USERPROFILE\.jdks\jbr-21.0.11"
cd mobile/android
.\gradlew.bat assembleDebug --no-daemon
```

> Gradle 8.14.3 不支持 Java 25，必须用 JDK 21。`build.gradle` 已配置阿里云 Maven 镜像，避免从 Google Maven 下载依赖时 TLS 握手失败。

在 Android Studio 里：

1. 等待 Gradle 同步；
2. `Build → Generate App Bundles or APKs → Generate APKs` 生成 debug APK；
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
- [x] 底部 5 Tab、每日环形进度、我的统计环形图
- [x] 打卡记录月历 + 当天答题详情
- [x] 空数据启动 + 旧版升级自动清理
- [x] Node 冒烟测试 + 390 宽界面检查
- [ ] Android 真机验证
- [x] Debug APK 打包
- [ ] Release 签名
- [ ] 导出 / 导入备份
- [ ] 本地复习提醒

## 注意

- 没有网络权限依赖，断网可用；
- 没有登录和多用户，数据只属于这台手机；
- 如果以后要做云同步，再启用 `backend/` 的服务端版本。
