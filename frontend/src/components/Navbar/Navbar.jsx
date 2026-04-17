import React, { useState } from 'react';
import './Navbar.css';

const Navbar = () => {
  const [activeLink, setActiveLink] = useState('Platform');

  const navLinks = ['Platform', 'Migrations', 'Features', 'Success Stories'];

  return (
    <nav className="navbar">
      <div className="navbar-logo">
        EVUA
      </div>
      
      <ul className="navbar-links">
        {navLinks.map((link) => (
          <li key={link} className="nav-item">
            <button 
              className={`nav-link ${activeLink === link ? 'active' : ''}`}
              onClick={() => setActiveLink(link)}
            >
              {link}
            </button>
          </li>
        ))}
      </ul>

      <div className="navbar-actions">
        <button className="login-btn">Log In</button>
        <button className="get-access-btn">Get Access</button>
      </div>
    </nav>
  );
};

export default Navbar;
