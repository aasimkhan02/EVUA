import React, { useState } from 'react';
import Sidebar from './components/Sidebar/Sidebar';
import Navbar from './components/Navbar/Navbar';
import Migration from './pages/Migration/Migration';
import Workspace from './pages/Workspace/Workspace';
import Dashboard from './pages/Dashboard/Dashboard';
import Validation from './pages/Validation/Validation';
import History from './pages/History/History';
import './App.css';

const App = () => {
  const [activePage, setActivePage] = useState('migration');

  const renderContent = () => {
    switch (activePage) {
      case 'migration':
        return <Migration setActivePage={setActivePage} />;
      case 'workspace':
        return <Workspace />;
      case 'dashboard':
        return <Dashboard />;
      case 'validation':
        return <Validation />;
      case 'history':
        return <History />;
      default:
        return <Migration />;
    }
  };

  return (
    <div className="app-container">
      <Sidebar activePage={activePage} setActivePage={setActivePage} />
      <div className="main-content" style={{ height: '100vh', overflowY: 'auto' }}>
        <Navbar />
        {renderContent()}
      </div>
    </div>
  );
};

export default App;