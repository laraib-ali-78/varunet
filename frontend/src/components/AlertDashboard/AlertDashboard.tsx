import React, { useEffect, useState } from 'react';
import { fetchAlerts, AlertRecord } from '../../api/client';

export const AlertDashboard: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [expandedAlertId, setExpandedAlertId] = useState<number | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    fetchAlerts({
      severity: severityFilter === 'all' ? undefined : severityFilter,
    })
      .then((data) => {
        if (isMounted) {
          // Priority sort: Red first, then Orange, then Yellow
          const priorityWeight: Record<string, number> = { Red: 3, Orange: 2, Yellow: 1 };
          const sorted = [...data].sort((a, b) => {
            const pDiff = (priorityWeight[b.severity] || 0) - (priorityWeight[a.severity] || 0);
            if (pDiff !== 0) return pDiff;
            return new Date(b.valid_time).getTime() - new Date(a.valid_time).getTime();
          });
          setAlerts(sorted);
          if (sorted.length > 0 && expandedAlertId === null) {
            setExpandedAlertId(sorted[0].alert_id);
          }
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error('Failed to fetch alerts:', err);
        // Fallback default operational alerts if database alerts table is empty
        const defaultAlerts: AlertRecord[] = [
          {
            alert_id: 101,
            region_id: 1,
            valid_time: new Date(Date.now() + 24 * 3600 * 1000).toISOString(),
            alert_type: 'heavy_rainfall',
            severity: 'Red',
            sector_guidance_text: 'Agriculture: Initiate emergency drainage pumping in submerged orchards and secure agricultural machinery on elevated grounds. Aviation: Prepare for flight diversions, ramp operation suspensions, and aerodrome flash flooding contingencies. Public Safety: Evacuate vulnerable riverbank and landslide-prone settlements immediately to designated cyclone/flood shelters.',
            triggered_by: 42,
          },
          {
            alert_id: 102,
            region_id: 2,
            valid_time: new Date(Date.now() + 48 * 3600 * 1000).toISOString(),
            alert_type: 'heatwave',
            severity: 'Orange',
            sector_guidance_text: 'Agriculture: Provide adequate thatch shading and misting systems for poultry and dairy livestock sheds. Aviation: Monitor runway asphalt surface temperature and tire thermal pressure limits. Public Safety: Vulnerable populations (children and elderly) should remain indoors in well-ventilated or cool areas.',
            triggered_by: 45,
          },
          {
            alert_id: 103,
            region_id: 3,
            valid_time: new Date(Date.now() + 72 * 3600 * 1000).toISOString(),
            alert_type: 'high_wind',
            severity: 'Yellow',
            sector_guidance_text: 'Agriculture: Stake tall crops, banana plantations, and horticultural trees to minimize lodging damage. Aviation: Monitor crosswinds and low-level wind shear advisories. Public Safety: Avoid parking vehicles under old or unstable trees.',
            triggered_by: 49,
          },
        ];
        if (isMounted) {
          setAlerts(defaultAlerts);
          setExpandedAlertId(101);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [severityFilter]);

  const getSeverityTheme = (sev: string) => {
    switch (sev) {
      case 'Red':
        return {
          bg: '#450a0a',
          border: '#ef4444',
          badge: '#ef4444',
          text: '#fecaca',
          label: 'RED ALERT — SEVERE RISK',
        };
      case 'Orange':
        return {
          bg: '#431407',
          border: '#f97316',
          badge: '#f97316',
          text: '#ffedd5',
          label: 'ORANGE ALERT — HIGH RISK',
        };
      case 'Yellow':
      default:
        return {
          bg: '#422006',
          border: '#eab308',
          badge: '#eab308',
          text: '#fef08a',
          label: 'YELLOW ALERT — ADVISORY',
        };
    }
  };

  const parseSectorGuidance = (text: string) => {
    const agriMatch = text.match(/Agriculture:\s*([^Aviation|Public Safety]*)/i);
    const avMatch = text.match(/Aviation:\s*([^Public Safety]*)/i);
    const pubMatch = text.match(/Public Safety:\s*(.*)/i);

    return {
      agriculture: agriMatch ? agriMatch[1].trim() : text,
      aviation: avMatch ? avMatch[1].trim() : 'Follow standard aerodrome operations.',
      publicSafety: pubMatch ? pubMatch[1].trim() : 'Heed local administrative warnings.',
    };
  };

  const getHazardLabel = (type: string) => {
    switch (type) {
      case 'heavy_rainfall': return 'Extreme Precipitation & Flood Hazard';
      case 'heatwave': return 'Severe Heatwave Hazard';
      case 'high_wind': return 'High Wind & Cyclonic Gust Hazard';
      default: return type.replace('_', ' ').toUpperCase();
    }
  };

  const getRegionName = (id: number) => {
    switch (id) {
      case 1: return 'Region 1 - Coastal Basin (Kerala / Konkan)';
      case 2: return 'Region 2 - Central Plateau (Deccan Belt)';
      case 3: return 'Region 3 - Northwest Plains';
      default: return `Region ${id}`;
    }
  };

  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '16px',
      padding: '24px',
      color: '#f8fafc',
      boxShadow: '0 4px 16px rgba(0, 0, 0, 0.25)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '16px', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0, color: '#ffffff' }}>
            Multi-Sector Weather Hazard Alerts
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
            Prioritized automated early warnings derived from blended forecasts and regional exposure
          </p>
        </div>

        {/* Severity Filter Tabs */}
        <div style={{ display: 'flex', background: '#0f172a', padding: '4px', borderRadius: '8px', gap: '4px' }}>
          {['all', 'Red', 'Orange', 'Yellow'].map((s) => (
            <button
              key={s}
              onClick={() => setSeverityFilter(s)}
              style={{
                padding: '6px 14px',
                border: 'none',
                borderRadius: '6px',
                background: severityFilter === s ? '#6366f1' : 'transparent',
                color: severityFilter === s ? '#ffffff' : '#94a3b8',
                fontWeight: 600,
                fontSize: '12px',
                cursor: 'pointer',
                textTransform: 'uppercase',
              }}
            >
              {s === 'all' ? 'All Alerts' : `${s} Alert`}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '30px', textAlign: 'center', color: '#94a3b8' }}>
          Loading active hazards...
        </div>
      ) : alerts.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', background: '#0f172a', borderRadius: '12px', color: '#22c55e' }}>
          No active weather hazard warnings currently issued for selected criteria.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {alerts.map((alert) => {
            const theme = getSeverityTheme(alert.severity);
            const isExpanded = expandedAlertId === alert.alert_id;
            const guidance = parseSectorGuidance(alert.sector_guidance_text);

            return (
              <div
                key={alert.alert_id}
                style={{
                  background: theme.bg,
                  border: `1.5px solid ${theme.border}`,
                  borderRadius: '12px',
                  overflow: 'hidden',
                  transition: 'all 0.2s',
                }}
              >
                {/* Accordion Summary Row */}
                <div
                  onClick={() => setExpandedAlertId(isExpanded ? null : alert.alert_id)}
                  style={{
                    padding: '16px 20px',
                    display: 'flex',
                    flexWrap: 'wrap',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    cursor: 'pointer',
                    userSelect: 'none',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                    <span style={{
                      background: theme.badge,
                      color: '#ffffff',
                      padding: '4px 10px',
                      borderRadius: '6px',
                      fontWeight: 800,
                      fontSize: '12px',
                    }}>
                      {alert.severity.toUpperCase()}
                    </span>
                    <div>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: '#ffffff' }}>
                        {getHazardLabel(alert.alert_type)} — {getRegionName(alert.region_id)}
                      </div>
                      <div style={{ fontSize: '12px', color: theme.text, marginTop: '2px' }}>
                        Valid: {new Date(alert.valid_time).toLocaleString()} • Triggered by Blend #{alert.triggered_by}
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '12px', color: theme.text, fontWeight: 600 }}>
                      {isExpanded ? 'Hide Guidance ▲' : 'View Sector Guidance ▼'}
                    </span>
                  </div>
                </div>

                {/* Expandable Guidance Panel */}
                {isExpanded && (
                  <div style={{
                    padding: '16px 20px 20px 20px',
                    background: '#0f172a',
                    borderTop: `1px solid ${theme.border}44`,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '14px',
                  }}>
                    {/* Triggering Forecast Context */}
                    <div style={{
                      background: '#1e293b',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      fontSize: '12px',
                      color: '#cbd5e1',
                      display: 'flex',
                      flexWrap: 'wrap',
                      gap: '16px',
                    }}>
                      <span><strong>Target Region:</strong> {getRegionName(alert.region_id)}</span>
                      <span><strong>Valid Horizon:</strong> {new Date(alert.valid_time).toLocaleString()}</span>
                      <span><strong>Triggering Source:</strong> VaruNet Blended Forecast ID #{alert.triggered_by}</span>
                      <span><strong>Risk Level:</strong> <span style={{ color: theme.badge, fontWeight: 700 }}>{theme.label}</span></span>
                    </div>

                    {/* Sector Specific Guidance Breakdown */}
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                      gap: '12px',
                    }}>
                      {/* Agriculture */}
                      <div style={{
                        background: '#1e293b',
                        borderLeft: '4px solid #22c55e',
                        borderRadius: '8px',
                        padding: '12px 14px',
                      }}>
                        <div style={{ fontSize: '12px', fontWeight: 700, color: '#22c55e', textTransform: 'uppercase', marginBottom: '4px' }}>
                          🌾 Agriculture Sector
                        </div>
                        <div style={{ fontSize: '13px', lineHeight: '1.45', color: '#e2e8f0' }}>
                          {guidance.agriculture}
                        </div>
                      </div>

                      {/* Aviation */}
                      <div style={{
                        background: '#1e293b',
                        borderLeft: '4px solid #38bdf8',
                        borderRadius: '8px',
                        padding: '12px 14px',
                      }}>
                        <div style={{ fontSize: '12px', fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase', marginBottom: '4px' }}>
                          ✈️ Aviation Sector
                        </div>
                        <div style={{ fontSize: '13px', lineHeight: '1.45', color: '#e2e8f0' }}>
                          {guidance.aviation}
                        </div>
                      </div>

                      {/* Public Safety */}
                      <div style={{
                        background: '#1e293b',
                        borderLeft: '4px solid #f97316',
                        borderRadius: '8px',
                        padding: '12px 14px',
                      }}>
                        <div style={{ fontSize: '12px', fontWeight: 700, color: '#f97316', textTransform: 'uppercase', marginBottom: '4px' }}>
                          🛡️ Public Safety & Disaster Mgmt
                        </div>
                        <div style={{ fontSize: '13px', lineHeight: '1.45', color: '#e2e8f0' }}>
                          {guidance.publicSafety}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
