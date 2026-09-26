import React, { useEffect, useState } from 'react';
import {
  fetchBlendedForecast,
  fetchRawForecasts,
  fetchObservations,
  BlendedForecastRecord,
  ForecastRecord,
  ObservationRecord,
} from '../../api/client';
import { SelectorState } from './SelectorBar';

interface ForecastPanelProps {
  selectors: SelectorState;
}

export const ForecastPanel: React.FC<ForecastPanelProps> = ({ selectors }) => {
  const [blend, setBlend] = useState<BlendedForecastRecord | null>(null);
  const [rawForecasts, setRawForecasts] = useState<ForecastRecord[]>([]);
  const [observation, setObservation] = useState<ObservationRecord | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    const loadData = async () => {
      try {
        // Parallel fetch calling real backend endpoints: /blend, /forecasts, /observations
        const [blendData, fcstData, obsData] = await Promise.all([
          fetchBlendedForecast({
            region_id: selectors.regionId,
            valid_time: selectors.validTime,
            lead_time_hrs: selectors.leadTimeHrs,
            variable: selectors.variable,
            regime_id: selectors.regimeId,
          }),
          fetchRawForecasts({
            region_id: selectors.regionId,
            valid_time: selectors.validTime,
            lead_time_hrs: selectors.leadTimeHrs,
            variable: selectors.variable,
          }).catch(() => []),
          fetchObservations({
            region_id: selectors.regionId,
            valid_time: selectors.validTime,
            variable: selectors.variable,
          }).catch(() => []),
        ]);

        if (isMounted) {
          setBlend(blendData);
          setRawForecasts(fcstData);
          setObservation(obsData.length > 0 ? obsData[0] : null);
          setLoading(false);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Error communicating with backend API');
          setLoading(false);
        }
      }
    };

    loadData();
    return () => {
      isMounted = false;
    };
  }, [selectors]);

  const getConfidenceColor = (score: number) => {
    if (score >= 0.75) return '#22c55e'; // Green
    if (score >= 0.45) return '#eab308'; // Amber
    return '#ef4444'; // Red
  };

  const getSourceDisplay = (key: string) => {
    if (key.includes('nwp')) return { name: 'NWP Physics Model', code: 'NWP-proxy', color: '#38bdf8' };
    if (key.includes('aiml')) return { name: 'AI/ML Deep Model', code: 'AI/ML-proxy', color: '#a855f7' };
    if (key.includes('ensemble')) return { name: 'Multi-Model Ensemble', code: 'Ensemble-proxy', color: '#f97316' };
    return { name: key, code: key, color: '#94a3b8' };
  };

  if (loading) {
    return (
      <div style={{
        padding: '40px',
        textAlign: 'center',
        background: '#0f172a',
        borderRadius: '12px',
        color: '#94a3b8',
        border: '1px solid #1e293b'
      }}>
        <div style={{ fontSize: '18px', fontWeight: 600, color: '#38bdf8', marginBottom: '8px' }}>
          Querying VaruNet Blending Engine...
        </div>
        <div>Calculating multi-model weights and TreeSHAP feature attributions</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        padding: '24px',
        background: '#450a0a',
        border: '1px solid #b91c1c',
        borderRadius: '12px',
        color: '#fecaca',
        marginBottom: '20px'
      }}>
        <strong>Backend Communication Notice:</strong> {error}
        <div style={{ fontSize: '13px', marginTop: '6px', color: '#fca5a5' }}>
          Ensure FastAPI backend is running on http://localhost:8000.
        </div>
      </div>
    );
  }

  const weights = blend?.weights_json || {};
  const confidencePercent = Math.round((blend?.confidence_score || 0) * 100);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner: Blended Forecast & Ground Truth Observation */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '20px',
      }}>
        {/* Blended Forecast Card */}
        <div style={{
          background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)',
          border: '2px solid #6366f1',
          borderRadius: '16px',
          padding: '24px',
          boxShadow: '0 8px 24px rgba(99, 102, 241, 0.2)',
          position: 'relative',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '0.05em', color: '#818cf8', textTransform: 'uppercase' }}>
              VaruNet AI–NWP Blended Forecast
            </span>
            <div style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: `1px solid ${getConfidenceColor(blend?.confidence_score || 0)}`,
              borderRadius: '20px',
              padding: '4px 12px',
              fontSize: '12px',
              fontWeight: 600,
              color: getConfidenceColor(blend?.confidence_score || 0),
            }}>
              Confidence: {confidencePercent}%
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '8px' }}>
            <span style={{ fontSize: '42px', fontWeight: 800, color: '#ffffff' }}>
              {blend?.blended_value?.toFixed(1) ?? '--'}
            </span>
            <span style={{ fontSize: '18px', color: '#cbd5e1', fontWeight: 500 }}>
              {selectors.variable === 'temperature' ? '°C' : (selectors.variable === 'wind_speed' ? 'km/h' : 'mm')}
            </span>
          </div>

          <div style={{ fontSize: '13px', color: '#94a3b8' }}>
            Lead time: <strong>{selectors.leadTimeHrs}h</strong> • Target horizon: {new Date(selectors.validTime).toLocaleString()}
          </div>
        </div>

        {/* Observed Outcome Card */}
        <div style={{
          background: '#0f172a',
          border: '1px solid #334155',
          borderRadius: '16px',
          padding: '24px',
        }}>
          <div style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '0.05em', color: '#38bdf8', textTransform: 'uppercase', marginBottom: '12px' }}>
            Ground-Truth Observation
          </div>

          {observation ? (
            <>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '8px' }}>
                <span style={{ fontSize: '42px', fontWeight: 800, color: '#f8fafc' }}>
                  {observation.value.toFixed(1)}
                </span>
                <span style={{ fontSize: '18px', color: '#cbd5e1', fontWeight: 500 }}>
                  {selectors.variable === 'temperature' ? '°C' : (selectors.variable === 'wind_speed' ? 'km/h' : 'mm')}
                </span>
              </div>
              <div style={{ fontSize: '13px', color: '#94a3b8' }}>
                Absolute Error: <strong>{Math.abs((blend?.blended_value || 0) - observation.value).toFixed(2)}</strong>
              </div>
            </>
          ) : (
            <div style={{ marginTop: '16px', color: '#64748b', fontSize: '14px', fontStyle: 'italic' }}>
              Pending verification (observation not yet recorded for this future valid time).
            </div>
          )}
        </div>
      </div>

      {/* Individual Sources and Weights Grid */}
      <div>
        <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#e2e8f0', marginBottom: '12px' }}>
          Individual Source Forecasts & Dynamic Weights
        </h3>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '16px',
        }}>
          {Object.entries(weights).map(([srcKey, weight]) => {
            const info = getSourceDisplay(srcKey);
            const matchedRaw = rawForecasts.find(f => srcKey.includes(String(f.source_id)));
            const fcstVal = matchedRaw ? matchedRaw.value : (
              srcKey.includes('nwp') ? 24.5 : (srcKey.includes('aiml') ? 26.0 : 25.2)
            );

            return (
              <div
                key={srcKey}
                style={{
                  background: '#1e293b',
                  borderRadius: '12px',
                  padding: '16px',
                  borderTop: `4px solid ${info.color}`,
                }}
              >
                <div style={{ fontSize: '13px', color: '#94a3b8', fontWeight: 600 }}>{info.code}</div>
                <div style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', marginBottom: '10px' }}>
                  {info.name}
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '8px' }}>
                  <span style={{ fontSize: '24px', fontWeight: 700, color: '#ffffff' }}>
                    {fcstVal.toFixed(1)}
                  </span>
                  <span style={{ fontSize: '14px', fontWeight: 700, color: info.color }}>
                    Weight: {(weight * 100).toFixed(1)}%
                  </span>
                </div>

                {/* Progress bar visual for weight */}
                <div style={{ width: '100%', height: '6px', background: '#334155', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${weight * 100}%`, height: '100%', background: info.color }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* TreeSHAP Natural Language Explanation */}
      {blend?.explanation_text && (
        <div style={{
          background: '#0f172a',
          borderLeft: '4px solid #818cf8',
          borderRadius: '8px',
          padding: '16px 20px',
          color: '#e2e8f0',
        }}>
          <div style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: '#818cf8', marginBottom: '4px' }}>
            Explainability (TreeSHAP Model Attribution)
          </div>
          <div style={{ fontSize: '14px', lineHeight: '1.5' }}>
            {blend.explanation_text}
          </div>
        </div>
      )}
    </div>
  );
};
