import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Mic, Keyboard, SkipForward, CheckCircle2 } from "lucide-react";
import Waveform from "../components/Waveform";
import AgentAvatar from "../components/AgentAvatar";
import { useInterview } from "../context/InterviewContext";
import { startListening, speak, cancelSpeaking, isSpeechRecognitionSupported, isSpeechSynthesisSupported } from "../services/speechService";
import { getInterview, submitAnswer, completeInterview, toSession } from "../services/interviewService";

export default function Interview() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { setup } = useInterview();
  const [interview, setInterview] = useState(null);
  const [phase, setPhase] = useState("loading");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [text, setText] = useState("");
  const [retry, setRetry] = useState(0);
  const voiceSupported = isSpeechRecognitionSupported();
  const [typing, setTyping] = useState(setup.inputMode === "text" || !voiceSupported);
  const typingRef = useRef(typing);
  const transcript = useRef("");
  const recognition = useRef(null);
  const started = useRef(0);
  const busy = useRef(true);
  const lifecycle = useRef(0);
  const current = interview?.questions.find(q => !q.answer);

  function updateText(value) { transcript.current = value.slice(0, 20000); setText(transcript.current); }
  function stopRecognition() { recognition.current?.stop(); recognition.current = null; }
  function fallback() {
    typingRef.current = true; setTyping(true);
    setNotice("Voice input stopped. You can continue typing your answer.");
  }
  function listen() {
    if (typingRef.current) return;
    const prefix = transcript.current;
    recognition.current = startListening({
      onResult: value => updateText(`${prefix} ${value}`.trim()), onError: fallback, onEnd: fallback,
    });
  }

  useEffect(() => {
    const generation = ++lifecycle.current;
    setPhase("loading"); setError("");
    getInterview(id).then(data => {
      if (generation !== lifecycle.current) return;
      if (data.status === "completed") navigate(`/results/${id}`, { replace: true });
      else { setInterview(data); setPhase("ready"); }
    }).catch(err => {
      if (generation === lifecycle.current) { setError(err.message); setPhase("error"); }
    });
    return () => { lifecycle.current++; stopRecognition(); cancelSpeaking(); };
  }, [id, retry, navigate]);

  useEffect(() => {
    if (!current) return;
    let canceled = false;
    busy.current = true;
    updateText(""); setNotice(""); setPhase("speaking");
    (async () => {
      if (isSpeechSynthesisSupported()) {
        try { await speak(current.text); } catch { /* readable question remains available */ }
      }
      if (canceled) return;
      started.current = Date.now(); busy.current = false;
      setPhase("listening"); listen();
    })();
    return () => { canceled = true; busy.current = true; stopRecognition(); cancelSpeaking(); };
    // Only a new question should restart speech or clear a draft answer.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id]);

  async function advance(data, generation) {
    if (generation !== lifecycle.current) return;
    setInterview(data);
    if (data.status === "completed") { navigate(`/results/${id}`, { replace: true }); return; }
    if (data.questions.every(q => q.answer)) {
      await completeInterview(id);
      if (generation === lifecycle.current) navigate(`/results/${id}`, { replace: true });
    }
  }

  async function submit(skipped = false) {
    if (busy.current || phase !== "listening" || !current) return;
    busy.current = true; setPhase("processing"); setError(""); stopRecognition();
    const generation = lifecycle.current;
    const answerText = skipped ? "" : transcript.current;
    const duration = skipped ? 1 : Math.max(1, (Date.now() - started.current) / 1000);
    try {
      // A previous response may have been lost after the server committed it.
      // Reconcile before retrying so an answer is never submitted twice.
      const latest = await getInterview(id);
      if (generation !== lifecycle.current) return;
      const question = latest.questions.find(q => q.id === current.id);
      if (!question?.answer && latest.status !== "completed") await submitAnswer(current.id, answerText, duration);
      if (generation !== lifecycle.current) return;
      await advance(await getInterview(id), generation);
    } catch (err) {
      if (generation === lifecycle.current) {
        setError(`${err.message} Your answer is still here; retry when connected.`);
        busy.current = false; typingRef.current = true; setTyping(true); setPhase("listening");
      }
    }
  }

  async function finish() {
    if (phase === "processing") return;
    setPhase("processing"); setError("");
    const generation = lifecycle.current;
    try { await advance(await getInterview(id), generation); }
    catch (err) { if (generation === lifecycle.current) { setError(err.message); setPhase("ready"); } }
  }

  function toggleInput() {
    stopRecognition(); typingRef.current = !typingRef.current; setTyping(typingRef.current);
    setNotice(""); listen();
  }

  if (!interview) return <div className="mx-auto max-w-3xl p-8">
    {error ? <><p role="alert">{error}</p><button className="mt-4 text-[var(--teal)]" onClick={() => setRetry(v => v + 1)}>Retry connection</button></> : <p role="status">Loading your interview…</p>}
  </div>;
  if (!current) return <div className="mx-auto max-w-3xl p-8">
    <h1 className="text-2xl">All questions answered</h1>
    {error && <p role="alert" className="mt-4 text-[var(--red)]">{error}</p>}
    <button disabled={phase === "processing"} onClick={finish} className="mt-6 rounded bg-[var(--amber)] px-5 py-3 text-black">{phase === "processing" ? "Saving report…" : "Finish and view report"}</button>
  </div>;

  const labels = toSession(interview);
  const primary = interview.questions.filter(q => !q.is_follow_up);
  const number = Math.min(primary.length, Math.floor(current.order_index / 2) + 1);
  const agentState = phase === "speaking" ? "speaking" : phase === "listening" ? "listening" : "thinking";
  return <main className="mx-auto max-w-3xl px-6 py-12">
    <div className="mb-6 text-sm text-[var(--text-muted)]">Question {number} / {primary.length}{current.is_follow_up ? " · Follow-up" : ""}</div>
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6">
      <p className="mb-2 text-xs text-[var(--text-muted)]">{labels.roleLabel} · {labels.typeLabel} · {labels.difficultyLabel}</p>
      <h1 className="text-xl font-medium">{current.is_follow_up && "Follow-up: "}{current.text}</h1>
      <div className="mt-6 flex items-center gap-5 rounded-lg bg-[var(--surface-raised)] p-5">
        <AgentAvatar state={agentState} /><div className="flex-1">
          <Waveform mode={phase === "speaking" ? "speaking" : phase === "listening" && !typing ? "listening" : "idle"} height={48} barCount={30} className="w-full justify-between" />
          <p role="status" className="mt-3 text-sm text-[var(--text-muted)]">{phase === "speaking" ? "Agent is speaking…" : phase === "processing" ? "Saving and scoring your answer…" : typing ? "Type your answer below" : "Listening — speak your answer"}</p>
        </div>
      </div>
      {notice && <p className="mt-4 text-[var(--amber)]">{notice}</p>}
      {error && <p role="alert" className="mt-4 text-[var(--red)]">{error}</p>}
      {typing ? <form onSubmit={event => { event.preventDefault(); submit(); }} className="mt-4">
        <textarea aria-label="Your answer" value={text} onChange={event => updateText(event.target.value)} maxLength={20000} disabled={phase !== "listening"} rows={5} className="w-full rounded border border-[var(--border)] bg-[var(--bg)] p-3" />
        <button disabled={phase !== "listening"} className="mt-3 rounded bg-[var(--teal)] px-4 py-2 text-black disabled:opacity-40">Submit answer</button>
      </form> : <p className="mt-4 min-h-12 rounded bg-[var(--bg)] p-3">{text || "Your transcript will appear here."}</p>}
      <div className="mt-5 flex flex-wrap items-center gap-3">
        {!typing && <button disabled={phase !== "listening"} onClick={() => submit()} className="inline-flex items-center gap-2 rounded bg-[var(--amber)] px-4 py-2 text-black disabled:opacity-40"><CheckCircle2 size={16} />I'm done answering</button>}
        {voiceSupported && <button disabled={phase !== "listening"} onClick={toggleInput} className="inline-flex items-center gap-2 text-sm disabled:opacity-40">{typing ? <Mic size={16} /> : <Keyboard size={16} />}{typing ? "Switch to voice" : "Switch to typing"}</button>}
        <button disabled={phase !== "listening"} onClick={() => submit(true)} className="ml-auto inline-flex items-center gap-2 text-sm disabled:opacity-40">Skip question <SkipForward size={16} /></button>
      </div>
    </div>
    <p className="mt-4 text-center text-xs text-[var(--text-muted)]">Answers and scores are saved to your account on the backend. Browser voice recognition may send audio to your browser provider.</p>
  </main>;
}
