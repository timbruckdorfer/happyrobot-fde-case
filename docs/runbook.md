# Runbook — HappyRobot FDE Case

## TL;DR — reproduce the deployment in 10 minutes

Prerequisites: macOS or Linux, [Docker](https://docs.docker.com/get-docker/) (optional locally),
[Fly.io account](https://fly.io/) + `flyctl`, an [FMCSA web key](https://mobile.fmcsa.dot.gov/QCDevsite/getStarted),
and `node 20+` + `python 3.12` (the repo's `Makefile` will install them via `uv` and `npm`).

```bash
# 1. clone + setup
git clone <your-repo-url> happyrobot-fde && cd happyrobot-fde

# 2. install local toolchains (uv + Python 3.12 + npm deps)
make setup

# 3. run tests
make test          # backend pytest

# 4. (optional) run locally
export API_KEY=local-dev-key
export FMCSA_API_KEY=<your-fmcsa-key>
make dev-api &     # backend on :8000
make dev-web       # frontend on :5173 (proxies /api -> :8000)

# 5. deploy to Fly.io
flyctl auth login
flyctl launch --no-deploy --copy-config --name happyrobot-fde   # one-time
flyctl volumes create happyrobot_data --region iad --size 1     # one-time
export API_KEY=$(openssl rand -hex 24)
export FMCSA_API_KEY=<your-fmcsa-key>
make fly-secrets
make fly-deploy
flyctl status
```

Visit `https://happyrobot-fde-tb.fly.dev/` for the dashboard (paste the API key in the
top-right input). Visit `https://happyrobot-fde-tb.fly.dev/api/docs` for OpenAPI.

## Configuration

All configuration is via environment variables (read at startup by
`app/core/settings.py`):

| Variable | Default | Purpose |
|---|---|---|
| `API_KEY` | `dev-api-key-change-me` | Required for all `/api/*` endpoints |
| `FMCSA_API_KEY` | _empty_ | FMCSA QCMobile webKey |
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLite path (Fly: `sqlite:////data/app.db`) |
| `CORS_ORIGINS` | `*` | Comma-separated allowlist; restrict to your dashboard origin in prod |
| `ENVIRONMENT` | `dev` | Tagged into structured logs |
| `NEGOTIATION_FLOOR_PCT` | `0.92` | Below this share of `loadboard_rate`, broker counters |
| `NEGOTIATION_CEILING_PCT` | `1.10` | Above this share, broker counters down |
| `NEGOTIATION_MAX_ROUNDS` | `3` | Hard cap on negotiation turns |
| `RATE_LIMIT_VERIFY` | `30/minute` | slowapi rate for `/api/verify_carrier` |

## Operational notes

- **Persistence:** SQLite on a Fly volume (`/data`). For production scale move to
  Postgres by changing `DATABASE_URL`; SQLModel works against both unchanged.
- **Secrets:** stored as Fly secrets (`flyctl secrets list`). Never committed.
- **TLS:** Fly's default automatic Let's Encrypt cert (`force_https = true`).
- **Auto-stop:** Fly machines auto-stop when idle (`auto_stop_machines = "stop"`).
  First request after idle has ~1s cold start; pre-warm with `curl /healthz` before
  recording the demo.
- **Logs:** structured JSON via `structlog`. View with `flyctl logs`.

## Smoke tests after deploy

```bash
BASE=https://happyrobot-fde-tb.fly.dev
KEY=<your-API_KEY>

curl -s "$BASE/healthz"
curl -sf -X POST "$BASE/api/search_loads" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"max_results":2}' | jq '.count'
curl -sf -X POST "$BASE/api/evaluate_offer" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"load_id":"REF1001","carrier_offer":2100,"round":1}' | jq '.decision'
curl -sf -X POST "$BASE/api/verify_carrier" \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"mc_number":"123456"}' | jq '.eligible, .carrier_name'
```

## Common issues

| Symptom | Fix |
|---|---|
| `401` from API | Header missing or wrong key. Check `X-API-Key` matches `flyctl secrets list`. |
| `eligible:false` with reason "FMCSA API key not configured" | Run `make fly-secrets` with `FMCSA_API_KEY` set. |
| Dashboard renders but charts say "No data yet" | No calls logged to `/api/calls` yet. Run a test web call or `curl` a sample payload. |
| `flyctl deploy` fails on volume mount | Run `flyctl volumes create happyrobot_data --region <your-region>` first. |
| HappyRobot web call ends in <1s, no audio from agent | Voice agent worker failed to attach to LiveKit room. Likeliest causes (in order): `Prompt.model.id` is V2's `turbo` instead of V3's `turbo-one`; `agent.language_accents.id` is `en` instead of `en-us`; workflow not actually published (publish silently fails on prompt-quality issues). Full diagnostic in `docs/troubleshooting_and_v3_migration.md`. |
| Dashboard "Recent Calls" rows show literal `{{extract.mc_number}}` etc. | V2 short-form variable references (`{{extract.foo}}`, `{{transcript}}`, `{{verify_carrier.foo}}`) stored as plain text. V3 requires Plate `mention` nodes referencing the upstream node's `persistent_id`. Use `mcp__happyrobot-ai__fix_broken_vars` to verify, and the inline variable picker in the editor (or the long form `{{<persistent_id>.<variable_id>}}`) to fix. |
| `Cannot publish: some prompt nodes have open issues` | The Prompt node has open prompt-quality issues. Run `mcp__happyrobot-ai__fix_prompt_issues` to enumerate them. Common offenders: dangling `transfer_to_colleague` tool reference, TTS-unfriendly tokens (`HappyRobotLoads.com`, `3 PM`, `53 feet`), duplicated instruction blocks. Fix or publish with `skip_prompt_validation=true`. |
| Agent finishes its closing line, then call sits open until caller manually hangs up (logged as `failed` session) | `max_silence_hold_duration` not set on the Inbound Voice Agent. The LLM has no in-prompt way to hang up — the platform terminates the call when this silence-after-assistant threshold is hit. Set it to `4` seconds on the agent node. Details in `docs/troubleshooting_and_v3_migration.md` (bug #5). |
| HappyRobot run shows `FAILED` but the conversation was perfect | Two different status concepts. Pull `monitor_runs action="sessions" run_id=<id>` first — `session.status: completed` with `call_end_initiator: "user"` means the voice call itself was fine. The run is only failed because a downstream node (usually `POST log_call`) returned a 5xx. Most common cause: Fly cold-start hiccup (machine has `auto_stop_machines = "stop"`); retest the call. If consistent, run the failing payload through `translate()` in `app/services/happyrobot_translate.py` to find the real validation failure. |

## Tearing down

```bash
flyctl apps destroy happyrobot-fde --yes
flyctl volumes destroy happyrobot_data --yes   # data is permanently deleted
```
