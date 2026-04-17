import React from 'react';
import { Compass, SquareTerminal, FolderKanban, LayoutDashboard, ShieldCheck, History } from 'lucide-react';
import './Sidebar.css';

const Sidebar = ({ activePage, setActivePage }) => {
  const menuItems = [
    { id: 'migration', icon: SquareTerminal },       // 1st: Migration
    { id: 'workspace', icon: FolderKanban },         // 2nd: Workspace
    { id: 'dashboard', icon: LayoutDashboard },      // 3rd: Dashboard
    { id: 'validation', icon: ShieldCheck },         // 4th: Validation
    { id: 'history', icon: History },                // 5th: History
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <Compass className="logo-icon" size={24} />
      </div>

      <div className="sidebar-nav">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.id;
          
          return (
            <button
              key={item.id}
              className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setActivePage(item.id)}
            >
              <Icon 
                className={`nav-icon ${isActive ? 'active-icon' : ''}`} 
                size={22} 
                strokeWidth={isActive ? 2.5 : 2}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default Sidebar;
