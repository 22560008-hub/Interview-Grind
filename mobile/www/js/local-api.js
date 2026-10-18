/*
 * 单机版本地 API。
 *
 * 在页面加载时拦截 /api/* 的 fetch，把原来发给 FastAPI 的请求路由到
 * IndexedDB 里的本地数据。这样现有 index.html 不需要改业务调用。
 */
(() => {
  "use strict";

  const nativeFetch = window.fetch.bind(window);
  const DB_NAME = "interview-grind";
  const DB_VERSION = 1;
  const API_PREFIX = "/api/";

  let dbPromise = null;
  let readyPromise = null;
  let aliases = { strong: {}, weak: {} };
  let questionById = new Map();
  let questionList = [];

  const CN_DIGITS = {
    零: 0, 一: 1, 二: 2, 两: 2, 三: 3, 四: 4,
    五: 5, 六: 6, 七: 7, 八: 8, 九: 9, 十: 10,
  };
  const CN_UNITS = "次个种天年层路台条轮步颗位只张页周月秒倍";
  const CN_NUMBER_RE = new RegExp(
    `([零一二两三四五六七八九十]+)(?=(?:分钟|毫秒|[${CN_UNITS}]))`,
    "g"
  );
  const NEGATIONS = ["不", "没", "无", "非", "未", "无需", "不能", "不会", "无法"];
  const CONTRASTS = ["而是", "但是", "然而", "反而", "不过"];
  const FALSE_NEGATIONS = ["非常", "不仅", "不但", "无论", "不断", "不同"];
  const NEGATION_WINDOW = 5;
  const NEGATION_EXEMPT = new Set(["锁过期"]);
  const CLAUSE_SPLIT_RE = /[，。；、！？,.;!?：:（）()【】\[\]\n\r]+/;

  class HttpError extends Error {
    constructor(status, detail) {
      super(detail);
      this.status = status;
    }
  }

  // ---------- 基础工具 ----------

  function openDb() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains("meta")) {
          db.createObjectStore("meta", { keyPath: "key" });
        }
        if (!db.objectStoreNames.contains("questions")) {
          db.createObjectStore("questions", { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains("progress")) {
          db.createObjectStore("progress", { keyPath: "questionId" });
        }
        if (!db.objectStoreNames.contains("wrong")) {
          db.createObjectStore("wrong", { keyPath: "questionId" });
        }
        if (!db.objectStoreNames.contains("favorites")) {
          db.createObjectStore("favorites", { keyPath: "questionId" });
        }
        if (!db.objectStoreNames.contains("records")) {
          const store = db.createObjectStore("records", {
            keyPath: "id",
            autoIncrement: true,
          });
          store.createIndex("questionId", "questionId", { unique: false });
          store.createIndex("createdAt", "createdAt", { unique: false });
        }
        if (!db.objectStoreNames.contains("daily")) {
          db.createObjectStore("daily", { keyPath: "date" });
        }
        if (!db.objectStoreNames.contains("dailyItems")) {
          const store = db.createObjectStore("dailyItems", {
            keyPath: "key",
          });
          store.createIndex("date", "date", { unique: false });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
    return dbPromise;
  }

  function requestResult(request) {
    return new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async function dbGet(store, key) {
    const db = await openDb();
    return requestResult(db.transaction(store, "readonly").objectStore(store).get(key));
  }

  async function dbGetAll(store) {
    const db = await openDb();
    return requestResult(
      db.transaction(store, "readonly").objectStore(store).getAll()
    );
  }

  async function dbGetByIndex(store, index, value) {
    const db = await openDb();
    return requestResult(
      db
        .transaction(store, "readonly")
        .objectStore(store)
        .index(index)
        .getAll(value)
    );
  }

  async function dbPut(store, value) {
    const db = await openDb();
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).put(value);
    return new Promise((resolve, reject) => {
      tx.oncomplete = () => resolve(value);
      tx.onerror = () => reject(tx.error);
    });
  }

  async function dbAdd(store, value) {
    const db = await openDb();
    const tx = db.transaction(store, "readwrite");
    const request = tx.objectStore(store).add(value);
    return new Promise((resolve, reject) => {
      tx.oncomplete = () => resolve(request.result);
      tx.onerror = () => reject(tx.error);
    });
  }

  async function dbDelete(store, key) {
    const db = await openDb();
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).delete(key);
    return new Promise((resolve, reject) => {
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => reject(tx.error);
    });
  }

  async function dbCount(store) {
    const db = await openDb();
    return requestResult(
      db.transaction(store, "readonly").objectStore(store).count()
    );
  }

  function pad(value) {
    return String(value).padStart(2, "0");
  }

  function localDate(date = new Date()) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  }

  function localIso(date = new Date()) {
    return `${localDate(date)}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(
      date.getSeconds()
    )}`;
  }

  function shiftDate(dayText, delta) {
    const date = new Date(`${dayText}T00:00:00`);
    date.setDate(date.getDate() + delta);
    return localDate(date);
  }

  function addDaysIso(days) {
    const date = new Date();
    date.setDate(date.getDate() + days);
    return localIso(date);
  }

  function formatDateTime(iso) {
    if (!iso) return "";
    return iso.slice(0, 16).replace("T", " ");
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#x27;");
  }

  function escapeRegExp(text) {
    return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function shuffle(items, random = Math.random) {
    const copy = items.slice();
    for (let i = copy.length - 1; i > 0; i -= 1) {
      const j = Math.floor(random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }

  function seededRandom(seedText) {
    let seed = 2166136261;
    for (let i = 0; i < seedText.length; i += 1) {
      seed ^= seedText.charCodeAt(i);
      seed = Math.imul(seed, 16777619);
    }
    return function random() {
      seed |= 0;
      seed = (seed + 0x6d2b79f5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // ---------- 关键点匹配（Python 版本的 JS 移植） ----------

  function parseCnNumber(text) {
    if (!text) return null;
    if (text.includes("十")) {
      const [tensText, onesText] = text.split("十");
      const tens = tensText ? CN_DIGITS[tensText] ?? 1 : 1;
      const ones = onesText ? CN_DIGITS[onesText] ?? 0 : 0;
      return tens * 10 + ones;
    }
    if (text.length === 1) {
      const value = CN_DIGITS[text];
      return value === undefined ? null : value;
    }
    return null;
  }

  function normalize(text) {
    let value = String(text).normalize("NFKC").toLowerCase();
    value = value.replace(CN_NUMBER_RE, (match, numberText) => {
      const number = parseCnNumber(numberText);
      return number === null ? match : String(number);
    });
    return value.replace(/[^0-9a-z\u4e00-\u9fff]+/g, "");
  }

  function tokenForm(text) {
    let value = String(text).normalize("NFKC").toLowerCase();
    value = value.replace(/[-_/]+/g, " ");
    return value.replace(/\s+/g, " ").trim();
  }

  function isAscii(text) {
    return /^[\x00-\x7F]+$/.test(text);
  }

  function isNegated(text, index) {
    let window = text.slice(Math.max(0, index - NEGATION_WINDOW), index);
    for (const word of FALSE_NEGATIONS) {
      window = window.split(word).join("");
    }
    if (CONTRASTS.some((marker) => window.includes(marker))) return false;
    return NEGATIONS.some((word) => window.includes(word));
  }

  function aliasMatches(alias, compactText, tokenText, checkNegation) {
    const trimmed = alias.trim();
    if (!trimmed) return false;

    if (isAscii(trimmed)) {
      const token = tokenForm(trimmed);
      if (!token) return false;
      const pattern = new RegExp(
        `(?<![0-9a-z])${escapeRegExp(token)}(?![0-9a-z])`,
        "g"
      );
      let match;
      while ((match = pattern.exec(tokenText)) !== null) {
        if (!checkNegation || !isNegated(tokenText, match.index)) return true;
      }
      return false;
    }

    const needle = normalize(trimmed);
    if (!needle) return false;
    let start = 0;
    while (true) {
      const index = compactText.indexOf(needle, start);
      if (index === -1) return false;
      if (!checkNegation || !isNegated(compactText, index)) return true;
      start = index + 1;
    }
  }

  function matchesAny(point, aliasList, compacts, tokens, checkNegation) {
    for (let i = 0; i < compacts.length; i += 1) {
      for (const alias of [point, ...aliasList]) {
        if (aliasMatches(alias, compacts[i], tokens[i], checkNegation)) {
          return true;
        }
      }
    }
    return false;
  }

  function matchKeyPoints(keyPoints, userAnswer) {
    const clauses = String(userAnswer)
      .split(CLAUSE_SPLIT_RE)
      .filter((part) => part.trim());
    const compacts = clauses.map(normalize);
    const tokens = clauses.map(tokenForm);
    const matched = [];
    const missing = [];
    const uncertain = [];

    for (const point of keyPoints || []) {
      const checkNegation = !NEGATION_EXEMPT.has(point);
      const strong = (aliases.strong && aliases.strong[point]) || [];
      if (matchesAny(point, strong, compacts, tokens, checkNegation)) {
        matched.push(point);
        continue;
      }
      const weak = (aliases.weak && aliases.weak[point]) || [];
      if (matchesAny(point, weak, compacts, tokens, checkNegation)) {
        uncertain.push(point);
      } else {
        missing.push(point);
      }
    }

    const total = matched.length + missing.length + uncertain.length;
    return {
      matched,
      missing,
      uncertain,
      coverage: total ? Math.round((matched.length / total) * 100) : 0,
    };
  }

  // ---------- 题库 ----------

  async function loadJson(path) {
    const response = await nativeFetch(path);
    if (!response.ok) {
      throw new Error(`加载 ${path} 失败：${response.status}`);
    }
    return response.json();
  }

  async function seedQuestions() {
    if ((await dbCount("questions")) > 0) return;
    const questions = await loadJson("data/questions.json");
    const db = await openDb();
    const tx = db.transaction("questions", "readwrite");
    const store = tx.objectStore("questions");
    for (const question of questions) store.put(question);
    await new Promise((resolve, reject) => {
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }

  const USER_DATA_VERSION = "clean-2026-10-18";

  async function resetUserDataIfNeeded() {
    const current = await dbGet("meta", "user_data_version");
    if (current && current.value === USER_DATA_VERSION) return;

    const db = await openDb();
    const tx = db.transaction(
      ["records", "progress", "wrong", "favorites", "daily", "dailyItems", "meta"],
      "readwrite"
    );
    for (const storeName of [
      "records",
      "progress",
      "wrong",
      "favorites",
      "daily",
      "dailyItems",
    ]) {
      tx.objectStore(storeName).clear();
    }
    tx.objectStore("meta").put({
      key: "user_data_version",
      value: USER_DATA_VERSION,
    });
    tx.objectStore("meta").put({ key: "user_data_imported", value: true });
    await new Promise((resolve, reject) => {
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }

  async function init() {
    await openDb();
    await seedQuestions();
    await resetUserDataIfNeeded();
    [questionList, aliases] = await Promise.all([
      dbGetAll("questions"),
      loadJson("data/key_point_aliases.json"),
    ]);
    questionById = new Map(questionList.map((question) => [question.id, question]));
  }

  function ensureReady() {
    if (!readyPromise) {
      readyPromise = init().catch((error) => {
        console.error("本地数据初始化失败", error);
        throw error;
      });
    }
    return readyPromise;
  }

  function getQuestion(questionId) {
    return questionById.get(String(questionId));
  }

  async function masteryLevel(questionId) {
    const progress = await dbGet("progress", questionId);
    return progress ? progress.masteryLevel || 0 : 0;
  }

  // ---------- 答题 ----------

  async function previewAnswer(body) {
    const question = getQuestion(body.question_id);
    if (!question) throw new HttpError(404, "题目不存在");
    if (question.type === "choice") {
      throw new HttpError(400, "选择题不支持简答题预判");
    }
    const match = matchKeyPoints(question.key_points || [], body.user_answer);
    return {
      display_user_answer: escapeHtml(body.user_answer),
      correct_answer: question.answer,
      explanation: question.explanation,
      matched_points: match.matched,
      missing_points: match.missing,
      uncertain_points: match.uncertain,
      coverage: match.coverage,
      requires_self_rating: true,
    };
  }

  async function gradeAnswer(body) {
    const question = getQuestion(body.question_id);
    if (!question) throw new HttpError(404, "题目不存在");
    if (question.type !== "choice" && !body.self_rating) {
      throw new HttpError(400, "简答题提交前请选择掌握程度");
    }

    let daily = null;
    let dailyItem = null;
    if (body.daily_practice_id) {
      daily = await dbGet("daily", String(body.daily_practice_id));
      if (!daily) throw new HttpError(400, "题目不属于这次每日练习");
      dailyItem = await dbGet("dailyItems", `${daily.date}|${question.id}`);
      if (!dailyItem) throw new HttpError(400, "题目不属于这次每日练习");
      if (dailyItem.userAnswer !== null && dailyItem.userAnswer !== undefined) {
        return {
          is_correct: dailyItem.isCorrect,
          correct_answer: question.answer,
          explanation: question.explanation,
          display_user_answer: escapeHtml(dailyItem.userAnswer),
          self_rating: null,
        };
      }
    }

    const isCorrect =
      question.type === "choice"
        ? String(body.user_answer).trim().toUpperCase() ===
          String(question.answer).trim().toUpperCase()
        : body.self_rating === "mastered";
    const answeredAt = localIso();

    await dbAdd("records", {
      questionId: question.id,
      userAnswer: body.user_answer,
      isCorrect,
      createdAt: answeredAt,
    });

    if (!isCorrect) {
      const wrong = await dbGet("wrong", question.id);
      await dbPut("wrong", {
        questionId: question.id,
        wrongCount: (wrong ? wrong.wrongCount : 0) + 1,
        lastWrongAt: answeredAt,
      });
    }

    let progress = await dbGet("progress", question.id);
    if (!progress) {
      progress = {
        questionId: question.id,
        attemptCount: 0,
        correctCount: 0,
        consecutiveCorrect: 0,
        masteryLevel: 0,
        lastAnsweredAt: null,
        nextReviewAt: null,
      };
    }
    progress.attemptCount += 1;
    progress.lastAnsweredAt = answeredAt;

    if (isCorrect) {
      progress.correctCount += 1;
      progress.consecutiveCorrect += 1;
      if (progress.consecutiveCorrect >= 3) progress.masteryLevel = 3;
      else if (progress.consecutiveCorrect >= 1) progress.masteryLevel = 2;
      const intervals = [0, 1, 3, 7, 14];
      const index = Math.min(progress.consecutiveCorrect, intervals.length - 1);
      progress.nextReviewAt = addDaysIso(intervals[index]);
    } else {
      progress.consecutiveCorrect = 0;
      progress.masteryLevel = 1;
      progress.nextReviewAt =
        question.type !== "choice" && body.self_rating === "fuzzy"
          ? addDaysIso(1)
          : answeredAt;
    }
    await dbPut("progress", progress);

    if (daily && dailyItem) {
      dailyItem.userAnswer = body.user_answer;
      dailyItem.isCorrect = isCorrect;
      dailyItem.answeredAt = answeredAt;
      await dbPut("dailyItems", dailyItem);

      const items = await dbGetByIndex("dailyItems", "date", daily.date);
      const answered = items.filter(
        (item) => item.userAnswer !== null && item.userAnswer !== undefined
      ).length;
      daily.correct = items.filter((item) => item.isCorrect === true).length;
      daily.isCompleted = daily.total > 0 && answered >= daily.total;
      daily.completedAt = daily.isCompleted ? answeredAt : null;
      await dbPut("daily", daily);
    }

    return {
      is_correct: isCorrect,
      correct_answer: question.answer,
      explanation: question.explanation,
      display_user_answer: escapeHtml(body.user_answer),
      self_rating: body.self_rating || null,
    };
  }

  // ---------- 题库 / 错题 / 收藏 / 统计 / 复习 ----------

  async function listQuestions(params) {
    let questions = questionList.slice();
    const module = params.get("module");
    const type = params.get("type");
    if (module) questions = questions.filter((q) => q.module === module);
    if (type) questions = questions.filter((q) => q.type === type);
    questions = shuffle(questions).slice(0, clampLimit(params.get("limit"), 10));

    return Promise.all(
      questions.map(async (question) => ({
        id: question.id,
        module: question.module,
        chapter: question.chapter,
        type: question.type,
        stem: question.stem,
        options: question.options,
        mastery_level: await masteryLevel(question.id),
      }))
    );
  }

  function clampLimit(value, fallback) {
    const parsed = Number.parseInt(value, 10);
    if (Number.isNaN(parsed)) return fallback;
    return Math.min(50, Math.max(1, parsed));
  }

  async function listWrongQuestions() {
    const rows = await dbGetAll("wrong");
    rows.sort((a, b) =>
      String(b.lastWrongAt || "").localeCompare(String(a.lastWrongAt || ""))
    );
    const result = [];
    for (const row of rows) {
      const question = getQuestion(row.questionId);
      if (!question) continue;
      result.push({
        wrong_id: row.questionId,
        wrong_count: row.wrongCount,
        question_id: question.id,
        module: question.module,
        type: question.type,
        stem: question.stem,
        answer: question.answer,
        explanation: question.explanation,
      });
    }
    return result;
  }

  async function removeWrongQuestion(questionId) {
    const existing = await dbGet("wrong", questionId);
    if (!existing) throw new HttpError(404, "错题不存在");
    await dbDelete("wrong", questionId);
    return { deleted: questionId };
  }

  async function listFavorites() {
    const rows = await dbGetAll("favorites");
    const result = [];
    for (const row of rows) {
      const question = getQuestion(row.questionId);
      if (!question) continue;
      result.push({
        question_id: question.id,
        module: question.module,
        stem: question.stem,
        answer: question.answer,
        explanation: question.explanation,
      });
    }
    return result;
  }

  async function addFavorite(questionId) {
    const existing = await dbGet("favorites", questionId);
    if (existing) throw new HttpError(400, "已经收藏过了");
    await dbPut("favorites", { questionId, createdAt: localIso() });
    return { favorited: questionId };
  }

  async function removeFavorite(questionId) {
    const existing = await dbGet("favorites", questionId);
    if (!existing) throw new HttpError(404, "没收藏过这道题");
    await dbDelete("favorites", questionId);
    return { deleted: questionId };
  }

  async function getStats() {
    const records = await dbGetAll("records");
    const byModule = new Map();
    let correct = 0;
    for (const record of records) {
      const question = getQuestion(record.questionId);
      if (!question) continue;
      const bucket =
        byModule.get(question.module) || { total: 0, correct: 0 };
      bucket.total += 1;
      if (record.isCorrect) {
        bucket.correct += 1;
        correct += 1;
      }
      byModule.set(question.module, bucket);
    }
    const total = records.length;
    const progress = await dbGetAll("progress");
    const mastery = { 薄弱: 0, 一般: 0, 熟练: 0 };
    for (const row of progress) {
      if (row.masteryLevel === 1) mastery.薄弱 += 1;
      else if (row.masteryLevel === 2) mastery.一般 += 1;
      else if (row.masteryLevel === 3) mastery.熟练 += 1;
    }
    return {
      total,
      correct,
      accuracy: total ? Math.round((correct / total) * 1000) / 10 : 0,
      by_module: Array.from(byModule.entries()).map(([module, value]) => ({
        module,
        total: value.total,
        correct: value.correct,
        accuracy: value.total
          ? Math.round((value.correct / value.total) * 1000) / 10
          : 0,
      })),
      mastery,
    };
  }

  async function getReviewQuestions() {
    const now = localIso();
    const progressRows = await dbGetAll("progress");
    const due = progressRows
      .filter(
        (row) =>
          row.nextReviewAt &&
          row.nextReviewAt <= now &&
          (row.masteryLevel || 0) < 3
      )
      .sort((a, b) => String(a.nextReviewAt).localeCompare(String(b.nextReviewAt)))
      .slice(0, 10);

    const questions = [];
    for (const row of due) {
      const question = getQuestion(row.questionId);
      if (!question) continue;
      questions.push({
        id: question.id,
        module: question.module,
        chapter: question.chapter,
        type: question.type,
        stem: question.stem,
        options: question.options,
        mastery_level: row.masteryLevel,
        next_review_at: formatDateTime(row.nextReviewAt),
      });
    }
    return questions;
  }

  // ---------- 每日一练 ----------

  async function allProgressMap() {
    const rows = await dbGetAll("progress");
    return new Map(rows.map((row) => [row.questionId, row]));
  }

  async function selectDailyQuestions(dateText, count = 5) {
    const progressMap = await allProgressMap();
    const now = localIso();
    const review = [];
    const weak = [];
    const fresh = [];

    for (const question of questionList) {
      const progress = progressMap.get(question.id);
      if (!progress) {
        fresh.push(question);
      } else if (
        progress.nextReviewAt &&
        progress.nextReviewAt <= now &&
        (progress.masteryLevel || 0) < 3
      ) {
        review.push(question);
      } else if ((progress.masteryLevel || 0) === 1) {
        weak.push(question);
      }
    }

    const random = seededRandom(dateText);
    const selected = [
      ...shuffle(review, random).slice(0, 2),
      ...shuffle(weak, random).slice(0, 2),
      ...shuffle(fresh, random).slice(0, 1),
    ];
    const selectedIds = new Set(selected.map((question) => question.id));
    const remaining = shuffle(
      questionList.filter((question) => !selectedIds.has(question.id)),
      random
    );
    for (const question of remaining) {
      if (selected.length >= count) break;
      selected.push(question);
    }
    return selected.slice(0, count);
  }

  async function ensureDailyItems(daily) {
    const items = await dbGetByIndex("dailyItems", "date", daily.date);
    if (items.length) {
      return items.sort((a, b) => a.position - b.position);
    }
    const created = [];
    for (let position = 0; position < daily.questionIds.length; position += 1) {
      const questionId = daily.questionIds[position];
      const item = {
        key: `${daily.date}|${questionId}`,
        date: daily.date,
        questionId,
        position,
        userAnswer: null,
        isCorrect: null,
        answeredAt: null,
      };
      await dbPut("dailyItems", item);
      created.push(item);
    }
    return created;
  }

  async function getOrCreateDaily() {
    const dateText = localDate();
    let daily = await dbGet("daily", dateText);
    if (daily) {
      await ensureDailyItems(daily);
      return daily;
    }

    const selected = await selectDailyQuestions(dateText);
    daily = {
      date: dateText,
      questionIds: selected.map((question) => question.id),
      total: selected.length,
      correct: 0,
      isCompleted: false,
      startedAt: localIso(),
      completedAt: null,
    };
    await dbPut("daily", daily);
    for (let position = 0; position < selected.length; position += 1) {
      await dbPut("dailyItems", {
        key: `${dateText}|${selected[position].id}`,
        date: dateText,
        questionId: selected[position].id,
        position,
        userAnswer: null,
        isCorrect: null,
        answeredAt: null,
      });
    }
    return daily;
  }

  async function dailyQuestionPayload(daily) {
    const items = await ensureDailyItems(daily);
    const result = [];
    for (const item of items) {
      const question = getQuestion(item.questionId);
      if (!question) continue;
      const progress = await dbGet("progress", question.id);
      const answered = item.userAnswer !== null && item.userAnswer !== undefined;
      result.push({
        id: question.id,
        module: question.module,
        chapter: question.chapter,
        type: question.type,
        stem: question.stem,
        options: question.options,
        mastery_level: progress ? progress.masteryLevel || 0 : 0,
        user_answer: item.userAnswer,
        display_user_answer: answered ? escapeHtml(item.userAnswer) : null,
        is_correct: item.isCorrect,
        correct_answer: answered ? question.answer : null,
        explanation: answered ? question.explanation : null,
      });
    }
    return result;
  }

  async function getDaily() {
    const daily = await getOrCreateDaily();
    const questions = await dailyQuestionPayload(daily);
    return {
      date: daily.date,
      practice_id: daily.date,
      count: questions.length,
      questions,
      correct: daily.correct,
      is_completed: daily.isCompleted,
    };
  }

  async function extendDaily() {
    const daily = await getOrCreateDaily();
    const items = await ensureDailyItems(daily);
    const existing = new Set(items.map((item) => item.questionId));
    const candidates = shuffle(
      questionList.filter((question) => !existing.has(question.id))
    ).slice(0, 5);
    if (!candidates.length) return { questions: [], count: 0 };

    const start = daily.questionIds.length;
    for (let index = 0; index < candidates.length; index += 1) {
      const question = candidates[index];
      daily.questionIds.push(question.id);
      await dbPut("dailyItems", {
        key: `${daily.date}|${question.id}`,
        date: daily.date,
        questionId: question.id,
        position: start + index,
        userAnswer: null,
        isCorrect: null,
        answeredAt: null,
      });
    }
    daily.total = daily.questionIds.length;
    daily.isCompleted = false;
    daily.completedAt = null;
    await dbPut("daily", daily);

    const payload = await dailyQuestionPayload(daily);
    const byId = new Map(payload.map((question) => [question.id, question]));
    return {
      questions: candidates.map((question) => byId.get(question.id)).filter(Boolean),
      count: candidates.length,
    };
  }

  async function dailyHistory(days = 30) {
    const all = (await dbGetAll("daily")).sort((a, b) =>
      String(b.date).localeCompare(String(a.date))
    );
    const today = localDate();
    const start = shiftDate(today, -(days - 1));
    const records = [];

    for (const daily of all) {
      if (daily.date < start || daily.date > today) continue;
      const items = await ensureDailyItems(daily);
      const answered = items.filter(
        (item) => item.userAnswer !== null && item.userAnswer !== undefined
      ).length;
      const correct = items.filter(
        (item) =>
          item.userAnswer !== null &&
          item.userAnswer !== undefined &&
          item.isCorrect === true
      ).length;
      records.push({
        date: daily.date,
        total: daily.total,
        answered,
        correct,
        accuracy: answered ? Math.round((correct / answered) * 100) : 0,
        completion_rate: daily.total
          ? Math.round((answered / daily.total) * 100)
          : 0,
        is_completed: daily.isCompleted,
      });
    }

    const completedDates = new Set(
      all.filter((daily) => daily.isCompleted).map((daily) => daily.date)
    );
    let cursor = completedDates.has(today) ? today : shiftDate(today, -1);
    let streak = 0;
    while (completedDates.has(cursor)) {
      streak += 1;
      cursor = shiftDate(cursor, -1);
    }
    return { streak, records };
  }

  async function dailyHistoryDetail(day) {
    const daily = await dbGet("daily", day);
    if (!daily) throw new HttpError(404, "没有这一天的练习记录");
    const items = await ensureDailyItems(daily);
    const questions = [];
    for (const item of items) {
      const question = getQuestion(item.questionId);
      if (!question) continue;
      const answered = item.userAnswer !== null && item.userAnswer !== undefined;
      questions.push({
        id: question.id,
        module: question.module,
        type: question.type,
        stem: question.stem,
        options: question.options,
        user_answer: item.userAnswer,
        display_user_answer: answered ? escapeHtml(item.userAnswer) : null,
        is_correct: item.isCorrect,
        correct_answer: answered ? question.answer : null,
        explanation: answered ? question.explanation : null,
      });
    }
    return { date: daily.date, questions };
  }

  // ---------- 路由 ----------

  async function handle(method, pathname, params, body) {
    if (method === "GET" && pathname === "/api/questions") {
      return listQuestions(params);
    }
    if (method === "POST" && pathname === "/api/answers/preview") {
      return previewAnswer(body);
    }
    if (method === "POST" && pathname === "/api/answers") {
      return gradeAnswer(body);
    }
    if (method === "GET" && pathname === "/api/wrong-questions") {
      return listWrongQuestions();
    }
    const wrongMatch = pathname.match(/^\/api\/wrong-questions\/(.+)$/);
    if (method === "DELETE" && wrongMatch) {
      return removeWrongQuestion(decodeURIComponent(wrongMatch[1]));
    }
    if (method === "GET" && pathname === "/api/favorites") {
      return listFavorites();
    }
    const favoriteMatch = pathname.match(/^\/api\/favorites\/(.+)$/);
    if (favoriteMatch && method === "POST") {
      return addFavorite(decodeURIComponent(favoriteMatch[1]));
    }
    if (favoriteMatch && method === "DELETE") {
      return removeFavorite(decodeURIComponent(favoriteMatch[1]));
    }
    if (method === "GET" && pathname === "/api/stats") {
      return getStats();
    }
    if (method === "GET" && pathname === "/api/review") {
      const questions = await getReviewQuestions();
      return { count: questions.length, questions };
    }
    if (method === "GET" && pathname === "/api/daily") {
      return getDaily();
    }
    if (method === "POST" && pathname === "/api/daily/extend") {
      return extendDaily();
    }
    if (method === "GET" && pathname === "/api/daily/history") {
      const days = Number.parseInt(params.get("days"), 10) || 30;
      return dailyHistory(Math.min(365, Math.max(1, days)));
    }
    const historyMatch = pathname.match(/^\/api\/daily\/history\/(.+)$/);
    if (method === "GET" && historyMatch) {
      return dailyHistoryDetail(decodeURIComponent(historyMatch[1]));
    }
    throw new HttpError(404, "接口不存在");
  }

  function jsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data), {
      status,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  }

  window.fetch = async function localFetch(input, init = {}) {
    const rawUrl = typeof input === "string" ? input : input.url;
    const url = new URL(rawUrl, window.location.href);
    if (!url.pathname.startsWith(API_PREFIX)) {
      return nativeFetch(input, init);
    }

    try {
      await ensureReady();
      let body = null;
      if (init.body) body = JSON.parse(init.body);
      const data = await handle(
        (init.method || "GET").toUpperCase(),
        url.pathname,
        url.searchParams,
        body
      );
      return jsonResponse(data);
    } catch (error) {
      if (error instanceof HttpError) {
        return jsonResponse({ detail: error.message }, error.status);
      }
      console.error("本地 API 请求失败", error);
      return jsonResponse({ detail: "本地数据处理失败" }, 500);
    }
  };

  // 测试和调试时可以拿到这两个内部函数
  window.__localApi = { matchKeyPoints, normalize, getQuestion };
})();
