export type User = {
  id: number;
  email: string;
  is_active: boolean;
  created_at?: string;
};

export type Website = {
  id: number;
  user_id: number;
  name: string;
  domain: string;
  status: string;
  created_at?: string;
  updated_at?: string;
};

export type Credential = {
  id: number;
  website_id: number;
  credential?: string;
  status: string;
  created_at?: string;
  rotated_at?: string | null;
  revoked_at?: string | null;
};

export type EventRecord = {
  id: number;
  website_id: number;
  event_id: string;
  timestamp: string;
  event_type: string;
  source: string;
  source_ip?: string | null;
  session_id?: string | null;
  user_id?: string | null;
  method?: string | null;
  endpoint?: string | null;
  status_code?: number | null;
  user_agent?: string | null;
  metadata?: Record<string, unknown> | null;
};

export type Finding = {
  id: number;
  website_id: number;
  event_id: number;
  agent_name?: string | null;
  finding_type: string;
  confidence: number;
  evidence?: Record<string, unknown> | null;
  created_at?: string;
};

export type Investigation = {
  id: number;
  website_id: number;
  investigation_id: string;
  title: string;
  status: string;
  summary?: string | null;
  confidence: number;
  created_at?: string;
  completed_at?: string | null;
  correlation_id?: number | null;
};

export type Incident = {
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

export type ThreatIntelItem = {
  indicator: string;
  indicator_type: string;
  reputation: string;
  confidence: number;
  provider: string;
  last_checked?: string;
  risk_level?: string;
};

export type GraphNode = {
  id: string;
  label: string;
  type: string;
  value?: number;
};

export type GraphEdge = {
  source: string;
  target: string;
  label: string;
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
