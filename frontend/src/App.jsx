import { Routes, Route } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Home from "./pages/Home";
import BenchmarkSelector from "./pages/BenchmarkSelector";
import SessionDetail from "./pages/SessionDetail";

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Protected routes */}
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Home />} />
        <Route path="/benchmarks" element={<BenchmarkSelector />} />
        <Route path="/sessions/:sessionId" element={<SessionDetail />} />
      </Route>
    </Routes>
  );
}

export default App;
