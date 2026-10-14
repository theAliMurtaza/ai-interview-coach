import { createContext, useContext, useState, useCallback } from "react";

const InterviewContext = createContext(null);

export function InterviewProvider({ children }) {
  const [setup, setSetup] = useState({
    role: null,
    roleLabel: "",
    type: "technical",
    typeLabel: "Technical",
    difficulty: "junior",
    difficultyLabel: "Junior",
    questionCount: 6,
    inputMode: "voice", // "voice" | "text"
  });

  const updateSetup = useCallback((patch) => {
    setSetup((prev) => ({ ...prev, ...patch }));
  }, []);

  const value = { setup, updateSetup };

  return <InterviewContext.Provider value={value}>{children}</InterviewContext.Provider>;
}

export function useInterview() {
  const ctx = useContext(InterviewContext);
  if (!ctx) throw new Error("useInterview must be used within InterviewProvider");
  return ctx;
}
