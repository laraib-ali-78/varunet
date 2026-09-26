import React, { useState } from 'react';
import { DashboardPage } from './pages/DashboardPage';
import { CitizenPortal } from './components/CitizenPortal/CitizenPortal';

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<'operator' | 'citizen'>('operator');

  return (
    <div>
      {/* Top Application Switcher Bar */}
      <div style={{
        background: '#020617',
        borderBottom: '1px solid #1e293b',
        padding: '8px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc' }}>VaruNet View:</span>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setCurrentView('operator')}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              background: currentView === 'operator' ? '#6366f1' : '#0f172a',
              color: currentView === 'operator' ? '#ffffff' : '#94a3b8',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            Operator Command Dashboard
          </button>
          <button
            onClick={() => setCurrentView('citizen')}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              background: currentView === 'citizen' ? '#0ea5e9' : '#0f172a',
              color: currentView === 'citizen' ? '#ffffff' : '#94a3b8',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            Citizen Weather Portal
          </button>
        </div>
      </div>

      {/* View Rendering */}
      {currentView === 'operator' ? (
        <DashboardPage />
      ) : (
        <div style={{ minHeight: '100vh', background: '#f1f5f9' }}>
          <CitizenPortal />
        </div>
      )}
    </div>
  );
};

export default App;
