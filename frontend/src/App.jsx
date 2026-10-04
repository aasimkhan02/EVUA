import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar/Sidebar';
import Navbar from './components/Navbar/Navbar';
import Migration from './pages/Migration/Migration';
import Workspace from './pages/Workspace/Workspace';
import Dashboard from './pages/Dashboard/Dashboard';
import Validation from './pages/Validation/Validation';
import History from './pages/History/History';
import Landing from './pages/landing/landing';
import './App.css';

const AppContent = () => {
  const location = useLocation();
  const [activePage, setActivePage] = useState('migration');

  useEffect(() => {
    if (location.pathname.includes('/history')) {
      setActivePage('history');
    } else if (location.pathname.includes('/project')) {
      setActivePage('migration');
    }
  }, [location]);

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

const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/*" element={<AppContent />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
