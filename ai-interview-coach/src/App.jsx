import { BrowserRouter, Routes, Route } from "react-router-dom";
import { InterviewProvider } from "./context/InterviewContext";
import Navbar from "./components/Navbar";
import Landing from "./pages/Landing";
import RoleSelect from "./pages/RoleSelect";
import Interview from "./pages/Interview";
import Results from "./pages/Results";
import Dashboard from "./pages/Dashboard";

export default function App() {
  return (
    <InterviewProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-[var(--bg)] text-[var(--text-primary)]">
          <Navbar />
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/setup" element={<RoleSelect />} />
            <Route path="/interview" element={<Interview />} />
            <Route path="/results/:id" element={<Results />} />
            <Route path="/dashboard" element={<Dashboard />} />
          </Routes>
        </div>
      </BrowserRouter>
    </InterviewProvider>
  );
}
