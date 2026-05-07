# 5-Minute Demo Script

A tight, one-take script for the Loom walkthrough. Time-boxed to fit the brief's 5 min.

## 0. Pre-flight checklist (do this 5 minutes before recording)

- [ ] Pre-warm the Fly instance: `curl https://happyrobot-fde-tb.fly.dev/healthz`
- [ ] Open these tabs in this order:
  1. GitHub repo (README visible)
  2. HappyRobot workflow editor (web-call trigger ready)
  3. The deployed dashboard at `https://happyrobot-fde-tb.fly.dev/` with the API key already
     pasted in the top bar
  4. The HappyRobot web-call test panel
- [ ] Seed at least 3 historic calls so the dashboard isn't empty on first load:
  ```bash
  BASE=https://happyrobot-fde-tb.fly.dev; KEY=<your-key>
  curl -s -X POST "$BASE/api/calls" -H "X-API-Key: $KEY" \
    -H "Content-Type: application/json" \
    -d '{"mc_number":"123456","carrier_name":"Pre-demo Carrier",
         "eligible":true,"load_id":"REF1003","outcome":"booked",
         "sentiment":"positive","rounds":1,
         "loadboard_rate":950,"agreed_price":950}'
  curl -s -X POST "$BASE/api/calls" -H "X-API-Key: $KEY" \
    -H "Content-Type: application/json" \
    -d '{"mc_number":"234567","carrier_name":"Pre-demo Two",
         "eligible":true,"load_id":"REF1010","outcome":"declined",
         "sentiment":"neutral","rounds":0,
         "loadboard_rate":1300}'
  curl -s -X POST "$BASE/api/calls" -H "X-API-Key: $KEY" \
    -H "Content-Type: application/json" \
    -d '{"mc_number":"999999","outcome":"ineligible_carrier",
         "sentiment":"neutral","eligible":false,"rounds":0}'
  ```
- [ ] Quiet notifications, close other apps, full-screen Chrome, mic check.

## 1. Setup overview (60 seconds)

Open with the architecture in the README. Read out loud, with my own framing:

> "Hi, this is the inbound carrier-sales POC I built for HappyRobot's FDE case.
> The system has three pieces: a HappyRobot web-call agent that handles the
> conversation, a FastAPI backend that owns the business logic — FMCSA verification,
> load matching, and a server-enforced negotiation policy — and a custom React
> dashboard that surfaces the KPIs a freight broker actually cares about. Everything
> is one Docker image deployed to Fly.io with HTTPS and API-key auth. I purposely kept
> the negotiation rules in code, not in a prompt, so the agent literally cannot commit
> the broker to a price below the floor."

Quickly scroll the repo: `backend/app/api`, `services/negotiation.py`, the React
dashboard, and the Dockerfile. Mention "20+ pytest tests on the negotiation policy and
the API surface — happy to dig in later."

## 2. HappyRobot workflow (30 seconds)

Switch to the HappyRobot tab. Show:

- The web-call trigger.
- The four tool nodes (verify_carrier, search_loads, evaluate_offer, log_call).
- The system prompt's hard rules ("max 3 rounds", "never below floor").
- The end-of-call extraction + outcome classifier + sentiment classifier.

> "I lean on HappyRobot for what it's great at — turn-taking, classification,
> extraction — and lean on the API for the rules of the game."

## 3. Three live web calls (3 minutes)

Open the HappyRobot web-call panel side-by-side with the dashboard.

### Call A — Happy path (60s)

Click "Start call". Speak as the carrier:

- Agent: "Hi, this is Acme Logistics. Can I get your MC number?"
- Me: "MC 123456."
- Agent verifies → eligible. "What kind of equipment and lane?"
- Me: "Reefer, looking for something Newark NJ to Atlanta GA."
- Agent pitches REF1001 at $2,450.
- Me: "Sounds good, I'll take it at the listed rate."
- Agent: "Great, transferring you to a sales rep now…" / "Transfer was successful."
- End call.

### Call B — Counter-offer (75s)

- Me: "MC 234567." → eligible.
- Me: "Dry van, Chicago to Dallas."
- Agent pitches REF1002 at $2,100.
- Me: "I can't do less than $1,800 on that one."
- Agent calls evaluate_offer round=1 → counters at midpoint clamped to floor (~$1,932).
- Me: "OK, $1,932 works."
- Agent confirms → mock transfer.

### Call C — Ineligible (45s)

- Me: "MC 999999."
- Agent verifies → no carrier found / not eligible.
- Agent: "Thanks for calling. Unfortunately I'm not able to book with your authority
  right now…"
- End call.

## 4. Dashboard tour (60 seconds)

Switch to the dashboard tab. Click "Refresh".

- Point out **the KPI row** moving: total calls just went up by 3, conversion ticks,
  avg rounds and sentiment update.
- Click **"Outcome distribution"** — booked / declined / ineligible all represented.
- Scroll to the **calls table**, click the most recent call → drawer opens with
  transcript + extracted fields + agreed price.
- Mention the **filters** (outcome / sentiment) and the **CSV export** button.
- Mention the **"Top lanes"** ribbon at the bottom.

> "This is what an ops manager opens with their morning coffee."

## 5. Wrap (15 seconds)

> "Next steps would be live transfer integration, dynamic pricing floors, and TMS
> sync for the load board. Repo and dashboard links are in the README. Thanks!"

## Time budget

| Section | Target | Cumulative |
|---|---|---|
| Setup overview | 1:00 | 1:00 |
| Workflow | 0:30 | 1:30 |
| Call A | 1:00 | 2:30 |
| Call B | 1:15 | 3:45 |
| Call C | 0:45 | 4:30 |
| Dashboard | 0:30 | 5:00 |

Stay punchy. If you blow the time budget, cut Call B or shorten Call A.
