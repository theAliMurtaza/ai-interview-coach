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
 * @param {() => void} handlers.onEnd
 * @param {(err: any) => void} handlers.onError
 * @returns {{ stop: () => void } | null}
 */
export function startListening({ onResult, onStart, onEnd, onError }) {
  if (!SpeechRecognitionAPI) {
    onError?.(new Error("SpeechRecognition is not supported in this browser."));
    return null;
  }

  const recognition = new SpeechRecognitionAPI();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = "en-US";

  let finalTranscript = "";

  recognition.onstart = () => onStart?.();

  recognition.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const chunk = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += chunk + " ";
        onResult?.(finalTranscript.trim(), true);
      } else {
        interim += chunk;
        onResult?.((finalTranscript + interim).trim(), false);
      }
    }
  };

  recognition.onerror = (event) => onError?.(event);
  recognition.onend = () => onEnd?.();

  recognition.start();

  return {
    stop: () => recognition.stop(),
    abort: () => recognition.abort(),
  };
}

/**
 * Speaks text aloud and resolves when speech finishes.
 * @param {string} text
 * @param {{ rate?: number, pitch?: number, voiceName?: string }} [opts]
 */
export function speak(text, opts = {}) {
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

    utterance.onend = () => resolve();
    utterance.onerror = (e) => reject(e);

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  });
}

export function cancelSpeaking() {
  if (isSpeechSynthesisSupported()) window.speechSynthesis.cancel();
}

export function getVoices() {
  if (!isSpeechSynthesisSupported()) return [];
  return window.speechSynthesis.getVoices();
}
