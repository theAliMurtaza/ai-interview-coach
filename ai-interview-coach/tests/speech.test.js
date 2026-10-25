import test from "node:test";
import assert from "node:assert/strict";

let recognition;
let failStart = false;
globalThis.window = {
  SpeechRecognition: class {
    constructor() { recognition = this; }
    start() { if (failStart) throw new Error("Mic unavailable"); }
    abort() { this.aborted = true; }
  },
  speechSynthesis: { cancel() {}, speak() {}, getVoices: () => [] },
};
globalThis.SpeechSynthesisUtterance = class { constructor(text) { this.text = text; } };
const { startListening, speak, cancelSpeaking } = await import("../src/services/speechService.js");

test("stopping recognition detaches late events without changing input mode", () => {
  let ended = false;
  const controller = startListening({ onEnd: () => { ended = true; } });
  const lateEnd = recognition.onend;
  controller.stop();
  lateEnd();
  assert.equal(ended, false);
  assert.equal(recognition.onresult, null);
  assert.equal(recognition.aborted, true);
});

test("a synchronous microphone failure reports a paused microphone", () => {
  failStart = true;
  let error;
  startListening({ onError: value => { error = value; } });
  assert.match(error.message, /Mic unavailable/);
  failStart = false;
});

function resultEvent(chunks) {
  return { resultIndex: 0, results: chunks.map(([transcript, isFinal]) =>
    Object.assign([{ transcript }], { isFinal })) };
}

test("browser session endings restart voice and preserve final and interim text", t => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const results = [], states = [];
  const controller = startListening({ onResult: text => results.push(text), onState: state => states.push(state) });
  const first = recognition;
  first.onresult(resultEvent([["I built an API", true], ["with Python", false]]));
  first.onresult(resultEvent([["I built an API", true], ["with Python", true]]));
  first.onend();
  assert.equal(states.at(-1), "reconnecting");
  t.mock.timers.tick(250);
  assert.notEqual(recognition, first);
  recognition.onresult(resultEvent([["and tested it", false]]));
  assert.equal(results.at(-1), "I built an API with Python and tested it");
  recognition.onend();
  t.mock.timers.tick(250);
  recognition.onresult(resultEvent([["using pytest", true]]));
  assert.equal(results.at(-1), "I built an API with Python and tested it using pytest");
  controller.stop();
});

test("stopping during reconnection cancels the timer and ignores late results", t => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  const controller = startListening({ onResult: () => assert.fail("late result") });
  const first = recognition, lateResult = recognition.onresult;
  recognition.onend();
  controller.stop();
  lateResult(resultEvent([["late text", true]]));
  t.mock.timers.tick(10000);
  assert.equal(recognition, first);
});

test("silence and network errors reconnect but permission denial pauses", t => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let failure;
  const controller = startListening({ onError: err => { failure = err; } });
  for (const error of ["no-speech", "network"]) {
    const before = recognition;
    recognition.onerror({ error }); recognition.onend();
    t.mock.timers.tick(4000);
    assert.notEqual(recognition, before);
    assert.equal(failure, undefined);
  }
  const last = recognition;
  recognition.onerror({ error: "not-allowed" });
  t.mock.timers.tick(10000);
  assert.equal(recognition, last);
  assert.equal(failure.error, "not-allowed");
  controller.stop();
});

test("repeated empty disconnects stop retrying without losing the controller", t => {
  t.mock.timers.enable({ apis: ["setTimeout"] });
  let failure;
  const controller = startListening({ onError: err => { failure = err; } });
  for (let i = 0; i < 6; i++) { recognition.onend(); t.mock.timers.tick(4000); }
  assert.match(failure.message, /keeps disconnecting/);
  controller.stop();
});

test("canceling speech settles its promise even without a browser event", async () => {
  const result = assert.rejects(speak("Example question"), /canceled/);
  cancelSpeaking();
  await result;
});
