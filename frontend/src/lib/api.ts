const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || "";

export type DistributionItem = { label: string; count: number };
export type TimeseriesPoint = {
  date: string;
  calls: number;
  booked: number;
  conversion_rate: number;
};

export type Metrics = {
  total_calls: number;
  booked_calls: number;
  conversion_rate: number;
  avg_rounds: number;
  avg_margin_delta: number;
  avg_margin_pct: number;
  avg_sentiment_score: number;
  eligible_rate: number;
  outcomes: DistributionItem[];
  sentiments: DistributionItem[];
  equipment_types: DistributionItem[];
  top_lanes: DistributionItem[];
  timeseries: TimeseriesPoint[];
};

export type Call = {
  id: number;
  created_at: string;
  mc_number: string | null;
  carrier_name: string | null;
  eligible: boolean | null;
  load_id: string | null;
  outcome: string;
  sentiment: string;
  rounds: number;
  loadboard_rate: number | null;
  final_carrier_offer: number | null;
  agreed_price: number | null;
  transcript: string | null;
  notes: string | null;
};

function getApiKey(): string {
  return localStorage.getItem("hr_api_key") || "";
}

export function setApiKey(key: string): void {
  localStorage.setItem("hr_api_key", key);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const key = getApiKey();
  const resp = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": key,
      ...(init?.headers || {}),
    },
  });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return resp.json();
}

export const api = {
  metrics: (days = 30) => request<Metrics>(`/api/metrics?days=${days}`),
  listCalls: (params: {
    limit?: number;
    offset?: number;
    outcome?: string;
    sentiment?: string;
  } = {}) => {
    const q = new URLSearchParams();
    if (params.limit) q.set("limit", String(params.limit));
    if (params.offset) q.set("offset", String(params.offset));
    if (params.outcome) q.set("outcome", params.outcome);
    if (params.sentiment) q.set("sentiment", params.sentiment);
    return request<{ count: number; calls: Call[] }>(`/api/calls?${q.toString()}`);
  },
  health: () =>
    fetch(`${API_BASE}/healthz`).then((r) => r.json()) as Promise<{ status: string }>,
};
