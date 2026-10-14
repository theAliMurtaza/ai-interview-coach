import test from "node:test";
import assert from "node:assert/strict";
import { evaluateAnswer, summarizeSession } from "../src/services/evaluationService.js";
import { getAllSessions, saveSession, getSessionById, clearAllSessions } from "../src/services/storageService.js";
import { buildQuestionSet } from "../src/data/questionBank.js";

test("empty and skipped answers receive no points", () => {
  const evaluation = evaluateAnswer("   ", 30, ["react"]);
  assert.equal(evaluation.overallScore, 0);
  assert.equal(evaluation.communicationScore, 0);
});

test("punctuated fillers and invalid timing produce finite metrics", () => {
  const evaluation = evaluateAnswer("right? um unlike", NaN, []);
  assert.equal(evaluation.fillerCount, 2);
  assert.ok(Number.isFinite(evaluation.wpm));
});

test("concepts are matched as terms instead of substrings in unrelated words", () => {
  assert.deepEqual(evaluateAnswer("My reaction followed principles", 5, ["react", "ci"]).conceptsHit, []);
  assert.deepEqual(evaluateAnswer("React with CI and C++", 5, ["react", "ci", "c++"]).conceptsHit, ["react", "ci", "c++"]);
});

test("technical questions start at the selected difficulty and counts are bounded", () => {
  const questions = buildQuestionSet({ role: "frontend", type: "technical", difficulty: "junior", count: NaN });
  assert.equal(questions.length, 6);
  assert.match(questions[0].id, /-j-/);
});

test("question batches have unique instance IDs and no adjacent repeats", () => {
  const questions = buildQuestionSet({ role: "frontend", type: "technical", difficulty: "junior", count: 40 });
  assert.equal(questions.length, 40);
  assert.equal(new Set(questions.map(q => q.instanceId)).size, 40);
  for (let i = 1; i < questions.length; i++) assert.notEqual(questions[i].id, questions[i - 1].id);
});

test("corrupt storage and quota errors do not lose the current report", () => {
  let raw = '{"not":"an array"}';
  globalThis.localStorage = {
    getItem: () => raw,
    setItem: () => { throw new Error("Quota exceeded"); },
    removeItem: () => { raw = null; },
  };
  assert.deepEqual(getAllSessions(), []);
  raw = '[null, {}, {"id":"broken","summary":{}}]';
  assert.deepEqual(getAllSessions(), []);
  const evaluation = evaluateAnswer("react", 5, ["react"]);
  const session = { id: "test", completedAt: new Date().toISOString(), roleLabel: "Frontend", typeLabel: "Technical", difficultyLabel: "Junior", answers: [{question: "Explain React", transcript: "react", evaluation}], summary: summarizeSession([evaluation]) };
  assert.equal(saveSession(session).persisted, false);
  assert.equal(getSessionById("test"), session);
  assert.equal(clearAllSessions(), true);
  assert.deepEqual(getAllSessions(), []);
});
