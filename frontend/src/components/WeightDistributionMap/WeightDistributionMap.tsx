import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Polygon, Tooltip, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { fetchBlendedForecast, BlendedForecastRecord } from '../../api/client';
import { SelectorState } from '../ForecastDashboard/SelectorBar';

interface WeightDistributionMapProps {
  selectors: SelectorState;
  onSelectRegion?: (regionId: number) => void;
}

interface RegionGeoData {
  id: number;
  name: string;
  center: [number, number];
  polygon: [number, number][];
}

// Geographic polygon boundaries for India's meteorological regions (EPSG:4326)
const REGION_GEOMETRIES: RegionGeoData[] = [
  {
    id: 1,
    name: 'Region 1 - Coastal Basin (Kerala & Konkan)',
    center: [12.5, 75.5],
    polygon: [
      [8.3, 76.9],
      [10.0, 76.2],
      [12.5, 75.0],
      [15.5, 73.7],
      [18.9, 72.8],
      [19.2, 73.5],
      [16.0, 74.5],
      [13.0, 75.8],
      [10.5, 76.9],
      [8.5, 77.5],
      [8.3, 76.9],
    ],
  },
  {
    id: 2,
    name: 'Region 2 - Central Plateau (Deccan Belt)',
    center: [18.0, 78.5],
    polygon: [
      [15.0, 74.8],
      [19.0, 73.5],
      [21.5, 76.0],
      [21.8, 80.5],
      [19.5, 82.0],
      [16.5, 81.0],
      [14.0, 78.5],
      [15.0, 74.8],
    ],
  },
  {
    id: 3,
    name: 'Region 3 - Northwest Plains (Gangetic & Indus Valley)',
    center: [28.5, 76.0],
    polygon: [
      [24.5, 72.0],
      [28.0, 70.5],
      [31.5, 74.0],
      [31.2, 77.5],
      [28.5, 79.5],
      [25.5, 79.0],
      [24.5, 75.0],
      [24.5, 72.0],
    ],
  },
];

const SOURCE_COLORS: Record<string, string> = {
  fcst_nwp: '#38bdf8',       // Cyan / Light Blue for NWP Physics
  fcst_aiml: '#a855f7',      // Purple for Deep AI/ML
  fcst_ensemble: '#f97316',  // Orange for Multi-Model Ensemble
  balanced: '#6366f1',       // Indigo for Balanced Consensus
};

const SOURCE_LABELS: Record<string, string> = {
  fcst_nwp: 'NWP-proxy (Numerical Weather Prediction)',
  fcst_aiml: 'AI/ML-proxy (Deep ML Model)',
  fcst_ensemble: 'Ensemble-proxy (Multi-Model Average)',
  balanced: 'Balanced Ensemble Consensus',
};

// Component to adjust map bounds when selected region changes
const MapRecenter: React.FC<{ center: [number, number] }> = ({ center }) => {
  const map = useMap();
  useEffect(() => {
    map.setView(center, map.getZoom());
  }, [center, map]);
  return null;
};

export const WeightDistributionMap: React.FC<WeightDistributionMapProps> = ({
  selectors,
  onSelectRegion,
}) => {
  const [regionBlends, setRegionBlends] = useState<Record<number, BlendedForecastRecord>>({});
  const [clickedRegionId, setClickedRegionId] = useState<number | null>(selectors.regionId);
  const [loading, setLoading] = useState<boolean>(true);

  // 3. Live update when selector (time/lead-time/variable) changes
  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    const fetchAllRegions = async () => {
      try {
        const promises = REGION_GEOMETRIES.map((r) =>
          fetchBlendedForecast({
            region_id: r.id,
            valid_time: selectors.validTime,
            lead_time_hrs: selectors.leadTimeHrs,
            variable: selectors.variable,
            regime_id: selectors.regimeId,
          }).then((res) => ({ id: r.id, data: res }))
        );

        const results = await Promise.all(promises);
        if (isMounted) {
          const map: Record<number, BlendedForecastRecord> = {};
          results.forEach((item) => {
            map[item.id] = item.data;
          });
          setRegionBlends(map);
          setLoading(false);
        }
      } catch (err) {
        console.error('Error fetching regional weight distributions:', err);
        if (isMounted) setLoading(false);
      }
    };

    fetchAllRegions();
    return () => {
      isMounted = false;
    };
  }, [selectors.validTime, selectors.leadTimeHrs, selectors.variable, selectors.regimeId]);

  // Keep clicked region in sync with selector's active region
  useEffect(() => {
    setClickedRegionId(selectors.regionId);
  }, [selectors.regionId]);

  // Determine winning forecast source for a region
  const getWinningSource = (weights: Record<string, number> = {}) => {
    const entries = Object.entries(weights);
    if (!entries.length) return { key: 'balanced', weight: 0.33, color: SOURCE_COLORS.balanced };

    entries.sort((a, b) => b[1] - a[1]);
    const top = entries[0];
    const second = entries[1] || ['', 0];

    // If difference < 0.05, treat as balanced consensus
    if (top[1] - second[1] < 0.05) {
      return { key: 'balanced', weight: top[1], color: SOURCE_COLORS.balanced };
    }

    return {
      key: top[0],
      weight: top[1],
      color: SOURCE_COLORS[top[0]] || SOURCE_COLORS.balanced,
    };
  };

  const activeRegionData = clickedRegionId ? regionBlends[clickedRegionId] : null;
  const activeRegionGeo = REGION_GEOMETRIES.find((r) => r.id === clickedRegionId);

  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '16px',
      padding: '24px',
      color: '#f8fafc',
      boxShadow: '0 4px 16px rgba(0, 0, 0, 0.25)',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px',
    }}>
      {/* Header & Legend */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0, color: '#ffffff' }}>
            Geospatial Blend Weight Distribution Map
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
            Interactive regional coverage shaded by dominant forecasting model (Leaflet GIS)
          </p>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', background: '#0f172a', padding: '8px 16px', borderRadius: '8px', fontSize: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: SOURCE_COLORS.fcst_nwp }} />
            <span>NWP Physics Dominant</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: SOURCE_COLORS.fcst_aiml }} />
            <span>AI/ML Dominant</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: SOURCE_COLORS.fcst_ensemble }} />
            <span>Ensemble Dominant</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: SOURCE_COLORS.balanced }} />
            <span>Balanced Consensus</span>
          </div>
        </div>
      </div>

      {/* Main Container: Map + Detail Panel */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(400px, 2fr) minmax(320px, 1fr)', gap: '20px' }}>
        {/* Leaflet Map Container */}
        <div style={{
          height: '480px',
          borderRadius: '12px',
          overflow: 'hidden',
          border: '1px solid #334155',
          position: 'relative',
        }}>
          {loading && (
            <div style={{
              position: 'absolute',
              top: 10,
              right: 10,
              zIndex: 1000,
              background: 'rgba(15, 23, 42, 0.9)',
              color: '#38bdf8',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: 600,
            }}>
              Updating Regional Weights...
            </div>
          )}

          <MapContainer
            center={[20.5937, 78.9629]} // Center of India
            zoom={5}
            style={{ height: '100%', width: '100%', background: '#090d16' }}
            scrollWheelZoom={false}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {/* Render Region Polygons */}
            {REGION_GEOMETRIES.map((reg) => {
              const blend = regionBlends[reg.id];
              const winner = getWinningSource(blend?.weights_json);
              const isSelected = clickedRegionId === reg.id;

              return (
                <Polygon
                  key={reg.id}
                  positions={reg.polygon}
                  pathOptions={{
                    color: isSelected ? '#ffffff' : winner.color,
                    weight: isSelected ? 3 : 2,
                    fillColor: winner.color,
                    fillOpacity: isSelected ? 0.65 : 0.45,
                  }}
                  eventHandlers={{
                    click: () => {
                      setClickedRegionId(reg.id);
                      if (onSelectRegion) onSelectRegion(reg.id);
                    },
                  }}
                >
                  <Tooltip sticky direction="top">
                    <div style={{ padding: '4px', fontSize: '12px' }}>
                      <strong>{reg.name}</strong>
                      <br />
                      Primary Model: <strong>{SOURCE_LABELS[winner.key] || winner.key}</strong>
                      <br />
                      Top Weight: {(winner.weight * 100).toFixed(1)}%
                    </div>
                  </Tooltip>
                </Polygon>
              );
            })}

            {activeRegionGeo && <MapRecenter center={activeRegionGeo.center} />}
          </MapContainer>
        </div>

        {/* 2. On-Click Region Weight Vector & SHAP Explanation Panel */}
        <div style={{
          background: '#0f172a',
          borderRadius: '12px',
          border: '1px solid #334155',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}>
          {activeRegionGeo && activeRegionData ? (
            <>
              <div>
                <div style={{ fontSize: '11px', fontWeight: 700, color: '#818cf8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Selected Geographic Region
                </div>
                <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#ffffff', margin: '4px 0 0 0' }}>
                  {activeRegionGeo.name}
                </h3>
              </div>

              {/* Blended Value & Confidence */}
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: '#1e293b',
                padding: '12px 16px',
                borderRadius: '8px',
              }}>
                <div>
                  <div style={{ fontSize: '12px', color: '#94a3b8' }}>Blended Value</div>
                  <div style={{ fontSize: '24px', fontWeight: 800, color: '#ffffff' }}>
                    {activeRegionData.blended_value.toFixed(1)} {selectors.variable === 'rainfall' ? 'mm' : ''}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '12px', color: '#94a3b8' }}>Confidence</div>
                  <div style={{
                    fontSize: '18px',
                    fontWeight: 700,
                    color: activeRegionData.confidence_score >= 0.7 ? '#22c55e' : (activeRegionData.confidence_score >= 0.4 ? '#eab308' : '#ef4444')
                  }}>
                    {Math.round(activeRegionData.confidence_score * 100)}%
                  </div>
                </div>
              </div>

              {/* Exact Weight Vector */}
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#cbd5e1', marginBottom: '8px' }}>
                  Exact Blend Weight Vector (Σw = 1.0)
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {Object.entries(activeRegionData.weights_json).map(([src, w]) => {
                    const color = SOURCE_COLORS[src] || '#94a3b8';
                    const name = SOURCE_LABELS[src] || src;
                    return (
                      <div key={src} style={{ background: '#1e293b', padding: '10px 12px', borderRadius: '6px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                          <span style={{ color: '#e2e8f0', fontWeight: 500 }}>{name}</span>
                          <span style={{ color, fontWeight: 700 }}>{(w * 100).toFixed(1)}%</span>
                        </div>
                        <div style={{ width: '100%', height: '5px', background: '#334155', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ width: `${w * 100}%`, height: '100%', background: color }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Natural Language Explanation Text from TreeSHAP */}
              {activeRegionData.explanation_text && (
                <div style={{
                  background: 'rgba(99, 102, 241, 0.08)',
                  borderLeft: '4px solid #6366f1',
                  borderRadius: '6px',
                  padding: '12px',
                  fontSize: '13px',
                  lineHeight: '1.45',
                  color: '#e2e8f0',
                }}>
                  <strong style={{ color: '#818cf8', display: 'block', marginBottom: '4px', fontSize: '11px', textTransform: 'uppercase' }}>
                    TreeSHAP Reason
                  </strong>
                  {activeRegionData.explanation_text}
                </div>
              )}
            </>
          ) : (
            <div style={{ padding: '40px 20px', textAlign: 'center', color: '#64748b' }}>
              Click on any region on the map to inspect its exact weight vector and TreeSHAP attribution.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
