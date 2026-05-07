import type { Call } from "../lib/api";

type Props = {
  call: Call | null;
  onClose: () => void;
};

function fmt(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export function CallDrawer({ call, onClose }: Props) {
  if (!call) return null;
  const margin =
    call.agreed_price && call.loadboard_rate
      ? call.agreed_price - call.loadboard_rate
      : null;
  return (
    <div
      className="drawer-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="drawer">
        <header>
          <div>
            <h2>Call #{call.id}</h2>
            <div style={{ color: "var(--muted)", fontSize: 12 }}>
              {new Date(call.created_at).toLocaleString()}
            </div>
          </div>
          <button className="ghost" onClick={onClose} style={{ background: "transparent", color: "var(--muted)", border: "1px solid var(--border)", borderRadius: 8, padding: "6px 10px", cursor: "pointer" }}>
            Close
          </button>
        </header>

        <div className="drawer-grid">
          <div className="field">
            <div className="k">Outcome</div>
            <div className="v">
              <span className={`pill ${call.outcome}`}>{call.outcome}</span>
            </div>
          </div>
          <div className="field">
            <div className="k">Sentiment</div>
            <div className="v">
              <span className={`pill ${call.sentiment}`}>{call.sentiment}</span>
            </div>
          </div>
          <div className="field">
            <div className="k">MC Number</div>
            <div className="v">{call.mc_number || "—"}</div>
          </div>
          <div className="field">
            <div className="k">Carrier</div>
            <div className="v">{call.carrier_name || "—"}</div>
          </div>
          <div className="field">
            <div className="k">Load</div>
            <div className="v">{call.load_id || "—"}</div>
          </div>
          <div className="field">
            <div className="k">Rounds</div>
            <div className="v">{call.rounds}</div>
          </div>
          <div className="field">
            <div className="k">Listed Rate</div>
            <div className="v">{fmt(call.loadboard_rate)}</div>
          </div>
          <div className="field">
            <div className="k">Final Carrier Offer</div>
            <div className="v">{fmt(call.final_carrier_offer)}</div>
          </div>
          <div className="field">
            <div className="k">Agreed Price</div>
            <div className="v">{fmt(call.agreed_price)}</div>
          </div>
          <div className="field">
            <div className="k">Margin Δ</div>
            <div className="v" style={{ color: margin === null ? undefined : margin <= 0 ? "var(--good)" : "var(--warn)" }}>
              {margin === null ? "—" : (margin >= 0 ? "+" : "") + fmt(margin)}
            </div>
          </div>
        </div>

        <h3 style={{ marginTop: 0, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.5px" }}>
          Transcript
        </h3>
        <div className="transcript">{call.transcript || "(no transcript captured)"}</div>

        {call.notes ? (
          <>
            <h3 style={{ marginTop: 16, color: "var(--muted)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Notes
            </h3>
            <div className="transcript">{call.notes}</div>
          </>
        ) : null}
      </div>
    </div>
  );
}
