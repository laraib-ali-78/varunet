import React, { useEffect, useState } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import {
  fetchModelComparison,
  fetchSkillEvolution,
  fetchDisagreementGrid,
  ModelComparisonRecord,
  SkillEvolutionRecord,
  DisagreementGridRecord,
} from '../../api/client';

export const AnalyticsDashboard: React.FC = () => {
  const [comparisonData, setComparisonData] = useState<ModelComparisonRecord[]>([]);
  const [evolutionData, setEvolutionData] = useState<SkillEvolutionRecord[]>([]);
  const [disagreementData, setDisagreementData] = useState<DisagreementGridRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'comparison' | 'evolution' | 'disagreement'>('comparison');

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    Promise.all([
      fetchModelComparison().catch(() => []),
      fetchSkillEvolution().catch(() => []),
      fetchDisagreementGrid().catch(() => []),
    ]).then(([comp, evol, grid]) => {
      if (isMounted) {
        setComparisonData(comp);
        setEvolutionData(evol);
        setDisagreementData(grid);
        setLoading(false);
      }
    });

    return () => {
      isMounted = false;
    };
  }, []);

  const getHeatmapColor = (variance: number) => {
    if (variance >= 18) return '#991b1b'; // Severe (Deep Crimson)
    if (variance >= 10) return '#dc2626'; // Very High (Red)
    if (variance >= 6) return '#d97706';  // High (Amber)
    if (variance >= 3) return '#0d9488';  // Moderate (Teal)
    return '#0284c7';                     // Low (Blue)
  };

  // Unique regions and lead times for the disagreement heatmap matrix
  const regions = Array.from(new Set(disagreementData.map((d) => d.region)));
  const leadTimes = ['24h', '48h', '72h', '120h'];

  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '16px',
      padding: '24px',
      color: '#f8fafc',
      boxShadow: '0 4px 16px rgba(0, 0, 0, 0.25)',
      display: 'flex',
      flexDirection: 'column',
      gap: '20px',
    }}>
      {/* Header & Tab Bar */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0, color: '#ffffff' }}>
            Advanced Analytics & Model Verification Portal
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
            Historical error tracking, three-way benchmark comparisons, and inter-source disagreement heatmaps
          </p>
        </div>

        {/* View Switcher Tabs */}
        <div style={{ display: 'flex', background: '#0f172a', padding: '4px', borderRadius: '8px', gap: '4px' }}>
          <button
            onClick={() => setActiveTab('comparison')}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '6px',
              background: activeTab === 'comparison' ? '#6366f1' : 'transparent',
              color: activeTab === 'comparison' ? '#ffffff' : '#94a3b8',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            Three-Way Comparison
          </button>
          <button
            onClick={() => setActiveTab('evolution')}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '6px',
              background: activeTab === 'evolution' ? '#6366f1' : 'transparent',
              color: activeTab === 'evolution' ? '#ffffff' : '#94a3b8',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            Skill Evolution Over Time
          </button>
          <button
            onClick={() => setActiveTab('disagreement')}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '6px',
              background: activeTab === 'disagreement' ? '#6366f1' : 'transparent',
              color: activeTab === 'disagreement' ? '#ffffff' : '#94a3b8',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            Disagreement Heatmap
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#94a3b8' }}>
          Querying verification metrics from backend...
        </div>
      ) : (
        <>
          {/* 1. Three-Way Benchmark Comparison Chart */}
          {activeTab === 'comparison' && (
            <div>
              <div style={{ marginBottom: '16px', fontSize: '13px', color: '#cbd5e1' }}>
                Surface of the held-out validation benchmark: (a) Individual sources, (b) Naive equal-weight average, and (c) VaruNet blended model.
              </div>

              <div style={{ height: '320px', width: '100%', marginBottom: '20px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparisonData} margin={{ top: 15, right: 30, left: 10, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="strategy" stroke="#94a3b8" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                    <YAxis stroke="#94a3b8" tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{ background: '#0f172a', borderColor: '#475569', borderRadius: '8px', color: '#f8fafc' }}
                      formatter={(val: any, name: any) => [`${Number(val).toFixed(3)} mm`, name]}
                    />
                    <Legend wrapperStyle={{ color: '#cbd5e1' }} />
                    <Bar dataKey="rmse" name="RMSE (mm)" radius={[6, 6, 0, 0]}>
                      {comparisonData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Bar>
                    <Bar dataKey="mae" name="MAE (mm)" fill="#3b82f6" radius={[6, 6, 0, 0]} opacity={0.65} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Exact Benchmark Table */}
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8' }}>
                      <th style={{ padding: '10px 12px' }}>Forecasting Strategy</th>
                      <th style={{ padding: '10px 12px' }}>Category</th>
                      <th style={{ padding: '10px 12px' }}>RMSE (mm)</th>
                      <th style={{ padding: '10px 12px' }}>MAE (mm)</th>
                      <th style={{ padding: '10px 12px' }}>Signed Bias (mm)</th>
                      <th style={{ padding: '10px 12px' }}>RMSE Imprv vs Naive</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparisonData.map((row) => (
                      <tr
                        key={row.strategy}
                        style={{
                          borderBottom: '1px solid #1e293b',
                          background: row.strategy.includes('VaruNet') ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                          fontWeight: row.strategy.includes('VaruNet') ? 700 : 400,
                        }}
                      >
                        <td style={{ padding: '12px', color: row.fill }}>{row.strategy}</td>
                        <td style={{ padding: '12px', color: '#94a3b8' }}>{row.category}</td>
                        <td style={{ padding: '12px' }}>{row.rmse.toFixed(3)}</td>
                        <td style={{ padding: '12px' }}>{row.mae.toFixed(3)}</td>
                        <td style={{ padding: '12px' }}>{row.bias > 0 ? `+${row.bias.toFixed(3)}` : row.bias.toFixed(3)}</td>
                        <td style={{
                          padding: '12px',
                          color: row.rmse_improvement > 0 ? '#22c55e' : (row.rmse_improvement < 0 ? '#f87171' : '#94a3b8'),
                        }}>
                          {row.rmse_improvement > 0 ? `+${row.rmse_improvement.toFixed(2)}%` : (row.rmse_improvement < 0 ? `${row.rmse_improvement.toFixed(2)}%` : 'Baseline (0%)')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 2. Skill Score Evolution Over Time */}
          {activeTab === 'evolution' && (
            <div>
              <div style={{ marginBottom: '16px', fontSize: '13px', color: '#cbd5e1' }}>
                Tracking historical verification RMSE across verification cycles. Notice consistent error suppression by the VaruNet blend.
              </div>

              <div style={{ height: '340px', width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={evolutionData} margin={{ top: 15, right: 30, left: 10, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="cycle" stroke="#94a3b8" tick={{ fill: '#cbd5e1', fontSize: 11 }} />
                    <YAxis stroke="#94a3b8" domain={[3.0, 6.5]} tick={{ fill: '#cbd5e1', fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{ background: '#0f172a', borderColor: '#475569', borderRadius: '8px', color: '#f8fafc' }}
                      formatter={(val: any, name: any) => [`${Number(val).toFixed(2)} mm`, name]}
                    />
                    <Legend wrapperStyle={{ color: '#cbd5e1' }} />
                    <Line type="monotone" dataKey="nwp_rmse" name="Source 1 (NWP Physics)" stroke="#38bdf8" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="aiml_rmse" name="Source 2 (AI/ML Model)" stroke="#a855f7" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="ensemble_rmse" name="Source 3 (Ensemble Average)" stroke="#f97316" strokeWidth={2} dot={{ r: 3 }} />
                    <Line type="monotone" dataKey="blend_rmse" name="VaruNet Blended Model" stroke="#6366f1" strokeWidth={3.5} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* 3. Disagreement Heatmap */}
          {activeTab === 'disagreement' && (
            <div>
              <div style={{ marginBottom: '16px', fontSize: '13px', color: '#cbd5e1' }}>
                Spatial-temporal variance matrix: Identifies where NWP, AI/ML, and Ensemble models sharply diverge in forecasted intensity.
              </div>

              {/* Heatmap Legend */}
              <div style={{ display: 'flex', gap: '16px', marginBottom: '16px', fontSize: '12px', alignItems: 'center' }}>
                <span style={{ color: '#94a3b8' }}>Variance Scale:</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ width: '12px', height: '12px', background: '#0284c7', borderRadius: '2px' }} /> Low (&lt;3)
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ width: '12px', height: '12px', background: '#0d9488', borderRadius: '2px' }} /> Moderate (3–6)
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ width: '12px', height: '12px', background: '#d97706', borderRadius: '2px' }} /> High (6–12)
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ width: '12px', height: '12px', background: '#dc2626', borderRadius: '2px' }} /> Very High (12–18)
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ width: '12px', height: '12px', background: '#991b1b', borderRadius: '2px' }} /> Severe (&gt;18)
                </span>
              </div>

              {/* Interactive Heatmap Matrix Grid */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: '220px repeat(4, 1fr)',
                gap: '8px',
                background: '#0f172a',
                padding: '16px',
                borderRadius: '12px',
              }}>
                {/* Header Row */}
                <div style={{ fontWeight: 700, fontSize: '12px', color: '#94a3b8', padding: '8px' }}>
                  GEOGRAPHIC REGION
                </div>
                {leadTimes.map((lt) => (
                  <div key={lt} style={{ fontWeight: 700, fontSize: '12px', color: '#94a3b8', textAlign: 'center', padding: '8px' }}>
                    {lt} HORIZON
                  </div>
                ))}

                {/* Matrix Rows */}
                {regions.map((reg) => (
                  <React.Fragment key={reg}>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: '#f8fafc', padding: '12px 8px', display: 'flex', alignItems: 'center' }}>
                      {reg}
                    </div>
                    {leadTimes.map((lt) => {
                      const item = disagreementData.find((d) => d.region === reg && d.lead_time === lt);
                      const variance = item ? item.variance : 0;
                      const spread = item ? item.spread : 0;
                      const intensity = item ? item.intensity : 'N/A';
                      const cellColor = getHeatmapColor(variance);

                      return (
                        <div
                          key={`${reg}-${lt}`}
                          style={{
                            background: cellColor,
                            borderRadius: '8px',
                            padding: '14px',
                            textAlign: 'center',
                            color: '#ffffff',
                            boxShadow: '0 2px 6px rgba(0, 0, 0, 0.2)',
                            transition: 'transform 0.15s',
                            cursor: 'pointer',
                          }}
                          title={`${reg} (${lt}): Variance=${variance}, Spread=${spread}mm (${intensity})`}
                        >
                          <div style={{ fontSize: '16px', fontWeight: 800 }}>{variance.toFixed(1)}</div>
                          <div style={{ fontSize: '11px', opacity: 0.9 }}>Spread: ±{spread.toFixed(1)}</div>
                          <div style={{ fontSize: '10px', marginTop: '2px', fontWeight: 600, textTransform: 'uppercase' }}>
                            {intensity}
                          </div>
                        </div>
                      );
                    })}
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
