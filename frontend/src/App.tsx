import { useEffect, useMemo, useState } from "react";
import { api, setApiKey, type Call, type Metrics } from "./lib/api";
import { KpiCard } from "./components/KpiCard";
import { CallsTimeseries, DistributionBar, DistributionPie } from "./components/Charts";
import { CallDrawer } from "./components/CallDrawer";

const OUTCOMES = [
  "",
  "booked",
  "declined",
  "no_match",
  "ineligible_carrier",
  "negotiation_failed",
  "transferred",
  "other",
];
const SENTIMENTS = ["", "positive", "neutral", "negative"];

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

function money(n: number): string {
  const sign = n >= 0 ? "+" : "-";
  return `${sign}$${Math.abs(n).toFixed(0)}`;
}

function downloadCsv(rows: Call[]) {
  const header = [
    "id",
    "created_at",
    "mc_number",
    "carrier_name",
    "load_id",
    "outcome",
    "sentiment",
    "rounds",
    "loadboard_rate",
    "final_carrier_offer",
    "agreed_price",
  ];
  const escape = (v: unknown) =>
    v === null || v === undefined
      ? ""
      : `"${String(v).replace(/"/g, '""')}"`;
  const csv = [
    header.join(","),
    ...rows.map((r) =>
      [
        r.id,
        r.created_at,
        r.mc_number,
        r.carrier_name,
        r.load_id,
        r.outcome,
        r.sentiment,
        r.rounds,
        r.loadboard_rate,
        r.final_carrier_offer,
        r.agreed_price,
      ]
        .map(escape)
        .join(","),
    ),
  ].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `calls-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function App() {
  const [apiKey, setKeyState] = useState<string>(localStorage.getItem("hr_api_key") || "");
  const [days, setDays] = useState<number>(30);
  const [outcomeFilter, setOutcomeFilter] = useState<string>("");
  const [sentimentFilter, setSentimentFilter] = useState<string>("");

  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [calls, setCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Call | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [m, c] = await Promise.all([
        api.metrics(days),
        api.listCalls({
          limit: 100,
          outcome: outcomeFilter || undefined,
          sentiment: sentimentFilter || undefined,
        }),
      ]);
      setMetrics(m);
      setCalls(c.calls);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (apiKey) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days, outcomeFilter, sentimentFilter, apiKey]);

  const sentimentLabel = useMemo(() => {
    if (!metrics) return "—";
    const s = metrics.avg_sentiment_score;
    const word = s > 0.3 ? "positive" : s < -0.3 ? "negative" : "neutral";
    return `${s.toFixed(2)} (${word})`;
  }, [metrics]);

  return (
    <div className="shell">
      <div className="topbar">
        <div className="brand">
          <div className="logo">🚛</div>
          <div>
            <h1>Acme Logistics — Carrier Sales Console</h1>
            <div className="sub">Inbound voice agent · powered by HappyRobot</div>
          </div>
        </div>
        <div className="controls">
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={1}>Last 24h</option>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <input
            type="password"
            placeholder="X-API-Key"
            value={apiKey}
            onChange={(e) => setKeyState(e.target.value)}
            onBlur={() => setApiKey(apiKey)}
          />
          <button onClick={refresh}>{loading ? "Refreshing…" : "Refresh"}</button>
        </div>
      </div>

      {error ? <div className="error">{error}</div> : null}

      {!apiKey ? (
        <div className="card">
          <h3>Welcome</h3>
          <p style={{ color: "var(--muted)" }}>
            Paste your <code>X-API-Key</code> in the top bar to load metrics. The key is
            stored in your browser's local storage only.
          </p>
        </div>
      ) : null}

      {metrics ? (
        <>
          <div className="kpi-grid">
            <KpiCard label="Total Calls" value={String(metrics.total_calls)} />
            <KpiCard
              label="Booked"
              value={String(metrics.booked_calls)}
              delta={`${pct(metrics.conversion_rate)} conversion`}
            />
            <KpiCard
              label="Avg Margin Δ"
              value={money(metrics.avg_margin_delta)}
              delta={`${pct(metrics.avg_margin_pct)} vs listed`}
            />
            <KpiCard label="Avg Rounds" value={metrics.avg_rounds.toFixed(2)} />
            <KpiCard label="Sentiment" value={sentimentLabel} />
            <KpiCard label="Eligible Rate" value={pct(metrics.eligible_rate)} />
          </div>

          <div className="charts-grid">
            <div className="card">
              <h3>Calls over time</h3>
              {metrics.timeseries.length ? (
                <CallsTimeseries data={metrics.timeseries} />
              ) : (
                <div className="empty">No calls in the selected window yet</div>
              )}
            </div>
            <div className="card">
              <h3>Outcome distribution</h3>
              <DistributionPie data={metrics.outcomes} />
            </div>
          </div>

          <div className="row-2">
            <div className="card">
              <h3>Sentiment</h3>
              <DistributionPie data={metrics.sentiments} />
            </div>
            <div className="card">
              <h3>Equipment types booked</h3>
              <DistributionBar data={metrics.equipment_types} />
            </div>
          </div>

          <div className="card">
            <div className="toolbar">
              <h3 style={{ margin: 0 }}>Recent Calls</h3>
              <div className="controls">
                <select
                  value={outcomeFilter}
                  onChange={(e) => setOutcomeFilter(e.target.value)}
                >
                  {OUTCOMES.map((o) => (
                    <option key={o} value={o}>
                      {o ? `Outcome: ${o}` : "All outcomes"}
                    </option>
                  ))}
                </select>
                <select
                  value={sentimentFilter}
                  onChange={(e) => setSentimentFilter(e.target.value)}
                >
                  {SENTIMENTS.map((s) => (
                    <option key={s} value={s}>
                      {s ? `Sentiment: ${s}` : "All sentiments"}
                    </option>
                  ))}
                </select>
                <button className="ghost" onClick={() => downloadCsv(calls)}>
                  Export CSV
                </button>
              </div>
            </div>
            {calls.length === 0 ? (
              <div className="empty">No calls yet</div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>When</th>
                    <th>MC</th>
                    <th>Carrier</th>
                    <th>Load</th>
                    <th>Outcome</th>
                    <th>Sentiment</th>
                    <th>Rounds</th>
                    <th>Listed</th>
                    <th>Agreed</th>
                  </tr>
                </thead>
                <tbody>
                  {calls.map((c) => (
                    <tr key={c.id} onClick={() => setSelected(c)}>
                      <td>{new Date(c.created_at).toLocaleString()}</td>
                      <td>{c.mc_number || "—"}</td>
                      <td>{c.carrier_name || "—"}</td>
                      <td>{c.load_id || "—"}</td>
                      <td>
                        <span className={`pill ${c.outcome}`}>{c.outcome}</span>
                      </td>
                      <td>
                        <span className={`pill ${c.sentiment}`}>{c.sentiment}</span>
                      </td>
                      <td>{c.rounds}</td>
                      <td>{c.loadboard_rate ? `$${c.loadboard_rate}` : "—"}</td>
                      <td>{c.agreed_price ? `$${c.agreed_price}` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div style={{ color: "var(--muted)", fontSize: 11, marginTop: 24, textAlign: "center" }}>
            Top lanes:{" "}
            {metrics.top_lanes.length
              ? metrics.top_lanes
                  .map((l) => `${l.label} (${l.count})`)
                  .join(" · ")
              : "—"}
          </div>
        </>
      ) : null}

      <CallDrawer call={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
