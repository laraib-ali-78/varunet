/**
 * VaruNet Frontend API Client
 * Connects directly to FastAPI backend endpoints with JWT authentication support.
 */

const getApiBaseUrl = (): string => {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return 'https://backend-production-538ef.up.railway.app/api';
  }
  return 'http://localhost:8000/api';
};

const API_BASE_URL = getApiBaseUrl();


// Token Management
export const AUTH_TOKEN_KEY = 'varunet_auth_token';
export const AUTH_USER_KEY = 'varunet_auth_user';

export function getAuthToken(): string | null {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(AUTH_TOKEN_KEY, token);
    } else {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      localStorage.removeItem(AUTH_USER_KEY);
    }
  } catch {
    // Ignore storage errors in restricted contexts
  }
}

export function getStoredUser(): { email: string; role: string } | null {
  try {
    const raw = localStorage.getItem(AUTH_USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
  email: string;
}

export async function loginUser(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Authentication failed: ${res.statusText}`);
  }
  const data: LoginResponse = await res.json();
  setAuthToken(data.access_token);
  try {
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify({ email: data.email, role: data.role }));
  } catch {
    // ignore
  }
  return data;
}

export function logoutUser(): void {
  setAuthToken(null);
}

export interface ForecastRecord {
  forecast_id: number;
  source_id: number;
  region_id: number;
  valid_time: string;
  lead_time_hrs: number;
  variable: string;
  value: number;
}

export interface ObservationRecord {
  region_id: number;
  valid_time: string;
  variable: string;
  value: number;
}

export interface BlendedForecastRecord {
  blend_id?: number;
  region_id: number;
  valid_time: string;
  lead_time_hrs: number;
  variable: string;
  blended_value: number;
  weights_json: Record<string, number>;
  confidence_score: number;
  explanation_text?: string;
  feature_attributions?: Record<string, Record<string, number>>;
}

export interface SkillScoreRecord {
  score_id: number;
  source_id: number;
  region_id: number;
  regime_id: number;
  season: string;
  lead_time_bucket: string;
  variable: string;
  rmse?: number | null;
  mae?: number | null;
  bias?: number | null;
  sample_size: number;
  last_updated: string;
}

export interface AlertRecord {
  alert_id: number;
  region_id: number;
  valid_time: string;
  alert_type: string;
  severity: 'Yellow' | 'Orange' | 'Red';
  sector_guidance_text: string;
  triggered_by: number;
}

export async function fetchRawForecasts(params: {
  region_id?: number;
  valid_time?: string;
  lead_time_hrs?: number;
  variable?: string;
}): Promise<ForecastRecord[]> {
  const query = new URLSearchParams();
  if (params.region_id !== undefined) query.append('region_id', params.region_id.toString());
  if (params.valid_time) query.append('valid_time', params.valid_time);
  if (params.lead_time_hrs !== undefined) query.append('lead_time_hrs', params.lead_time_hrs.toString());
  if (params.variable) query.append('variable', params.variable);

  const res = await fetch(`${API_BASE_URL}/forecasts?${query.toString()}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch forecasts: ${res.statusText}`);
  return res.json();
}

export async function fetchObservations(params: {
  region_id?: number;
  valid_time?: string;
  variable?: string;
}): Promise<ObservationRecord[]> {
  const query = new URLSearchParams();
  if (params.region_id !== undefined) query.append('region_id', params.region_id.toString());
  if (params.valid_time) query.append('valid_time', params.valid_time);
  if (params.variable) query.append('variable', params.variable);

  const res = await fetch(`${API_BASE_URL}/observations?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch observations: ${res.statusText}`);
  return res.json();
}

export async function fetchBlendedForecast(params: {
  region_id: number;
  valid_time: string;
  lead_time_hrs: number;
  variable?: string;
  regime_id?: number;
}): Promise<BlendedForecastRecord> {
  const query = new URLSearchParams({
    region_id: params.region_id.toString(),
    valid_time: params.valid_time,
    lead_time_hrs: params.lead_time_hrs.toString(),
    variable: params.variable || 'rainfall',
    regime_id: (params.regime_id || 1).toString(),
  });

  const res = await fetch(`${API_BASE_URL}/blend?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch blended forecast: ${res.statusText}`);
  return res.json();
}

export async function fetchSkillScores(params: {
  source_id?: number;
  region_id?: number;
  regime_id?: number;
  season?: string;
  lead_time_bucket?: string;
  variable?: string;
}): Promise<SkillScoreRecord[]> {
  const query = new URLSearchParams();
  if (params.source_id !== undefined) query.append('source_id', params.source_id.toString());
  if (params.region_id !== undefined) query.append('region_id', params.region_id.toString());
  if (params.regime_id !== undefined) query.append('regime_id', params.regime_id.toString());
  if (params.season) query.append('season', params.season);
  if (params.lead_time_bucket) query.append('lead_time_bucket', params.lead_time_bucket);
  if (params.variable) query.append('variable', params.variable);

  const res = await fetch(`${API_BASE_URL}/skill-scores?${query.toString()}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch skill scores: ${res.statusText}`);
  return res.json();
}

export async function fetchAlerts(params: {
  region_id?: number;
  severity?: string;
}): Promise<AlertRecord[]> {
  const query = new URLSearchParams();
  if (params.region_id !== undefined) query.append('region_id', params.region_id.toString());
  if (params.severity) query.append('severity', params.severity);

  const res = await fetch(`${API_BASE_URL}/alerts?${query.toString()}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch alerts: ${res.statusText}`);
  return res.json();
}

export interface CitizenBlendRecord {
  region_id: number;
  valid_time: string;
  variable: string;
  blended_value: number;
  confidence_label: string;
  plain_language_summary: string;
}

export async function fetchCitizenBlend(params: {
  region_id: number;
  valid_time?: string;
  lead_time_hrs?: number;
  variable?: string;
}): Promise<CitizenBlendRecord> {
  const query = new URLSearchParams();
  query.append('region_id', params.region_id.toString());
  if (params.valid_time) query.append('valid_time', params.valid_time);
  if (params.lead_time_hrs !== undefined) query.append('lead_time_hrs', params.lead_time_hrs.toString());
  if (params.variable) query.append('variable', params.variable);

  const res = await fetch(`${API_BASE_URL}/blend/citizen?${query.toString()}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch citizen blend: ${res.statusText || res.status}`);
  }
  return res.json();
}

export async function fetchCitizenAlerts(params: {
  region_id?: number;
}): Promise<AlertRecord[]> {
  const query = new URLSearchParams();
  if (params.region_id !== undefined) query.append('region_id', params.region_id.toString());

  const res = await fetch(`${API_BASE_URL}/alerts/citizen?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch citizen alerts: ${res.statusText || res.status}`);
  return res.json();
}


export interface ModelComparisonRecord {
  strategy: string;
  category: string;
  rmse: number;
  mae: number;
  bias: number;
  rmse_improvement: number;
  mae_improvement: number;
  fill: string;
}

export async function fetchModelComparison(): Promise<ModelComparisonRecord[]> {
  const res = await fetch(`${API_BASE_URL}/skill-scores/comparison`);
  if (!res.ok) throw new Error(`Failed to fetch model comparison: ${res.statusText}`);
  return res.json();
}

export interface SkillEvolutionRecord {
  cycle: string;
  nwp_rmse: number;
  aiml_rmse: number;
  ensemble_rmse: number;
  blend_rmse: number;
}

export async function fetchSkillEvolution(): Promise<SkillEvolutionRecord[]> {
  const res = await fetch(`${API_BASE_URL}/skill-scores/evolution`);
  if (!res.ok) throw new Error(`Failed to fetch skill evolution: ${res.statusText}`);
  return res.json();
}

export interface DisagreementGridRecord {
  region: string;
  lead_time: string;
  variance: number;
  spread: number;
  intensity: string;
}

export async function fetchDisagreementGrid(): Promise<DisagreementGridRecord[]> {
  const res = await fetch(`${API_BASE_URL}/skill-scores/disagreement-grid`);
  if (!res.ok) throw new Error(`Failed to fetch disagreement grid: ${res.statusText}`);
  return res.json();
}
