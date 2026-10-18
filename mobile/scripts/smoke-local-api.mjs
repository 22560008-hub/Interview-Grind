import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import "fake-indexeddb/auto";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const dataDir = path.resolve(scriptDir, "../www/data");

function staticResponse(input) {
  const name = String(input).split("/").pop();
  if (name === "user_data.json") {
    return { ok: false, status: 404, json: async () => ({}) };
  }
  const text = fs.readFileSync(path.join(dataDir, name), "utf8");
  return { ok: true, status: 200, json: async () => JSON.parse(text) };
}

global.window = global;
global.window.location = { href: "https://localhost/" };
global.window.fetch = async (input) =>
  staticResponse(typeof input === "string" ? input : input.url);

await import(pathToFileURL(path.join(scriptDir, "../www/js/local-api.js")));

async function request(url, init = {}) {
  const response = await global.fetch(url, init);
  return { status: response.status, body: await response.json() };
}

async function post(url, body) {
  return request(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

const questions = await request("/api/questions?limit=3");
assert.equal(questions.status, 200);
assert.equal(questions.body.length, 3);
assert.ok(questions.body.every((question) => question.id));
console.log("questions ok", questions.body.map((question) => question.id));

const shortList = await request("/api/questions?type=short_answer&limit=1");
assert.equal(shortList.status, 200);
const shortQuestion = shortList.body[0];
assert.ok(shortQuestion);

const preview = await post("/api/answers/preview", {
  question_id: shortQuestion.id,
  user_answer: "序列号 确认应答",
});
assert.equal(preview.status, 200);
assert.ok(Array.isArray(preview.body.matched_points));
console.log("preview ok", preview.body.coverage);

const mastered = await post("/api/answers", {
  question_id: shortQuestion.id,
  user_answer: "序列号 确认应答",
  self_rating: "mastered",
});
assert.equal(mastered.status, 200);
assert.equal(mastered.body.is_correct, true);

const stats = await request("/api/stats");
assert.equal(stats.status, 200);
assert.equal(stats.body.total, 1);
assert.equal(stats.body.correct, 1);
console.log("stats ok", stats.body);

const favorites = await post(`/api/favorites/${shortQuestion.id}`, {});
assert.equal(favorites.status, 200);
const favoriteList = await request("/api/favorites");
assert.equal(favoriteList.body.length, 1);

const daily = await request("/api/daily");
assert.equal(daily.status, 200);
assert.equal(daily.body.questions.length, 5);
assert.ok(daily.body.practice_id);
console.log("daily ok", daily.body.practice_id, daily.body.count);

const history = await request("/api/daily/history?days=7");
assert.equal(history.status, 200);
assert.ok(Array.isArray(history.body.records));

const choiceList = await request("/api/questions?type=choice&limit=1");
const choiceQuestion = choiceList.body[0];
const wrong = await post("/api/answers", {
  question_id: choiceQuestion.id,
  user_answer: "Z",
});
assert.equal(wrong.status, 200);
assert.equal(wrong.body.is_correct, false);

const wrongList = await request("/api/wrong-questions");
assert.equal(wrongList.status, 200);
assert.equal(wrongList.body.length, 1);
const review = await request("/api/review");
assert.equal(review.status, 200);
assert.ok(review.body.count >= 1);
console.log("wrong/review ok", wrongList.body.length, review.body.count);

const matcher = global.window.__localApi;
assert.ok(matcher);
const match = matcher.matchKeyPoints(["序列号"], "用序号标识字节");
assert.deepEqual(match.matched, ["序列号"]);
const numeric = matcher.matchKeyPoints(["三次握手"], "3 次握手");
assert.deepEqual(numeric.matched, ["三次握手"]);
const negated = matcher.matchKeyPoints(["三次握手"], "不需要三次握手");
assert.deepEqual(negated.missing, ["三次握手"]);
console.log("matcher ok");

console.log("ALL LOCAL API SMOKE TESTS PASSED");
