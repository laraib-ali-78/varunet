import React, { useState, useEffect } from 'react';
import { SelectorBar, SelectorState } from '../components/ForecastDashboard/SelectorBar';
import { ForecastPanel } from '../components/ForecastDashboard/ForecastPanel';
import { ComparisonChart } from '../components/ForecastComparison/ComparisonChart';
import { WeightDistributionMap } from '../components/WeightDistributionMap/WeightDistributionMap';
import { AlertDashboard } from '../components/AlertDashboard/AlertDashboard';
import { AnalyticsDashboard } from '../components/AnalyticsDashboard/AnalyticsDashboard';
import { getStoredUser, loginUser, logoutUser } from '../api/client';

export const DashboardPage: React.FC = () => {
  const [selectors, setSelectors] = useState<SelectorState>({
    regionId: 1,
    validTime: '2024-06-15T00:00:00Z',
    leadTimeHrs: 24,
    variable: 'rainfall',
    regimeId: 1,
  });


  const [activeSection, setActiveSection] = useState<'forecast' | 'alerts' | 'analytics'>('forecast');
  
  // Operator Authentication State
  const [currentUser, setCurrentUser] = useState<{ email: string; role: string } | null>(getStoredUser());
  const [loginEmail, setLoginEmail] = useState<string>('forecaster@varunet.in');
  const [loginPassword, setLoginPassword] = useState<string>('Forecaster@123');
  const [authLoading, setAuthLoading] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    try {
      const resp = await loginUser(loginEmail, loginPassword);
      setCurrentUser({ email: resp.email, role: resp.role });
      // Trigger refresh of panels
      setSelectors((prev) => ({ ...prev }));
    } catch (err: any) {
      setAuthError(err.message || 'Login failed');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    logoutUser();
    setCurrentUser(null);
    setSelectors((prev) => ({ ...prev }));
  };

  const handleSelectorChange = (updated: Partial<SelectorState>) => {
    setSelectors((prev) => ({ ...prev, ...updated }));
  };

  const handleRegionClick = (regionId: number) => {
    setSelectors((prev) => ({ ...prev, regionId }));
  };

  const handleRefresh = () => {
    setSelectors((prev) => ({ ...prev }));
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: '#090d16',
      color: '#f8fafc',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
      padding: '24px 32px',
    }}>
      {/* Top Header */}
      <header style={{
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingBottom: '20px',
        marginBottom: '20px',
        borderBottom: '1px solid #1e293b',
        gap: '16px',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h1 style={{ fontSize: '26px', fontWeight: 800, margin: 0, color: '#ffffff', letterSpacing: '-0.02em' }}>
              VaruNet
            </h1>
            <span style={{
              background: 'linear-gradient(90deg, #6366f1, #38bdf8)',
              padding: '3px 10px',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: 700,
              color: '#ffffff',
              textTransform: 'uppercase',
            }}>
              SIH26081 Hybrid AI–NWP
            </span>
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
            Real-Time Multi-Model Forecast Blending, Deterministic Verification & Explainability Portal
          </p>
        </div>

        {/* Navigation Mode Switcher */}
        <div style={{ display: 'flex', background: '#0f172a', padding: '4px', borderRadius: '10px', gap: '4px' }}>
          <button
            onClick={() => setActiveSection('forecast')}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '8px',
              background: activeSection === 'forecast' ? '#6366f1' : 'transparent',
              color: activeSection === 'forecast' ? '#ffffff' : '#94a3b8',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            Forecast & Blending
          </button>
          <button
            onClick={() => setActiveSection('alerts')}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '8px',
              background: activeSection === 'alerts' ? '#ef4444' : 'transparent',
              color: activeSection === 'alerts' ? '#ffffff' : '#94a3b8',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            Hazard Alerts
          </button>
          <button
            onClick={() => setActiveSection('analytics')}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '8px',
              background: activeSection === 'analytics' ? '#6366f1' : 'transparent',
              color: activeSection === 'analytics' ? '#ffffff' : '#94a3b8',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            Verification & Analytics
          </button>
        </div>
      </header>

      {/* Operator Authentication Bar */}
      <div style={{
        background: '#0f172a',
        border: '1px solid #1e293b',
        borderRadius: '8px',
        padding: '12px 18px',
        marginBottom: '20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
      }}>
        {currentUser ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ height: '8px', width: '8px', borderRadius: '50%', background: '#22c55e', display: 'inline-block' }}></span>
              <span style={{ fontSize: '13px', color: '#e2e8f0', fontWeight: 600 }}>
                Logged In as Operator: <code style={{ color: '#38bdf8' }}>{currentUser.email}</code>
              </span>
              <span style={{ fontSize: '11px', background: '#334155', color: '#94a3b8', padding: '2px 8px', borderRadius: '4px', textTransform: 'uppercase', fontWeight: 700 }}>
                Role: {currentUser.role}
              </span>
            </div>
            <button
              onClick={handleLogout}
              style={{
                background: '#334155',
                color: '#f8fafc',
                border: 'none',
                borderRadius: '6px',
                padding: '6px 14px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Sign Out
            </button>
          </div>
        ) : (
          <form onSubmit={handleLogin} style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', width: '100%' }}>
            <span style={{ fontSize: '13px', color: '#94a3b8', fontWeight: 600 }}>
              Operator Authentication (for /forecasts & /skill-scores):
            </span>
            <input
              type="email"
              value={loginEmail}
              onChange={(e) => setLoginEmail(e.target.value)}
              placeholder="Email"
              required
              style={{
                background: '#1e293b',
                border: '1px solid #334155',
                color: '#ffffff',
                padding: '6px 10px',
                borderRadius: '6px',
                fontSize: '12px',
                outline: 'none',
              }}
            />
            <input
              type="password"
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
              placeholder="Password"
              required
              style={{
                background: '#1e293b',
                border: '1px solid #334155',
                color: '#ffffff',
                padding: '6px 10px',
                borderRadius: '6px',
                fontSize: '12px',
                outline: 'none',
              }}
            />
            <button
              type="submit"
              disabled={authLoading}
              style={{
                background: '#6366f1',
                color: '#ffffff',
                border: 'none',
                borderRadius: '6px',
                padding: '6px 14px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {authLoading ? 'Signing In...' : 'Sign In as Forecaster'}
            </button>
            {authError && (
              <span style={{ color: '#ef4444', fontSize: '12px', fontWeight: 500 }}>
                {authError}
              </span>
            )}
          </form>
        )}
      </div>

      {/* Main Content Body */}
      <main style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {activeSection === 'forecast' && (
          <>
            {/* Global Selector */}
            <SelectorBar
              selectors={selectors}
              onChange={handleSelectorChange}
              onRefresh={handleRefresh}
            />

            {/* Leaflet Geospatial Weight Distribution Map */}
            <WeightDistributionMap
              selectors={selectors}
              onSelectRegion={handleRegionClick}
            />

            {/* Forecast & Blending Panel */}
            <ForecastPanel selectors={selectors} />

            {/* Multi-Model Verification Comparison */}
            <ComparisonChart />
          </>
        )}

        {activeSection === 'alerts' && (
          <AlertDashboard />
        )}

        {activeSection === 'analytics' && (
          <AnalyticsDashboard />
        )}
      </main>
    </div>
  );
};
