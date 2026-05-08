# 5-Minute Demo — Recording Action Plan

A tight, one-take walkthrough for the Loom video. Time-boxed to fit the brief's 5 min.

This file is the **action plan** (what to do when, what to say at a high level). The
**teleprompter text** lives in [loom_teleprompter.md](loom_teleprompter.md) — paste
that into Loom's teleprompter so it doesn't show up in the recording.

---

## 0. Pre-flight checklist (do this 5 minutes before recording)

### A. Smoke test the system end-to-end

Don't skip this. The whole demo hinges on one live call working — verify it now.

1. Pre-warm the Fly machine (it auto-stops when idle):
   ```bash
   curl https://happyrobot-fde-tb.fly.dev/healthz
   ```
2. Open the HappyRobot editor → Run → Start a test call. Have a 30-second conversation:
   "Hi, I'm calling about REF1001. MC 123456. Sounds good, I'll take it at the rate."
3. After the call ends, immediately check:
   - HappyRobot dashboard: run shows **COMPLETED** (not failed).
   - Your custom dashboard: a new row appears with real values (carrier name, agreed
     price, transcript). **No literal `{{...}}` strings.**
4. If the run shows FAILED but session was completed, it's the cold-start issue; do
   another test call and it should land cleanly.

### B. Seed historic calls so the dashboard isn't empty

Run this once to make the dashboard look lived-in:

```bash
BASE=https://happyrobot-fde-tb.fly.dev
KEY=$(grep '^API_KEY=' .env | cut -d= -f2)

curl -s -X POST "$BASE/api/calls" -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"mc_number":"123456","carrier_name":"B Marron Logistics LLC",
       "eligible":true,"load_id":"REF1003","outcome":"booked",
       "sentiment":"positive","rounds":1,
       "loadboard_rate":950,"agreed_price":925}'

curl -s -X POST "$BASE/api/calls" -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"mc_number":"234567","carrier_name":"Acme Carriers Inc",
       "eligible":true,"load_id":"REF1010","outcome":"declined",
       "sentiment":"neutral","rounds":0,"loadboard_rate":1300}'

curl -s -X POST "$BASE/api/calls" -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"mc_number":"999999","outcome":"ineligible_carrier",
       "sentiment":"neutral","eligible":false,"rounds":0}'
```

### C. Tabs and apps

Open these tabs **in this order** so you tab left-to-right during the demo:

1. GitHub repo (README visible)
2. HappyRobot workflow editor (Inbound Carrier Sales New, V3 engine, live)
3. Custom dashboard at `https://happyrobot-fde-tb.fly.dev/` (API key already pasted)
4. HappyRobot web-call test panel (separate tab)

### D. Environment

- Quiet notifications. Slack on Do Not Disturb.
- Close unused apps; full-screen Chrome.
- Mic check: speak a sentence, listen back in QuickTime.
- Lighting: face a window or lamp, not a screen behind you.

---

## 1. Setup overview (60s) — README + repo tour

Tab: GitHub README.

- One-line framing: who built it, what it is, deployed at the URL on screen.
- Architecture diagram: Carrier → HappyRobot → FastAPI → FMCSA + SQLite, dashboard
  reads `/api/metrics` + `/api/calls`.
- Quick scroll through `backend/app/api/`, `services/negotiation.py`, the React app.
- Mention "20+ pytest tests; negotiation policy enforced server-side, not in a prompt."

## 2. HappyRobot workflow (45s) — V3 engine

Tab: HappyRobot editor.

- Show the DAG. Point out the four tools (`verify_carrier`, `find_available_loads`,
  `search_loads_by_lane`, `evaluate_offer`) and the post-call AI nodes (Classify,
  Sentiment, Extract, log_call).
- Open the Prompt node briefly: hard rules at the top, TTS guidance section,
  initial message. **Don't read it line-by-line** — say "system prompt with three
  hard rules: verify before pitching, max three rounds, never below floor."
- One sentence on division of labor: "HappyRobot owns the conversation; the API owns
  the rules."

## 3. Live web calls (2:30) — happy path + ineligible

Tab: HappyRobot web-call panel side-by-side with custom dashboard.

### Call A — Happy path (1:30)

Click "Start call". Speak as the carrier; let the agent drive.

- "Hi, I'm calling about a load."
- Agent: "Do you see a reference number on that posting?"
- "Yes, REF1001."
- Agent: "What's your MC number?"
- "MC 123456."
- Agent verifies → "Is this B MARRON LOGISTICS LLC?" → "Yes."
- Agent pitches REF1001 (Newark to Atlanta, reefer, $2,450).
- "Sounds good, I'll take it at the listed rate."
- Agent: "Great, you're booked. We'll send the rate confirmation over shortly.
  Thanks for calling Happy Robot Logistics."
- Wait ~4 seconds — silence-hold ends the call automatically.

### Call B — Ineligible (45s)

- "Hi, I'm calling about REF1002."
- Agent: "What's your MC number?"
- "MC 999999."
- Agent verifies → "Unfortunately I'm not able to book with your authority right
  now…" → polite close.

> **Skip the negotiation call** unless you're under time. The negotiation
> policy is testable in code; the brief weighs FMCSA + load match + persistence
> more heavily than a perfect counter-offer demo. If you have time, do it after
> the dashboard tour as a "let me show you one more thing" beat.

## 4. Dashboard tour (60s)

Tab: custom dashboard. Click Refresh.

- KPI row moved: total calls +2, conversion ticks, average rounds updated.
- Outcome distribution: booked / declined / ineligible all populated.
- Click the most recent call → drawer opens with full transcript + extracted fields.
- Show the filters (outcome, sentiment) and the CSV export button briefly.
- "This is what an ops manager opens with their morning coffee."

## 5. Wrap (15s)

- Next steps: live transfer integration, dynamic floors, TMS sync.
- "Repo and dashboard links are in the README. Thanks for watching."

---

## Time budget

| Section | Target | Cumulative |
|---|---|---|
| Setup overview | 1:00 | 1:00 |
| Workflow | 0:45 | 1:45 |
| Call A (happy path) | 1:30 | 3:15 |
| Call B (ineligible) | 0:45 | 4:00 |
| Dashboard | 0:45 | 4:45 |
| Wrap | 0:15 | 5:00 |

Stay punchy. If you blow the budget, cut Call B before cutting the dashboard tour.

## After recording

- Watch the playback at 1.25× to spot anything cringeworthy.
- Title: "HappyRobot FDE Take-Home — Inbound Carrier Sales (Tim Bruckdorfer)".
- Description: include the GitHub repo URL and the dashboard URL.
- Send the Loom link in the email per `docs/email.md`.
