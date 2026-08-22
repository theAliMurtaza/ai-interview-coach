import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Mic, MicOff, Keyboard, SkipForward, CheckCircle2, AlertTriangle } from "lucide-react";
import Waveform from "../components/Waveform";
import AgentAvatar from "../components/AgentAvatar";
import { useInterview } from "../context/InterviewContext";
import { buildQuestionSet, DEFAULT_QUESTIONS } from "../data/questionBank";
import {
  startListening,
  speak,
  cancelSpeaking,
  isSpeechRecognitionSupported,
  isSpeechSynthesisSupported,
} from "../services/speechService";
import { evaluateAnswer, summarizeSession } from "../services/evaluationService";
import { saveSession } from "../services/storageService";

const GENERIC_FOLLOW_UP =
  "Can you go a bit deeper, or walk me through a concrete example?";

export default function Interview() {
  const navigate = useNavigate();
  const { setup, setLastSession } = useInterview();

  const voiceSupported = isSpeechRecognitionSupported();

  const [questions] = useState(() =>
    setup.role
      ? buildQuestionSet({
          role: setup.role,
          type: setup.type,
          difficulty: setup.difficulty,
          count: setup.questionCount || DEFAULT_QUESTIONS,
        })
      : []
  );

  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState("intro"); // intro | agent-speaking | listening | processing | finished
  const [liveTranscript, setLiveTranscript] = useState("");
  const [answers, setAnswers] = useState([]);
  const [followUpUsed, setFollowUpUsed] = useState({});
  const [micError, setMicError] = useState(null);
  // manualMode = the user is typing rather than speaking, either because
  // they chose "Type my answers" at setup, the browser can't do speech
  // recognition, or they toggled mid-session.
  const [manualMode, setManualMode] = useState(
    setup.inputMode === "text" || !voiceSupported
  );

  const recognitionRef = useRef(null);
  const listenStartRef = useRef(null);
  const accumulatedTranscriptRef = useRef(""); // carries text across a follow-up on the same question
  const manualInputRef = useRef(null);

  const speechOk = isSpeechSynthesisSupported();
  const current = questions[index];

  const cleanupRecognition = useCallback(() => {
    recognitionRef.current?.stop?.();
    recognitionRef.current = null;
  }, []);

  useEffect(() => {
    if (!setup.role) {
      navigate("/setup");
      return;
    }
    // Greet, then ask the first question.
    const run = async () => {
      setPhase("agent-speaking");
      const greeting = `Let's get started. I'll ask you ${questions.length} questions for the ${setup.roleLabel} track. Take your time with each answer.`;
      if (speechOk) {
        try {
          await speak(greeting, { rate: 1 });
        } catch {
          /* speech synthesis can fail silently in some browsers — continue anyway */
        }
      }
      askQuestion(questions[0]?.text);
    };
    run();
    return () => {
      cancelSpeaking();
      cleanupRecognition();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function askQuestion(text) {
    if (!text) return;
    setPhase("agent-speaking");
    setLiveTranscript("");
    if (speechOk) {
      try {
        await speak(text, { rate: 1 });
      } catch {
        /* ignore */
      }
    }
    beginListening();
  }

  function beginListening() {
    setMicError(null);
    setPhase("listening");
    listenStartRef.current = Date.now();

    if (manualMode) return; // typed-answer mode, no recognition to start

    const controller = startListening({
      onResult: (text) => setLiveTranscript(text),
      onError: () => {
        setMicError(
          "Microphone access wasn't available — you can type your answer instead."
        );
        setManualMode(true);
      },
    });
    recognitionRef.current = controller;
  }

  function switchInputMode(mode) {
    if (mode === "voice" && !voiceSupported) return;
    cleanupRecognition();
    setManualMode(mode === "text");
    // if we're mid-answer, restart listening in the new mode for this question
    if (phase === "listening") {
      listenStartRef.current = Date.now();
      if (mode === "voice") {
        setMicError(null);
        const controller = startListening({
          onResult: (text) => setLiveTranscript(text),
          onError: () => {
            setMicError("Microphone access wasn't available — you can type your answer instead.");
            setManualMode(true);
          },
        });
        recognitionRef.current = controller;
      }
    }
  }

  async function handleDoneAnswering() {
    cleanupRecognition();
    const durationSeconds = Math.max(1, (Date.now() - listenStartRef.current) / 1000);
    const fullTranscript = `${accumulatedTranscriptRef.current} ${liveTranscript}`.trim();
    const evaluation = evaluateAnswer(fullTranscript, durationSeconds, current.expectedConcepts || []);

    const questionKey = current.instanceId || current.id;
    const alreadyFollowedUp = followUpUsed[questionKey];
    const shouldFollowUp =
      !alreadyFollowedUp && evaluation.overallScore < 55 && fullTranscript.split(/\s+/).length > 3;

    if (shouldFollowUp) {
      setPhase("processing");
      setFollowUpUsed((prev) => ({ ...prev, [questionKey]: true }));
      accumulatedTranscriptRef.current = fullTranscript;
      const followUpText = current.followUpHint
        ? `Thanks — ${GENERIC_FOLLOW_UP}`
        : GENERIC_FOLLOW_UP;
      setPhase("agent-speaking");
      if (speechOk) {
        try {
          await speak(followUpText);
        } catch {
          /* ignore */
        }
      }
      beginListening();
      return;
    }

    accumulatedTranscriptRef.current = "";
    const updated = [...answers, { question: current.text, transcript: fullTranscript, evaluation }];
    setAnswers(updated);

    const nextIndex = index + 1;
    if (nextIndex < questions.length) {
      setIndex(nextIndex);
      askQuestion(questions[nextIndex].text);
    } else {
      finishSession(updated);
    }
  }

  async function finishSession(finalAnswers) {
    setPhase("processing");
    if (speechOk) {
      try {
        await speak("That's the full set of questions. Let's look at how you did.");
      } catch {
        /* ignore */
      }
    }
    const summary = summarizeSession(finalAnswers.map((a) => a.evaluation));
    const session = {
      id: `s_${Date.now()}`,
      completedAt: new Date().toISOString(),
      roleLabel: setup.roleLabel,
      typeLabel: setup.typeLabel,
      difficultyLabel: setup.difficultyLabel,
      answers: finalAnswers,
      summary,
    };
    saveSession(session);
    setLastSession(session);
    setPhase("finished");
    navigate(`/results/${session.id}`);
  }

  function handleSkip() {
    cleanupRecognition();
    accumulatedTranscriptRef.current = "";
    const evaluation = evaluateAnswer("", 1, current.expectedConcepts || []);
    const updated = [...answers, { question: current.text, transcript: "(skipped)", evaluation }];
    setAnswers(updated);
    const nextIndex = index + 1;
    if (nextIndex < questions.length) {
      setIndex(nextIndex);
      askQuestion(questions[nextIndex].text);
    } else {
      finishSession(updated);
    }
  }

  function handleManualSubmit(e) {
    e.preventDefault();
    const text = manualInputRef.current?.value?.trim() || "";
    setLiveTranscript(text);
    if (manualInputRef.current) manualInputRef.current.value = "";
    // small timeout so state settles before evaluating
    setTimeout(() => handleDoneAnswering(), 0);
  }

  if (!current) return null;

  const agentState =
    phase === "agent-speaking"
      ? "speaking"
      : phase === "listening"
      ? "listening"
      : phase === "processing"
      ? "thinking"
      : "idle";

  return (
    <div className="mx-auto max-w-3xl px-6 py-12">
      {/* Progress — a real ordered sequence, so numbering is meaningful here */}
      <div className="mb-8 flex items-center gap-3">
        <span className="font-[var(--font-mono)] text-xs text-[var(--text-muted)]">
          Question {index + 1} / {questions.length}
        </span>
        <div className="h-1 flex-1 overflow-hidden rounded-full bg-[var(--surface-raised)]">
          <div
            className="h-full rounded-full bg-[var(--teal)] transition-all duration-500"
            style={{ width: `${((index + (phase === "finished" ? 1 : 0)) / questions.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Question card */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
        <div className="mb-1 font-[var(--font-mono)] text-xs uppercase tracking-wider text-[var(--text-muted)]">
          {setup.roleLabel} · {setup.typeLabel}
        </div>
        <h2 className="text-xl font-medium leading-snug">{current.text}</h2>

        {/* Agent panel: avatar + live signal */}
        <div className="mt-6 flex items-center gap-5 rounded-lg border border-[var(--border-soft)] bg-[var(--surface-raised)] px-4 py-6">
          <AgentAvatar state={agentState} />
          <div className="flex-1">
            <Waveform
              mode={
                phase === "agent-speaking" ? "speaking" : phase === "listening" ? "listening" : "idle"
              }
              height={48}
              barCount={30}
              className="w-full justify-between"
            />
            <p className="mt-3 text-sm text-[var(--text-muted)]">
              {phase === "agent-speaking" && "Agent is speaking…"}
              {phase === "listening" && (manualMode ? "Type your answer below" : "Listening — speak your answer")}
              {phase === "processing" && "Reviewing your answer…"}
              {phase === "intro" && "Getting ready…"}
            </p>
          </div>
        </div>

        {micError && (
          <div className="mt-4 flex items-start gap-2 rounded-md border border-[var(--red-dim)] bg-[var(--red-dim)]/20 p-3 text-sm text-[var(--text-secondary)]">
            <AlertTriangle size={16} className="mt-0.5 shrink-0 text-[var(--red)]" />
            {micError}
          </div>
        )}

        {/* Live transcript */}
        {!manualMode && (
          <div className="mt-4 min-h-[3rem] rounded-md border border-[var(--border-soft)] bg-[var(--bg)] p-3 font-[var(--font-mono)] text-sm text-[var(--text-secondary)]">
            {liveTranscript || (phase === "listening" ? "…" : "Your transcript will appear here.")}
          </div>
        )}

        {/* Manual fallback input */}
        {manualMode && phase === "listening" && (
          <form onSubmit={handleManualSubmit} className="mt-4">
            <textarea
              ref={manualInputRef}
              rows={4}
              autoFocus
              placeholder="Type your answer, then submit."
              className="w-full rounded-md border border-[var(--border-soft)] bg-[var(--bg)] p-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none"
            />
            <button
              type="submit"
              className="mt-2 rounded-md bg-[var(--teal)] px-4 py-2 text-sm font-medium text-[#06231d]"
            >
              Submit answer
            </button>
          </form>
        )}

        {/* Controls */}
        <div className="mt-6 flex flex-wrap items-center gap-3">
          {phase === "listening" && !manualMode && (
            <button
              onClick={handleDoneAnswering}
              className="inline-flex items-center gap-2 rounded-md bg-[var(--amber)] px-4 py-2.5 text-sm font-medium text-[#1a1305]"
            >
              <CheckCircle2 size={16} />
              I'm done answering
            </button>
          )}

          {/* voice/text switch, available any time voice is supported */}
          {voiceSupported && (
            <button
              onClick={() => switchInputMode(manualMode ? "voice" : "text")}
              className="inline-flex items-center gap-1.5 rounded-md border border-[var(--border)] px-3 py-2 text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              title={manualMode ? "Switch to speaking" : "Switch to typing"}
            >
              {manualMode ? <Mic size={14} /> : <Keyboard size={14} />}
              {manualMode ? "Switch to voice" : "Switch to typing"}
            </button>
          )}

          {phase === "listening" && (
            <span className="inline-flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
              {manualMode ? <MicOff size={14} /> : <Mic size={14} className="text-[var(--red)]" />}
              {manualMode ? "Typing mode" : "Mic live"}
            </span>
          )}
          <button
            onClick={handleSkip}
            disabled={phase === "agent-speaking" || phase === "processing"}
            className="ml-auto inline-flex items-center gap-2 rounded-md border border-[var(--border)] px-4 py-2.5 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] disabled:opacity-40"
          >
            Skip question <SkipForward size={14} />
          </button>
        </div>
      </div>

      <p className="mt-4 text-center text-xs text-[var(--text-muted)]">
        Runs entirely in your browser. Nothing is uploaded anywhere.
      </p>
    </div>
  );
}
