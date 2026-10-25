import test from "node:test";
import assert from "node:assert/strict";
import { beginActivity, getPendingActivity, subscribeToActivity } from "../src/services/activityService.js";

test("overlapping operations remain busy until both finish; cleanup is idempotent", () => {
  const states = [];
  const unsubscribe = subscribeToActivity(() => states.push(getPendingActivity()));
  const first = beginActivity(), second = beginActivity();
  first(); first();
  assert.equal(getPendingActivity(), 1);
  second();
  assert.equal(getPendingActivity(), 0);
  assert.deepEqual(states, [1, 2, 1, 0]);
  unsubscribe();
  beginActivity()();
  assert.deepEqual(states, [1, 2, 1, 0]);
});
