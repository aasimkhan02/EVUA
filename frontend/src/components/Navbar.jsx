import { Link, useNavigate } from "react-router-dom";
import useAuth from "../hooks/useAuth";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center font-bold text-white text-sm">
              E
            </div>
            <span className="text-lg font-semibold text-white">EVUA</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link
              to="/"
              className="text-gray-400 hover:text-white transition-colors text-sm"
            >
              Home
            </Link>
            <Link
              to="/benchmarks"
              className="text-gray-400 hover:text-white transition-colors text-sm"
            >
              Benchmarks
            </Link>
          </div>
        </div>
        {user && (
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 bg-indigo-500/20 border border-indigo-500/30 rounded-full flex items-center justify-center">
                <span className="text-indigo-400 text-xs font-medium">
                  {user.name?.charAt(0).toUpperCase()}
                </span>
              </div>
              <span className="text-sm text-gray-300">{user.name}</span>
            </div>
            <button
              onClick={handleLogout}
              className="text-sm text-gray-500 hover:text-red-400 transition-colors cursor-pointer"
            >
              Logout
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
