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

test("a synchronous microphone failure reaches the typed fallback", () => {
  failStart = true;
  let error;
  startListening({ onError: value => { error = value; } });
  assert.match(error.message, /Mic unavailable/);
  failStart = false;
});

test("canceling speech settles its promise even without a browser event", async () => {
  const result = assert.rejects(speak("Example question"), /canceled/);
  cancelSpeaking();
  await result;
});
