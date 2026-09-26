import React, { useEffect, useState } from 'react';
import { fetchBlendedForecast, fetchCitizenAlerts, BlendedForecastRecord, AlertRecord } from '../../api/client';

export interface CityOption {
  name: string;
  state: string;
  regionId: number;
}

export const CITIES: CityOption[] = [
  { name: 'Kochi', state: 'Kerala', regionId: 1 },
  { name: 'Mumbai', state: 'Maharashtra', regionId: 1 },
  { name: 'Hyderabad', state: 'Telangana', regionId: 2 },
  { name: 'Pune', state: 'Maharashtra', regionId: 2 },
  { name: 'Delhi NCR', state: 'National Capital Region', regionId: 3 },
  { name: 'Chandigarh', state: 'Punjab / Haryana', regionId: 3 },
];

export const CitizenPortal: React.FC = () => {
  const [selectedCity, setSelectedCity] = useState<CityOption>(CITIES[0]);
  const [blend, setBlend] = useState<BlendedForecastRecord | null>(null);
  const [activeAlert, setActiveAlert] = useState<AlertRecord | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    const nowIso = new Date().toISOString();

    Promise.all([
      // 1. Plain-language forecast from /blend endpoint
      fetchBlendedForecast({
        region_id: selectedCity.regionId,
        valid_time: nowIso,
        lead_time_hrs: 24,
        variable: 'rainfall',
      }),
      // 3. Active public-safety advisory from /alerts/citizen endpoint (public)
      fetchCitizenAlerts({
        region_id: selectedCity.regionId,
      }).catch(() => []),
    ])
      .then(([blendData, alertsData]) => {
        if (isMounted) {
          setBlend(blendData);
          // Find most severe active alert if any
          if (alertsData && alertsData.length > 0) {
            setActiveAlert(alertsData[0]);
          } else {
            setActiveAlert(null);
          }
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Unable to load weather information.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedCity]);

  // 2. Simple confidence indicator using words, NOT numbers
  const getPlainLanguageConfidence = (score: number) => {
    if (score >= 0.70) {
      return {
        label: 'High Confidence',
        description: 'Atmospheric prediction models are in strong consensus.',
        badgeColor: '#15803d',
        bgColor: '#f0fdf4',
        textColor: '#166534',
        icon: '✓',
      };
    } else if (score >= 0.40) {
      return {
        label: 'Moderate Confidence',
        description: 'Slight timing variation in passing weather systems.',
        badgeColor: '#b45309',
        bgColor: '#fffbeb',
        textColor: '#92400e',
        icon: 'ℹ',
      };
    } else {
      return {
        label: 'Some Uncertainty',
        description: 'Forecast models show divergent weather scenarios. Check for updates.',
        badgeColor: '#b91c1c',
        bgColor: '#fef2f2',
        textColor: '#991b1b',
        icon: '⚠',
      };
    }
  };

  // 1. Plain-language forecast translation
  const getPlainLanguageSummary = (rainfallMm: number) => {
    if (rainfallMm < 2.5) {
      return {
        headline: 'Mostly Dry & Clear',
        detail: 'Expect dry weather with pleasant conditions. No rain gear needed today.',
        icon: '☀️',
      };
    } else if (rainfallMm < 15.5) {
      return {
        headline: 'Light Passing Showers',
        detail: 'Occasional light drizzles during the day. An umbrella is handy for outdoor plans.',
        icon: '🌦️',
      };
    } else if (rainfallMm < 64.5) {
      return {
        headline: 'Moderate Rainfall',
        detail: 'Steady rain showers expected. Roads may be slick; plan for normal travel delays.',
        icon: '🌧️',
      };
    } else if (rainfallMm < 115.5) {
      return {
        headline: 'Heavy Rainfall Expected',
        detail: 'Substantial continuous rain. Expect localized waterlogging on typical low-lying routes.',
        icon: '⛈️',
      };
    } else {
      return {
        headline: 'Torrential Downpours',
        detail: 'Extreme downpours likely to cause severe waterlogging and transit disruption. Limit travel.',
        icon: '🌊',
      };
    }
  };

  // 3. Extract public safety sentence
  const getPublicSafetySentence = (alertText?: string) => {
    if (!alertText) {
      return 'No active weather hazard warnings for your city today. Normal conditions prevail.';
    }
    const pubMatch = alertText.match(/Public Safety:\s*(.*?)(?:Agriculture:|Aviation:|$)/i);
    if (pubMatch && pubMatch[1].trim()) {
      return pubMatch[1].trim();
    }
    return alertText;
  };

  const confidence = getPlainLanguageConfidence(blend?.confidence_score ?? 0.8);
  const summary = getPlainLanguageSummary(blend?.blended_value ?? 12.0);
  const publicSafetySentence = getPublicSafetySentence(activeAlert?.sector_guidance_text);

  return (
    <div style={{
      maxWidth: '640px',
      margin: '0 auto',
      padding: '32px 20px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
      color: '#1e293b',
    }}>
      {/* Brand Header */}
      <div style={{ textAlign: 'center', marginBottom: '28px' }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          background: '#e0e7ff',
          color: '#4338ca',
          padding: '4px 14px',
          borderRadius: '20px',
          fontSize: '12px',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          marginBottom: '8px',
        }}>
          Citizen Weather Service
        </div>
        <h1 style={{ fontSize: '28px', fontWeight: 800, margin: 0, color: '#0f172a' }}>
          VaruNet Weather Portal
        </h1>
        <p style={{ margin: '6px 0 0 0', fontSize: '15px', color: '#64748b' }}>
          Reliable multi-model weather forecasts and public safety updates for your city
        </p>
      </div>

      {/* City Selector */}
      <div style={{
        background: '#ffffff',
        borderRadius: '16px',
        padding: '20px 24px',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.06)',
        border: '1px solid #e2e8f0',
        marginBottom: '20px',
      }}>
        <label style={{ display: 'block', fontSize: '13px', fontWeight: 700, color: '#475569', marginBottom: '8px', textTransform: 'uppercase' }}>
          Select Your City
        </label>
        <select
          value={selectedCity.name}
          onChange={(e) => {
            const found = CITIES.find((c) => c.name === e.target.value);
            if (found) setSelectedCity(found);
          }}
          style={{
            width: '100%',
            padding: '12px 16px',
            fontSize: '16px',
            fontWeight: 600,
            borderRadius: '10px',
            border: '2px solid #cbd5e1',
            background: '#f8fafc',
            color: '#0f172a',
            outline: 'none',
            cursor: 'pointer',
          }}
        >
          {CITIES.map((c) => (
            <option key={c.name} value={c.name}>
              {c.name}, {c.state}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div style={{
          background: '#ffffff',
          borderRadius: '16px',
          padding: '48px 24px',
          textAlign: 'center',
          color: '#64748b',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.06)',
        }}>
          <div style={{ fontSize: '24px', marginBottom: '8px' }}>🌦️</div>
          <div style={{ fontSize: '16px', fontWeight: 600, color: '#0f172a' }}>Checking weather models for {selectedCity.name}...</div>
        </div>
      ) : error ? (
        <div style={{
          background: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '12px',
          padding: '16px 20px',
          color: '#991b1b',
        }}>
          {error}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Main Weather Card */}
          <div style={{
            background: 'linear-gradient(145deg, #ffffff 0%, #f8fafc 100%)',
            borderRadius: '20px',
            padding: '28px 24px',
            boxShadow: '0 6px 24px rgba(0, 0, 0, 0.07)',
            border: '1px solid #e2e8f0',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '54px', marginBottom: '8px' }}>
              {summary.icon}
            </div>

            <h2 style={{ fontSize: '24px', fontWeight: 800, color: '#0f172a', margin: '0 0 8px 0' }}>
              {summary.headline}
            </h2>

            <p style={{ fontSize: '16px', color: '#475569', lineHeight: '1.5', margin: '0 0 20px 0', maxWidth: '480px', marginInline: 'auto' }}>
              {summary.detail}
            </p>

            {/* 2. Plain Language Confidence Indicator */}
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '10px',
              background: confidence.bgColor,
              border: `1.5px solid ${confidence.badgeColor}33`,
              padding: '8px 18px',
              borderRadius: '24px',
              color: confidence.textColor,
            }}>
              <span style={{
                background: confidence.badgeColor,
                color: '#ffffff',
                width: '20px',
                height: '20px',
                borderRadius: '50%',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '12px',
                fontWeight: 700,
              }}>
                {confidence.icon}
              </span>
              <span style={{ fontSize: '14px', fontWeight: 700 }}>
                {confidence.label}
              </span>
            </div>

            <div style={{ fontSize: '13px', color: '#64748b', marginTop: '10px' }}>
              {confidence.description}
            </div>
          </div>

          {/* 3. Active Public Safety Advisory */}
          <div style={{
            background: activeAlert ? '#fff1f2' : '#f0fdf4',
            border: `1.5px solid ${activeAlert ? '#f43f5e' : '#86efac'}`,
            borderRadius: '16px',
            padding: '20px 24px',
            boxShadow: '0 4px 16px rgba(0, 0, 0, 0.04)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ fontSize: '18px' }}>
                {activeAlert ? '🛡️' : '✅'}
              </span>
              <span style={{
                fontSize: '13px',
                fontWeight: 800,
                color: activeAlert ? '#9f1239' : '#166534',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}>
                {activeAlert ? 'Official Public Safety Advisory' : 'Public Safety Status'}
              </span>
            </div>

            <p style={{
              fontSize: '15px',
              fontWeight: 600,
              lineHeight: '1.5',
              color: activeAlert ? '#881337' : '#14532d',
              margin: 0,
            }}>
              {publicSafetySentence}
            </p>
          </div>

          {/* Footer Notice */}
          <div style={{ textAlign: 'center', fontSize: '12px', color: '#94a3b8', paddingTop: '8px' }}>
            Blended forecast updated live from IMD, ECMWF, and AI models via VaruNet.
          </div>
        </div>
      )}
    </div>
  );
};
