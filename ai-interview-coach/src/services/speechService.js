// speechService.js
//
// Wraps the browser's native Web Speech API (SpeechRecognition +
// SpeechSynthesis) so the rest of the app never talks to `window`
// directly. This keeps the swap to a real backend (Whisper for STT,
// ElevenLabs/OpenAI for TTS) to a single file — see README.

const SpeechRecognitionAPI =
  typeof window !== "undefined"
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null;

export const isSpeechRecognitionSupported = () => Boolean(SpeechRecognitionAPI);
export const isSpeechSynthesisSupported = () =>
  typeof window !== "undefined" && "speechSynthesis" in window;

/**
 * Starts continuous speech recognition.
 * @param {Object} handlers
 * @param {(text: string, isFinal: boolean) => void} handlers.onResult
 * @param {() => void} handlers.onStart
 * @param {(err: any) => void} handlers.onError
 * @param {(state: string) => void} handlers.onState
 * @returns {{ stop: () => void } | null}
 */
export function startListening({ onResult, onStart, onError, onState }) {
  if (!SpeechRecognitionAPI) {
    onError?.(new Error("SpeechRecognition is not supported in this browser."));
    return null;
  }

  let recognition;
  let stopped = false;
  let timer;
  let completed = "";
  let emptyRestarts = 0;

  function detach(instance) {
    instance.onresult = instance.onerror = instance.onend = instance.onstart = null;
  }

  function fail(error) {
    stop();
    onState?.("paused");
    onError?.(error);
  }

  function begin() {
    if (stopped) return;
    const instance = new SpeechRecognitionAPI();
    recognition = instance;
    instance.continuous = true;
    instance.interimResults = true;
    instance.lang = "en-US";
    let cycleText = "";
    let lastError;
    const active = () => !stopped && recognition === instance;
    onState?.("starting");
    instance.onstart = () => { if (active()) { onState?.("listening"); onStart?.(); } };
    instance.onresult = event => {
      if (!active()) return;
      // Results are cumulative within a recognition session. Rebuild rather than
      // appending revised interim/final results and duplicating earlier words.
      cycleText = Array.from(event.results, result => result[0].transcript.trim()).join(" ").trim();
      if (cycleText) emptyRestarts = 0;
      onResult?.([completed, cycleText].filter(Boolean).join(" "), Array.from(event.results).every(result => result.isFinal));
    };
    instance.onerror = event => {
      if (!active()) return;
      lastError = event;
      if (!["no-speech", "network", "aborted"].includes(event.error)) fail(event);
      // Recoverable errors are followed by onend; restart only after disconnection.
    };
    instance.onend = () => {
      if (!active()) return;
      detach(instance);
      recognition = null;
      completed = [completed, cycleText].filter(Boolean).join(" ");
      emptyRestarts = cycleText ? 0 : emptyRestarts + 1;
      if (emptyRestarts > 5) { fail(lastError || new Error("Speech recognition keeps disconnecting.")); return; }
      onState?.("reconnecting");
      timer = setTimeout(begin, Math.min(250 * 2 ** emptyRestarts, 4000));
    };
    try { instance.start(); } catch (error) { fail(error); }
  }

  function stop() {
    stopped = true;
    clearTimeout(timer);
    if (recognition) {
      detach(recognition);
      try { recognition.abort(); } catch { /* already stopped */ }
      recognition = null;
    }
  }

  begin();
  return {
    stop,
    abort: stop,
  };
}

/**
 * Speaks text aloud and resolves when speech finishes.
 * @param {string} text
 * @param {{ rate?: number, pitch?: number, voiceName?: string }} [opts]
 */
let pendingSpeech = null;

export function speak(text, opts = {}) {
  cancelSpeaking();
  return new Promise((resolve, reject) => {
    if (!isSpeechSynthesisSupported()) {
      reject(new Error("SpeechSynthesis is not supported in this browser."));
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = opts.rate ?? 1;
    utterance.pitch = opts.pitch ?? 1;

    if (opts.voiceName) {
      const voice = window.speechSynthesis
        .getVoices()
        .find((v) => v.name === opts.voiceName);
      if (voice) utterance.voice = voice;
    }

    let timer;
    const finish = (error) => {
      if (pendingSpeech !== finish) return;
      pendingSpeech = null;
      clearTimeout(timer);
      utterance.onend = null;
      utterance.onerror = null;
      if (error) reject(error); else resolve();
    };
    pendingSpeech = finish;
    utterance.onend = () => finish();
    utterance.onerror = (e) => finish(e);
    // Some browsers never dispatch completion when autoplay or speech fails.
    timer = setTimeout(() => {
      finish(new Error("Speech playback timed out"));
      window.speechSynthesis.cancel();
    }, Math.max(15000, text.length * 100));

    try { window.speechSynthesis.speak(utterance); } catch (error) { finish(error); }
  });
}

export function cancelSpeaking() {
  pendingSpeech?.(new Error("Speech playback canceled"));
  if (isSpeechSynthesisSupported()) window.speechSynthesis.cancel();
}

export function getVoices() {
  if (!isSpeechSynthesisSupported()) return [];
  return window.speechSynthesis.getVoices();
}
