import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { lazy, Suspense } from "react";
import { InterviewProvider } from "./context/InterviewContext";
import Navbar from "./components/Navbar";
import { AuthProvider, RequireAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Landing from "./pages/Landing";
import RoleSelect from "./pages/RoleSelect";
import Interview from "./pages/Interview";
const Results = lazy(() => import("./pages/Results"));
const Dashboard = lazy(() => import("./pages/Dashboard"));

export default function App() {
  return (
    <InterviewProvider>
      <BrowserRouter>
        <AuthProvider>
        <div className="min-h-screen bg-[var(--bg)] text-[var(--text-primary)]">
          <Navbar />
          <Suspense fallback={<p role="status" className="p-8 text-center">Loading…</p>}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/setup" element={<RequireAuth><RoleSelect /></RequireAuth>} />
            <Route path="/interview" element={<Navigate to="/setup" replace />} />
            <Route path="/interview/:id" element={<RequireAuth><Interview /></RequireAuth>} />
            <Route path="/results/:id" element={<RequireAuth><Results /></RequireAuth>} />
            <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </Suspense>
        </div>
        </AuthProvider>
      </BrowserRouter>
    </InterviewProvider>
  );
}
