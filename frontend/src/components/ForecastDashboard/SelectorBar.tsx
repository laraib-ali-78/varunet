import React from 'react';

export interface SelectorState {
  regionId: number;
  validTime: string;
  leadTimeHrs: number;
  variable: string;
  regimeId: number;
}

interface SelectorBarProps {
  selectors: SelectorState;
  onChange: (updated: Partial<SelectorState>) => void;
  onRefresh?: () => void;
  isLoading?: boolean;
}

export const REGIONS = [
  { id: 1, name: 'Region 1 - Coastal Basin (Kerala / Konkan)' },
  { id: 2, name: 'Region 2 - Central Plateau (Deccan Belt)' },
  { id: 3, name: 'Region 3 - Northwest Plains (Gangetic Valley)' },
];

export const LEAD_TIMES = [
  { hours: 24, label: '24 Hours (Day 1)' },
  { hours: 48, label: '48 Hours (Day 2)' },
  { hours: 72, label: '72 Hours (Day 3)' },
  { hours: 120, label: '120 Hours (Medium Range)' },
];

export const VARIABLES = [
  { id: 'rainfall', label: 'Rainfall (mm)' },
  { id: 'temperature', label: 'Temperature (°C)' },
  { id: 'wind_speed', label: 'Wind Speed (km/h)' },
];

export const SelectorBar: React.FC<SelectorBarProps> = ({
  selectors,
  onChange,
  onRefresh,
  isLoading,
}) => {
  return (
    <div style={{
      background: '#1e293b',
      padding: '16px 20px',
      borderRadius: '12px',
      color: '#f8fafc',
      display: 'flex',
      flexWrap: 'wrap',
      gap: '16px',
      alignItems: 'flex-end',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.25)',
      marginBottom: '20px',
    }}>
      {/* Region Selector */}
      <div style={{ flex: '1 1 240px', minWidth: '220px' }}>
        <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#94a3b8', marginBottom: '6px' }}>
          GEOGRAPHIC REGION
        </label>
        <select
          value={selectors.regionId}
          onChange={(e) => onChange({ regionId: Number(e.target.value) })}
          style={{
            width: '100%',
            padding: '10px 12px',
            background: '#0f172a',
            border: '1px solid #334155',
            borderRadius: '8px',
            color: '#f8fafc',
            fontSize: '14px',
            outline: 'none',
          }}
        >
          {REGIONS.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </div>

      {/* Date & Time Selector */}
      <div style={{ flex: '1 1 180px', minWidth: '180px' }}>
        <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#94a3b8', marginBottom: '6px' }}>
          VALID DATE & TIME
        </label>
        <input
          type="datetime-local"
          value={selectors.validTime.slice(0, 16)}
          onChange={(e) => onChange({ validTime: e.target.value ? new Date(e.target.value).toISOString() : selectors.validTime })}
          style={{
            width: '100%',
            padding: '9px 12px',
            background: '#0f172a',
            border: '1px solid #334155',
            borderRadius: '8px',
            color: '#f8fafc',
            fontSize: '14px',
            outline: 'none',
          }}
        />
      </div>

      {/* Lead Time Selector */}
      <div style={{ flex: '1 1 180px', minWidth: '160px' }}>
        <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#94a3b8', marginBottom: '6px' }}>
          LEAD TIME
        </label>
        <select
          value={selectors.leadTimeHrs}
          onChange={(e) => onChange({ leadTimeHrs: Number(e.target.value) })}
          style={{
            width: '100%',
            padding: '10px 12px',
            background: '#0f172a',
            border: '1px solid #334155',
            borderRadius: '8px',
            color: '#f8fafc',
            fontSize: '14px',
            outline: 'none',
          }}
        >
          {LEAD_TIMES.map((lt) => (
            <option key={lt.hours} value={lt.hours}>
              {lt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Variable Selector */}
      <div style={{ flex: '1 1 160px', minWidth: '150px' }}>
        <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#94a3b8', marginBottom: '6px' }}>
          WEATHER VARIABLE
        </label>
        <select
          value={selectors.variable}
          onChange={(e) => onChange({ variable: e.target.value })}
          style={{
            width: '100%',
            padding: '10px 12px',
            background: '#0f172a',
            border: '1px solid #334155',
            borderRadius: '8px',
            color: '#f8fafc',
            fontSize: '14px',
            outline: 'none',
          }}
        >
          {VARIABLES.map((v) => (
            <option key={v.id} value={v.id}>
              {v.label}
            </option>
          ))}
        </select>
      </div>

      {/* Refresh Button */}
      {onRefresh && (
        <button
          onClick={onRefresh}
          disabled={isLoading}
          style={{
            padding: '10px 20px',
            background: isLoading ? '#475569' : '#0284c7',
            border: 'none',
            borderRadius: '8px',
            color: '#ffffff',
            fontWeight: 600,
            cursor: isLoading ? 'not-allowed' : 'pointer',
            fontSize: '14px',
            transition: 'background 0.2s',
          }}
        >
          {isLoading ? 'Computing Blend...' : 'Refresh Forecast'}
        </button>
      )}
    </div>
  );
};
