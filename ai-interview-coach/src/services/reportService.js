// reportService.js
//
// Generates a downloadable PDF interview report. Kept dependency-light
// (jsPDF only, no server round-trip) so the report works offline.

import { jsPDF } from "jspdf";
import { scoreLabel } from "./evaluationService";

const MARGIN = 15;
const PAGE_WIDTH = 210;
const CONTENT_WIDTH = PAGE_WIDTH - MARGIN * 2;

export function generateSessionPdf(session) {
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  let y = MARGIN;

  const addPageIfNeeded = (needed = 20) => {
    if (y + needed > 285) {
      doc.addPage();
      y = MARGIN;
    }
  };
  const writeLines = (lines, lineHeight = 4.5) => {
    for (const line of lines) {
      addPageIfNeeded(lineHeight);
      doc.text(line, MARGIN, y);
      y += lineHeight;
    }
  };

  // Header
  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text("Console — Interview Report", MARGIN, y);
  y += 8;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.setTextColor(90);
  doc.text(
    `${session.roleLabel} · ${session.typeLabel} · ${session.difficultyLabel} · ${new Date(
      session.completedAt
    ).toLocaleString()}`,
    MARGIN,
    y
  );
  doc.setTextColor(0);
  y += 10;

  // Summary block
  const s = session.summary;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.text("Overall summary", MARGIN, y);
  y += 6;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);

  const summaryLines = [
    `Overall score: ${s.overallScore ?? "—"} / 100 (${scoreLabel(s.overallScore)})`,
    `Communication score: ${s.communicationScore ?? "—"} / 100`,
    `Technical coverage: ${s.technicalScore ?? "—"} / 100`,
    `Average pace: ${s.avgWpm ?? "—"} words per minute`,
    `Filler words used: ${s.totalFillers}${
      s.topFillers?.length ? ` (most used: ${s.topFillers.map(([w, n]) => `"${w}" x${n}`).join(", ")})` : ""
    }`,
    `Responses (including follow-ups): ${s.questionCount}`,
  ];
  summaryLines.forEach((line) => {
    addPageIfNeeded();
    const wrapped = doc.splitTextToSize(line, CONTENT_WIDTH);
    writeLines(wrapped, 5);
  });

  y += 4;
  doc.setDrawColor(210);
  doc.line(MARGIN, y, PAGE_WIDTH - MARGIN, y);
  y += 8;

  // Per-question breakdown
  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  addPageIfNeeded();
  doc.text("Question-by-question breakdown", MARGIN, y);
  y += 8;

  session.answers.forEach((a, idx) => {
    addPageIfNeeded(35);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10.5);
    const qLines = doc.splitTextToSize(`Q${idx + 1}. ${a.question}`, CONTENT_WIDTH);
    writeLines(qLines, 5);
    y += 1;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(9.5);
    doc.setTextColor(70);
    const transcriptLines = doc.splitTextToSize(
      `Your answer: "${a.transcript || "(no answer recorded)"}"`,
      CONTENT_WIDTH
    );
    writeLines(transcriptLines);
    y += 2;

    doc.setTextColor(0);
    const evalu = a.evaluation;
    const metricLine = `Score: ${evalu.overallScore}/100 · Pace: ${evalu.wpm} wpm (${evalu.paceLabel}) · Fillers: ${evalu.fillerCount} · ${
      evalu.conceptCoverage !== null ? `Concept coverage: ${evalu.conceptCoverage}%` : `STAR structure: ${evalu.starScore}%`
    }`;
    const metricLines = doc.splitTextToSize(metricLine, CONTENT_WIDTH);
    addPageIfNeeded(metricLines.length * 4.5 + 8);
    doc.setFontSize(9);
    doc.setTextColor(50);
    writeLines(metricLines);

    if (evalu.conceptsMissed?.length) {
      const missedLine = `Consider mentioning: ${evalu.conceptsMissed.join(", ")}`;
      const missedLines = doc.splitTextToSize(missedLine, CONTENT_WIDTH);
      addPageIfNeeded(missedLines.length * 4.5 + 4);
      doc.setTextColor(150, 90, 20);
      writeLines(missedLines);
      doc.setTextColor(0);
    }

    const assessment = evalu.assessment || {};
    const assessed = ["ai", "unanswered"].includes(assessment.method);
    const coverage = assessment.coverage_percentage ?? evalu.conceptCoverage;
    const assessmentLines = assessed ? [
      `Correct: ${assessment.correct_percentage}% | Incorrect: ${assessment.incorrect_percentage}% | Missing: ${assessment.missing_percentage}%`,
      assessment.method === "ai" ? "AI estimates of answer requirements; missing points are not counted as wrong." : "No answer recorded; requirements are missing, not incorrect.",
    ] : [
      coverage == null ? "Concept coverage: not assessed" : `Concepts covered: ${coverage}% | Missing concepts: ${100 - coverage}%`,
      "Keyword coverage does not verify factual correctness.",
    ];
    if (evalu.feedback) assessmentLines.push(`Feedback: ${evalu.feedback}`);
    for (const [heading, items] of [
      ["What you got right", assessment.strengths], ["What to correct", assessment.corrections],
      ["How to improve", assessment.improvements],
    ]) {
      for (const item of items || []) assessmentLines.push(`${heading}: ${item}`);
    }
    for (const line of assessmentLines) writeLines(doc.splitTextToSize(line, CONTENT_WIDTH));

    y += 5;
  });

  doc.save(`console-interview-report-${session.id}.pdf`);
}
