import { useEffect, useRef, useState } from "react";
import { api } from "../services/apiService";
import { ROLES } from "../data/questionBank";

export const parseSpecialties = text => [...new Map(text.split(",").map(s => s.trim()).filter(Boolean).map(s => [s.toLowerCase(), s])).values()];

export default function ResumeSetup({ resumeId, specialties, onResume, onSpecialties, onUploading, disabled }) {
  const [resumes, setResumes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [listError, setListError] = useState("");
  const [hasMore, setHasMore] = useState(false);
  const offset = useRef(0);
  const uploadLock = useRef(false);
  const selected = resumes.find(resume => resume.id === resumeId);
  const topics = parseSpecialties(specialties);

  useEffect(() => {
    let active = true;
    api("/resumes?limit=20&offset=0").then(items => {
      if (active) { setResumes(items); offset.current = items.length; setHasMore(items.length === 20); }
    }).catch(err => { if (active) setListError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function loadMore() {
    setLoading(true); setListError("");
    try {
      const items = await api(`/resumes?limit=20&offset=${offset.current}`);
      setResumes(previous => [...new Map([...previous, ...items].map(item => [item.id, item])).values()]);
      offset.current += items.length; setHasMore(items.length === 20);
    } catch (err) { setListError(err.message); }
    finally { setLoading(false); }
  }

  function selectResume(resume) {
    onResume(resume?.id || "", resume);
    if (resume) onSpecialties((resume.suggested_specialties ?? resume.skills).filter(s => s.trim().length <= 60 && !s.includes(",")).slice(0, 20).join(", "));
  }

  async function upload(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || uploadLock.current) return;
    setError("");
    if (!/\.(pdf|docx|txt)$/i.test(file.name)) { setError("Choose a PDF, DOCX, or TXT resume."); return; }
    if (file.size > 10 * 1024 * 1024) { setError("Choose a resume smaller than 10 MB."); return; }
    uploadLock.current = true; setUploading(true); onUploading(true);
    try {
      const body = new FormData(); body.append("file", file);
      const resume = await api("/resumes/upload", { method: "POST", body });
      setResumes(previous => [resume, ...previous]);
      // The new item shifts subsequent pages by one.
      offset.current += 1;
      selectResume(resume);
    } catch (err) { setError(err.message); }
    finally { uploadLock.current = false; setUploading(false); onUploading(false); }
  }

  function toggleSkill(skill) {
    const exists = topics.some(topic => topic.toLowerCase() === skill.toLowerCase());
    onSpecialties((exists ? topics.filter(topic => topic.toLowerCase() !== skill.toLowerCase()) : [...topics, skill]).join(", "));
  }

  return <section className="mt-8 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5" aria-labelledby="resume-heading">
    <h2 id="resume-heading" className="text-lg font-medium">Resume & specialties</h2>
    <p className="mt-1 text-sm text-[var(--text-secondary)]">Upload a resume to select your interview role from its headline and detect relevant skills. You can adjust the role and topics before starting.</p>
    <label htmlFor="resume-file" className="mt-4 block text-sm font-medium">Upload resume (optional)</label>
    <input id="resume-file" type="file" accept=".pdf,.docx,.txt" onChange={upload} disabled={disabled || uploading || loading}
      className="mt-2 block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-[var(--teal-dim)] file:px-4 file:py-2 file:text-[var(--text-primary)] disabled:opacity-50" />
    <p className="mt-2 text-xs text-[var(--text-muted)]">Readable PDF, DOCX, or TXT, up to 10 MB. Scanned images need text recognition first. Saved resumes are private to your account.</p>
    {uploading && <p role="status" className="mt-2 text-sm">Uploading and reading your resume…</p>}
    {error && <p role="alert" className="mt-2 text-sm text-[var(--red)]">{error}</p>}
    {loading && <p className="mt-2 text-sm">Loading saved resumes…</p>}
    {resumes.length > 0 && <>
      <label htmlFor="saved-resume" className="mt-4 block text-sm font-medium">Saved resume</label>
      <select id="saved-resume" value={resumeId} onChange={event => selectResume(resumes.find(item => item.id === event.target.value))}
        disabled={disabled || uploading} className="mt-2 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] p-2 text-sm">
        <option value="">No resume — use the specialties below</option>
        {resumes.map(resume => <option key={resume.id} value={resume.id}>{resume.filename} · {new Date(resume.created_at).toLocaleString()}</option>)}
      </select>
    </>}
    {listError && <p role="alert" className="mt-2 text-sm text-[var(--red)]">Could not load saved resumes: {listError}</p>}
    {(hasMore || listError) && <button type="button" onClick={loadMore} disabled={loading || uploading || disabled} className="mt-2 text-sm text-[var(--teal)]">{listError ? "Retry loading resumes" : "Load more resumes"}</button>}
    {selected && <div className="mt-4">
      {selected.headline && <p className="mb-2 text-sm">Resume headline: <strong>{selected.headline}</strong></p>}
      <p role="status" className="mb-4 text-sm text-[var(--teal)]">{selected.suggested_role
        ? `Detected ${ROLES.find(role => role.id === selected.suggested_role)?.label || selected.suggested_role} from your headline. You can change the role below.`
        : "No clear interview role found in the headline. Choose a role below."}</p>
      <p className="text-sm font-medium">Detected skills</p>
      {selected.skills.length ? <div className="mt-2 flex flex-wrap gap-2">{[...new Set(selected.skills)].map(skill => {
        const active = topics.some(topic => topic.toLowerCase() === skill.toLowerCase());
        return <button key={skill} type="button" aria-pressed={active} onClick={() => toggleSkill(skill)} disabled={disabled || uploading || (!active && topics.length >= 20)}
          className={`rounded-full border px-3 py-1 text-sm disabled:opacity-50 ${active ? "border-[var(--teal)] bg-[var(--teal-dim)]/30" : "border-[var(--border)] text-[var(--text-muted)]"}`}>{skill}</button>;
      })}</div> : <p className="mt-2 text-sm text-[var(--text-secondary)]">No recognized skills found. Enter your specialties below.</p>}
      <p className="mt-2 text-xs text-[var(--text-muted)]">Click a skill to include or remove it. You can select up to 20 topics.</p>
    </div>}
    <label htmlFor="specialties" className="mt-4 block text-sm font-medium">Specialties to practice</label>
    <input id="specialties" value={specialties} onChange={event => onSpecialties(event.target.value)} disabled={disabled || uploading} maxLength={1250}
      placeholder="React, TypeScript, GraphQL" className="mt-2 w-full rounded-md border border-[var(--border)] bg-[var(--bg)] p-3 text-sm" />
    <p className="mt-2 text-xs text-[var(--text-muted)]">Separate topics with commas. Questions focus on these topics at your selected level. Leave blank for general questions about your role.</p>
  </section>;
}
