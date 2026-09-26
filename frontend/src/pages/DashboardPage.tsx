import React, { useState } from 'react';
import { SelectorBar, SelectorState } from '../components/ForecastDashboard/SelectorBar';
import { ForecastPanel } from '../components/ForecastDashboard/ForecastPanel';
import { ComparisonChart } from '../components/ForecastComparison/ComparisonChart';
import { WeightDistributionMap } from '../components/WeightDistributionMap/WeightDistributionMap';
import { AlertDashboard } from '../components/AlertDashboard/AlertDashboard';
import { AnalyticsDashboard } from '../components/AnalyticsDashboard/AnalyticsDashboard';

export const DashboardPage: React.FC = () => {
  const [selectors, setSelectors] = useState<SelectorState>({
    regionId: 1,
    validTime: new Date().toISOString(),
    leadTimeHrs: 24,
    variable: 'rainfall',
    regimeId: 1,
  });

  const [activeSection, setActiveSection] = useState<'forecast' | 'alerts' | 'analytics'>('forecast');

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
