import React, { useState } from 'react';
import Sidebar from './components/Sidebar/Sidebar';
import Navbar from './components/Navbar/Navbar';
import Migration from './pages/Migration/Migration';
import Workspace from './pages/Workspace/Workspace';
import Dashboard from './pages/Dashboard/Dashboard';
import Validation from './pages/Validation/Validation';
import History from './pages/History/History';
import Login from './pages/Login/Login';
import Register from './pages/Register/Register';
import { useAuth } from './context/AuthContext';
import './App.css';

const App = () => {
  const { isAuthenticated, loading } = useAuth();
  const [activePage, setActivePage] = useState('migration');
  const [authView, setAuthView] = useState('login'); // 'login' or 'register'

  if (loading) {
    return <div className="loading-screen">Loading EVUA...</div>;
  }

  if (!isAuthenticated) {
    return authView === 'login' ? (
      <Login switchToRegister={() => setAuthView('register')} />
    ) : (
      <Register switchToLogin={() => setAuthView('login')} />
    );
  }

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
      <Sidebar
        activePage={activePage}
        setActivePage={setActivePage}
        onLogoClick={() => setActivePage('migration')}
      />
      <div className="main-content" style={{ height: '100vh', overflowY: 'auto' }}>
        <Navbar
          onLogoClick={() => setActivePage('migration')}
          onNavClick={setActivePage}
          activePage={activePage}
        />
        {renderContent()}
      </div>
    </div>
  );
};

export default App;