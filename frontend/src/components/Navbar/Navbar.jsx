import React, { useState, useRef, useEffect } from 'react';
import { LogOut, ChevronDown, User } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import './Navbar.css';

const Navbar = ({ onLogoClick, onNavClick, activePage }) => {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
  };

  // Avatar initial from email
  const initial = (user?.email ?? 'U')[0].toUpperCase();

  return (
    <nav className="navbar">
      <button
        type="button"
        className="navbar-logo-button"
        onClick={onLogoClick}
        aria-label="Go to home"
      >
        <span className="navbar-logo">EVUA</span>
      </button>

      <ul className="navbar-links">
        {[
          { id: 'dashboard', label: 'Platform' },
          { id: 'migration', label: 'Migrations' },
          { id: 'validation', label: 'Features' },
        ].map((link) => (
          <li key={link} className="nav-item">
            <button
              className={`nav-link ${activePage === link.id ? 'active' : ''}`}
              onClick={() => onNavClick(link.id)}
              type="button"
            >
              {link.label}
            </button>
          </li>
        ))}
      </ul>

      {/* User menu */}
      <div className="navbar-actions">
        <div className="user-menu-wrapper" ref={menuRef}>
          <button
            className="user-menu-trigger"
            onClick={() => setMenuOpen(v => !v)}
            aria-label="User menu"
          >
            <div className="user-avatar">{initial}</div>
            <span className="user-email">{user?.email ?? 'Account'}</span>
            <ChevronDown size={14} className={`user-chevron ${menuOpen ? 'open' : ''}`} />
          </button>

          {menuOpen && (
            <div className="user-dropdown">
              <div className="user-dropdown-header">
                <div className="user-avatar-lg">{initial}</div>
                <div>
                  <div className="user-dropdown-email">{user?.email ?? '—'}</div>
                  <div className="user-dropdown-role">EVUA User</div>
                </div>
              </div>
              <div className="user-dropdown-divider" />
              <button className="user-dropdown-item logout-item" onClick={handleLogout}>
                <LogOut size={14} />
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
