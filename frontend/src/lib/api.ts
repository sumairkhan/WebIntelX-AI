const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
export const WEBINTELX_SDK_URL = process.env.NEXT_PUBLIC_WEBINTELX_SDK_URL ?? `${API_URL}/sdk/webintelx.js`;
export const INGESTION_ENDPOINT = process.env.NEXT_PUBLIC_INGESTION_ENDPOINT ?? `${API_URL}/api/ingest/events`;

export type WebsiteType = "custom" | "wordpress" | "shopify" | "woocommerce" | "other";

export type Website = {
  id: number;
  user_id: number;
  name: string;
  domain: string;
  origin?: string | null;
  status: string;
  created_at?: string;
  updated_at?: string;
};

export type CredentialMetadata = {
  id: number;
  website_id: number;
  status: string;
  created_at: string;
  rotated_at?: string | null;
  revoked_at?: string | null;
};

export type NewCredential = CredentialMetadata & { credential: string };

export type WebsiteEvent = {
  id: number;
  website_id: number;
  event_id: string;
  timestamp: string;
  event_type: string;
  source: string;
  session_id?: string | null;
  method?: string | null;
  endpoint?: string | null;
  status_code?: number | null;
  created_at: string;
};

export type GraphNodeRecord = { id: string; label: string; type?: string; value?: number };
export type GraphEdgeRecord = { source: string; target: string; label?: string };
export type WebsiteGraph = { nodes: GraphNodeRecord[]; edges: GraphEdgeRecord[] };

export type WebsiteTelemetry = {
  event_count: number;
  finding_count: number;
  active_credential: boolean;
  connected: boolean;
  sdk_detected: boolean;
  telemetry_received: boolean;
  ingestion_working: boolean;
  last_event: WebsiteEvent | null;
};

export type FindingRecord = {
  id: number;
  website_id: number;
  event_id: number;
  agent_name: string | null;
  finding_type: string;
  confidence: number;
  evidence: Record<string, unknown> | null;
  created_at: string;
};

export type InvestigationRecord = {
  id: number;
  website_id: number;
  correlation_id: number | null;
  investigation_id: string;
  title: string;
  status: string;
  summary: string | null;
  confidence: number;
  facts: Array<Record<string, unknown>>;
  inferences: Array<Record<string, unknown>>;
  uncertainties: string[];
  created_at: string | null;
  completed_at: string | null;
};

export type IncidentRecord = {
  id: number;
  incident_id: string;
  website_id: number;
  title: string;
  risk_level: string;
  risk_score: number;
  confidence: number;
  status: string;
  created_at?: string;
  updated_at?: string;
};

export type ThreatIntelResult = {
  indicator: string;
  indicator_type: string;
  provider: string;
  malicious: boolean | string;
  confidence: number;
  reputation: string;
  categories: string[];
  source: string;
  checked_at: string;
};

export type ReportRecord = {
  website_id: number;
  website?: string;
  summary: string;
  facts: string[];
  inferences: string[];
  uncertainties: string[];
  format?: string;
};

export function hasRecentTelemetry(telemetry: WebsiteTelemetry | undefined, now = Date.now()) {
  if (!telemetry?.last_event?.created_at) return false;
  const age = now - Date.parse(telemetry.last_event.created_at);
  return age >= 0 && age <= 5 * 60 * 1000;
}

export function isWebsiteConnected(website: Website | undefined, telemetry: WebsiteTelemetry | undefined, now = Date.now()) {
  return website?.status.toLowerCase() === "active" && telemetry?.connected === true;
}

const tokenStorageKey = "webintelx_token";
const authChangeEvent = "webintelx-auth-change";

export function getStoredToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(tokenStorageKey);
}

export function setStoredToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(tokenStorageKey, token);
  window.dispatchEvent(new Event(authChangeEvent));
}

export function clearStoredToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(tokenStorageKey);
  window.dispatchEvent(new Event(authChangeEvent));
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed: ${response.status}`);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const authApi = {
  register: (payload: { email: string; password: string }) =>
    apiFetch<{ id: number; email: string; is_active: boolean; created_at?: string }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  login: (payload: { email: string; password: string }) =>
    apiFetch<{ access_token: string; token_type: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  me: () => apiFetch<{ id: number; email: string; is_active: boolean; created_at?: string }>("/api/auth/me"),
};

export const websitesApi = {
  list: () => apiFetch<Website[]>("/api/websites"),
  create: (payload: { name: string; domain: string; status?: string }) =>
    apiFetch<Website>("/api/websites", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  get: (id: number) => apiFetch<Website>(`/api/websites/${id}`),
  update: (id: number, payload: { name?: string; domain?: string; status?: string }) =>
    apiFetch<Website>(`/api/websites/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  remove: (id: number) => apiFetch<Website>(`/api/websites/${id}`, { method: "DELETE" }),
};

export const credentialsApi = {
  list: (websiteId: number) => apiFetch<CredentialMetadata[]>(`/api/websites/${websiteId}/credentials`),
  create: (websiteId: number) =>
    apiFetch<NewCredential>(`/api/websites/${websiteId}/credentials`, {
      method: "POST",
    }),
  rotate: (websiteId: number, credentialId: number) =>
    apiFetch<NewCredential>(`/api/websites/${websiteId}/credentials/${credentialId}/rotate`, {
      method: "POST",
    }),
  revoke: (websiteId: number, credentialId: number) =>
    apiFetch<CredentialMetadata>(`/api/websites/${websiteId}/credentials/${credentialId}/revoke`, { method: "POST" }),
};

export const eventsApi = {
  list: (websiteId: number, limit = 50) => apiFetch<WebsiteEvent[]>(`/api/websites/${websiteId}/events?limit=${limit}`),
  telemetry: (websiteId: number) => apiFetch<WebsiteTelemetry>(`/api/websites/${websiteId}/telemetry`),
};

export const integrationApi = {
  getConfig: () => ({ sdkUrl: WEBINTELX_SDK_URL, ingestionEndpoint: INGESTION_ENDPOINT }),
  telemetry: (websiteId: number) => eventsApi.telemetry(websiteId),
};

export const findingsApi = {
  list: (websiteId: number) => apiFetch<FindingRecord[]>(`/api/websites/${websiteId}/findings`),
};

export const investigationsApi = {
  list: (websiteId: number) => apiFetch<InvestigationRecord[]>(`/api/websites/${websiteId}/investigations`),
  get: (websiteId: number, investigationId: string) =>
    apiFetch<InvestigationRecord>(`/api/websites/${websiteId}/investigations/${investigationId}`),
  create: (websiteId: number, payload: { correlation_id?: number | null }) =>
    apiFetch<InvestigationRecord>(`/api/websites/${websiteId}/investigations`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export const incidentsApi = {
  list: (websiteId: number) => apiFetch<IncidentRecord[]>(`/api/websites/${websiteId}/incidents`),
  get: (websiteId: number, incidentId: number) => apiFetch<IncidentRecord>(`/api/websites/${websiteId}/incidents/${incidentId}`),
  update: (websiteId: number, incidentId: number, payload: Record<string, unknown>) =>
    apiFetch<IncidentRecord>(`/api/websites/${websiteId}/incidents/${incidentId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
};

export const threatIntelApi = {
  check: (websiteId: number, indicator: string, indicatorType: string) =>
    apiFetch<ThreatIntelResult>(`/api/websites/${websiteId}/threat-intelligence/check`, {
      method: "POST",
      body: JSON.stringify({ indicator, indicator_type: indicatorType }),
    }),
};

export const graphApi = {
  get: (websiteId: number) => apiFetch<WebsiteGraph>(`/api/websites/${websiteId}/graph`),
};

export const riskApi = {
  evaluate: (websiteId: number, payload: Record<string, unknown>) =>
    apiFetch<Record<string, unknown>>(`/api/websites/${websiteId}/risk/evaluate`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export const responseApi = {
  recommendations: (websiteId: number, incidentId: number) =>
    apiFetch<Array<Record<string, unknown>>>(`/api/websites/${websiteId}/incidents/${incidentId}/recommendations`),
  feedback: (websiteId: number, incidentId: number, payload: Record<string, unknown>) =>
    apiFetch<Record<string, unknown>>(`/api/websites/${websiteId}/incidents/${incidentId}/feedback`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

export const reportsApi = {
  list: (websiteId: number) => apiFetch<ReportRecord[]>(`/api/websites/${websiteId}/reports`),
};

export const healthApi = {
  get: () => apiFetch<{ status: string; application: string; environment: string; database: string }>("/health"),
};
