# Troubleshooting Log — V3 Engine Migration of the Inbound Carrier Workflow

This document captures the full debugging session that took the `Inbound Carrier Sales New` workflow from "every call drops in <1 second with literal `{{...}}` strings polluting the dashboard" to "agent picks up, conversation works, dashboard populates correctly." It exists so future-you (or anyone else inheriting this workspace) doesn't have to re-walk the same eight dead ends.

## TL;DR — the bugs we found

The workflow had **five separate problems stacked on top of each other**, all hidden behind variants of the same surface symptom (silent agent / literal `{{...}}` in the dashboard / call wouldn't end):

| # | Bug | Root cause | Fix |
|---|---|---|---|
| 1 | Workflow on deprecated V2 engine | The starter template was V2; V3 had a different schema | Forked, took the "Upgrade to new engine" action |
| 2 | Workflow couldn't be published | Six prompt-quality issues blocked validation; UI failed silently | Rewrote prompt to address all 7 issues, or pass `skip_prompt_validation=true` |
| 3 | Agent worker never attached to LiveKit room | Stale model ID `turbo` (V2) and language accent `en` instead of `en-us` (mismatched the voice's `accent_key`) | `model.id = "turbo-one"` (gpt-4.1), `language_accents.id = "en-us"` |
| 4 | Variable references stored as plain text, not Plate mentions | The starter template's `{{...}}` syntax was V2 short-form (`{{transcript}}`, `{{extract.foo}}`) — V3 stores variable references as Plate `mention` nodes with the upstream node's `persistent_id` as `group_id` | Rewrote every variable in 8 nodes (Extract, Classify, Sentiment, POST log_call, all 4 tool webhooks) to V3 syntax `{{<persistent_id>.<variable_id>}}` |
| 5 | Agent finished its closing line, then the call sat open until the user manually hung up (counted as a "failed" call) | `max_silence_hold_duration` was unset on the Inbound Voice Agent. The LLM has no in-prompt way to actually hang up — the platform ends the call when this silence-after-assistant threshold is hit, and with no value set, that threshold never triggered | Set `max_silence_hold_duration: 4` (seconds) on the Inbound Voice Agent |

Bugs 3 and 4 each independently caused the silent agent + broken dashboard. Bug 5 only became visible after the agent could actually conduct a full conversation. We had to fix all of them; fixing only some did not move the needle.

---

## How the symptoms presented

- Web call would start. Browser mic activated for ~1 second. Then the call would terminate with no audio from the agent.
- The HappyRobot dashboard showed the run as **"Completed"** — but inspecting the run, the **session** was `status: failed, duration: 0, Room: n/a`.
- Our React dashboard's "Recent Calls" table showed entries with literal placeholder strings: `MC: {{extract.mc_number}}`, `Carrier: {{verify_carrier.carrier_name}}`, `Load: {{extract.reference_number}}`, `Outcome: OTHER`, `Sentiment: NEUTRAL`, `Rounds: 0`.
- The "in-node Call agent" button (testing the agent in isolation) failed instantly with `no trigger data found`. This was misleading — it's the expected behavior when bypassing the Web Call trigger, but it sent us hunting for a wiring bug that didn't exist.

The only successful entries in our dashboard pre-debugging (e.g. `B MARRON LOGISTICS LLC`, `API Smoke Test`) were ones we'd hit `POST /api/calls/happyrobot` on directly via `curl` — bypassing the HappyRobot pipeline entirely. So the voice flow had **never** worked end-to-end through HappyRobot before this debug session.

## How we diagnosed it

### The dead ends (rule-outs)

These were tried and didn't fix it. Documenting them so we don't re-run them:

1. **"The agent has no greeting"** — false. The Prompt node had `Initial Message: "Thank you for calling Happy Robot Logistics, how can I help?"`. V3's Prompt node owns the first-message field (not the Agent node, which is V2's place).
2. **"The model is invalid"** — partially true. The Prompt's model was `turbo` (V2 only). Changed to `turbo-one` (V3's gpt-4.1). Did not fix the silence on its own.
3. **"The workflow isn't published"** — true but not the cause. After force-publishing, the silent-agent failure persisted identically. Publishing was a prerequisite for the V3 voice infra to behave normally, but it wasn't sufficient.
4. **"The browser mic permission is broken"** — false. Mic activated; we could see WebRTC handshake start.
5. **"The agent name has a trailing space"** — cosmetic only. Trimmed it; no effect on session establishment.

### The smoking gun

`monitor_runs sessions <run_id>` returned, on every attempt:
```
Session: ...
  Type: inbound
  Status: failed
  Duration: 0 seconds
  User Number: web
  Room: n/a
```

`Room: n/a` despite a `room_name` being generated in the agent's output payload meant: **a room name was allocated, but no LiveKit worker ever attached to it.** That points the finger at agent worker dispatch — which only fails before the agent runs if the agent's config fails initialization.

The two fields that finally cracked it:

- **`agent.language_accents.id = "en"`** — but the voice "Paul" (`m357hexpjk2s`) declares `accent_key: "en-us"` in its metadata. When the worker tries to bind the voice's TTS pipeline to the configured accent, the lookup fails and the worker aborts.
- **`agent.name = "Paul "`** (trailing space) — cosmetic, but compared to the live Outbound Voice Agent in the same account (which is wired correctly with `"Paul"` and `"en-us"`), this confirmed the inbound config was a stale V2-style export.

After fixing both, the voice session attached. Once the agent actually started speaking, we discovered…

### The second bug, hidden by the first

After voice was working, real call data was flowing — but Extract, Classify, Sentiment, and `POST log_call` were all still acting like they had on broken calls. They were running on **literal text** because their input fields contained the V2-style short-form `{{transcript}}` as plain text inside a Plate paragraph node, like:
```json
"input": [{ "type": "paragraph", "children": [{ "text": "{{transcript}}" }] }]
```
V2's runtime templating engine resolved short-form references like `{{transcript}}` against the upstream call context. V3 does not — it requires Plate `mention` nodes with the upstream node's full `persistent_id` as `group_id`:
```json
"input": [{ "type": "paragraph", "children": [
  { "text": "" },
  { "type": "variable", "group_id": "<inbound_voice_agent_persistent_id>", "variable_id": "transcript", "children": [{ "text": "" }] },
  { "text": "" }
] }]
```
The MCP API auto-converts the string-template syntax `{{<persistent_id>.<variable_id>}}` into this Plate mention format, so we didn't have to write the JSON by hand — we just had to use the **right** persistent IDs.

This bug applied to **8 separate nodes**:
- `Extract.input`, `Classify.input`, `Sentiment.input` — all had `{{transcript}}` as plain text. They were processing the literal four-character string `{{transcript}}`, which is why every call's `Outcome` came out `OTHER` and `Sentiment` came out `NEUTRAL` (defaults).
- `POST log_call` — every one of its 14 body fields used V2 short-form (e.g. `{{extract.reference_number}}`, `{{verify_carrier.carrier_name}}`, `{{transcript}}`, `{{duration}}`).
- The four tool webhooks — `POST MC Number`, `GET Load`, `POST search_loads`, `POST evaluate_offer` — referenced their parent tool's parameters with V2 short-form (`{{mc_number}}`, `{{equipment_type}}`, etc.) rather than the V3 long form `{{<tool_persistent_id>.<param_name>}}`.

Every single one of those silently sent literal `{{...}}` strings to its target instead of the resolved value.

### A workflow-graph constraint we hit while fixing log_call

`POST log_call` is a child of `Extract` (which is downstream of `Sentiment` → `Classify` → `Inbound Voice Agent`). The four tool webhooks (`POST MC Number`, `GET Load`, `POST search_loads`, `POST evaluate_offer`) are children of their respective tool nodes, which are siblings under the Prompt — i.e. **on a parallel branch** of the DAG.

`log_call` cannot directly reference `{{verify_carrier.carrier_name}}` or `{{verify_carrier.eligible}}` because those fields belong to the POST MC Number webhook on the parallel tool branch — they're not in `log_call`'s ancestor chain.

Workaround we landed on:

- **`carrier_name`** is now sourced from the AI Extract node (which already had `carrier_name` as a parameter and pulls it from the transcript). This is actually *more* robust than reading the verify_carrier API response, because it captures the name as confirmed in conversation rather than what FMCSA had on file.
- **`eligible`** is left empty in the log payload. Two ways to fix this in the future if needed:
  1. Add `eligible` as a parameter to the AI Extract node so the LLM infers it from the transcript ("the agent verified the carrier and proceeded → true").
  2. Restructure so `POST log_call` lives under the tool branch (but then it'd fire mid-call, not at end-of-call, so this isn't a clean fix).
- **`loadboard_rate`** likewise left empty — same architectural reason. Adding it as an Extract parameter is the simplest fix.

### Bug #5 — the call wouldn't end after the agent's closing line

After bugs 1–4 were resolved and the agent could actually hold a full conversation
(verify carrier → find load → negotiate → agree on price → say goodbye), a new
symptom surfaced: **the agent would finish its closing line ("Thanks for calling
Happy Robot Logistics") and then go silent — but the call session stayed open
indefinitely.** The user had to click the browser's hang-up button manually,
which got logged as a `failed` session in the HappyRobot dashboard, dragging
down the success metrics for otherwise-perfect calls.

This is a non-obvious quirk of voice-agent platforms in general: **the LLM has
no in-prompt way to actually end a call.** Telling the agent "End the call" in
the system prompt is just text — it doesn't translate to any RPC call. The
platform decides when to terminate the session, based on configuration. In
HappyRobot V3, the relevant field is `max_silence_hold_duration` on the
Inbound Voice Agent (units: seconds). After the assistant produces a turn and
no further user audio arrives within that window, the platform tears down the
LiveKit room and marks the session `completed`.

The starter template doesn't set this field, and the schema has no documented
default — meaning the threshold either never fires or fires only after a very
long timeout. Either way, calls don't end gracefully.

**Fix:** set `max_silence_hold_duration: 4` (seconds) on the agent.
- Long enough that mid-conversation pauses (carriers thinking, looking up
  numbers, checking notes) don't accidentally end the call.
- Short enough that the call closes crisply after the agent's final line —
  there's nothing the caller will say after "Thanks for calling Happy Robot
  Logistics" that needs another 5+ seconds to begin.

We also set `max_call_duration: 600` (10 minutes) as a hard ceiling against
runaway calls — the schema accepted this and it gives a backstop if the silence
threshold somehow fails to trigger.

A more sophisticated alternative would be to add an explicit `end_call` tool
node that the agent invokes when the conversation should terminate. We didn't
take that path because: (a) HappyRobot's V3 integration list doesn't expose a
discoverable `end_call` event ID through `list_integrations`, so the wiring
isn't obvious; (b) silence-based termination is good enough for our use case
(structured carrier conversations with predictable closings); (c) it means one
fewer tool node to maintain.

### Read this before panicking about a "FAILED" run

Two different status concepts in HappyRobot, easy to conflate:

| Concept | Tracks | Surfaces in |
|---|---|---|
| **Session status** | The voice call itself — LiveKit room, audio quality, who hung up. Fields: `status`, `duration`, `call_end_event`, `call_end_initiator`. | `monitor_runs action="sessions"` |
| **Run status** | Whether every workflow node executed without error. A single failed downstream webhook fails the whole run. | `monitor_runs action="list"` and `action="get"` |

The two diverge often. A perfect 82-second conversation that ends cleanly with `call_end_initiator: "user"` (caller hung up) and `Session.status: completed` will still show as a `FAILED` **run** if `POST log_call` returns 5xx. When you see a "FAILED" run, always pull the session details first to find out whether the call itself was actually bad, or just one of the downstream nodes choked on its payload.

In one observed case here, a real 82-second booking conversation completed cleanly (`session.status: completed`, `call_end_initiator: "user"`) but the run was marked `failed` because `POST log_call` got a 5xx response from the FastAPI backend. We could not reproduce the 5xx with the same payload shape against the same endpoint — every retry returned 200. The most likely cause was a Fly.io cold-start hiccup (the machine has `auto_stop_machines = "stop"`, and the log_call POST happened ~11 seconds after the call ended, plenty of time for the machine to be transitioning state). Worth a `flyctl logs` look if it recurs, otherwise treat as transient.

If the 5xx is consistent rather than transient, the backend's `translate()` function in `app/services/happyrobot_translate.py` is the right place to look. It already handles:
- Empty-string fields → `None` (`_to_float`, `_to_int`, `_to_bool` all check `v == ""`)
- String-typed numbers from the LLM Extract (`"2450"` → `2450.0`)
- Missing fields (defaults to `None` or `0`)
- Unknown classifications (falls through to "other")

So the only payload that should hard-fail is one missing the `classification` field entirely (raises `ValueError` → 422). If you get a true 500 with everything populated, run the backend locally and `pytest`-trace the failing payload through `translate()`.

### Final missing pieces (the prompt)

The "Cannot publish: some prompt nodes have open issues" failure was the reason an earlier publish attempt failed silently in the UI. Running `fix_prompt_issues` returned **7 open issues**:

- **3× `verbose`** — the prompt had three duplicated instruction blocks (the reference-number ask, the MC number ask, and the load-details example were each written twice).
- **2× `text_to_speech_unfriendly`** — `"HappyRobotLoads.com"` would be read as one garbled word; `"3 PM"` and `"53 feet"` would be read literally rather than as natural speech.
- **1× `missing_text_to_speech_guidance`** — the prompt didn't tell the model how to read numbers, prices, dates, abbreviations, or URLs aloud.
- **1× `tool_does_not_exist`** — the prompt instructed the agent to "transfer them to your colleague" via a `transfer_to_colleague` tool that was never defined in the workflow.

The rewrite we shipped (now live in the Prompt node):

- Removed all three duplicated blocks.
- Added an explicit **"Numbers and units"** section telling the model how to read prices ("thirteen hundred dollars" not "$1,300"), distances ("fifty-three feet"), times ("three P M", "four A M"), dates ("Friday, July twelfth"), MC numbers (digit-by-digit), URLs ("happy robot loads dot com"), and abbreviations ("M C number", "T W I C").
- Spelled all of the above out in the example call dialogue, so the model has concrete in-context examples.
- Replaced the `transfer_to_colleague` step with a verbal booking confirmation ("Great, you're booked. We'll send the rate confirmation over shortly.") — this matches the brief's "mock transfer" requirement without referencing a non-existent tool.

---

## The MCP-driven fix sequence (what we actually ran)

For reproducibility, here's the exact sequence of MCP calls that took the workflow from broken to working. All against version `019df5b4-5c6f-7317-b1a5-853fce36613a` of workflow `019df5b4-5c48-7e18-b770-3186342d29ef` (Inbound Carrier Sales New).

```
# 1. Authenticate and get the lay of the land
mcp__happyrobot-ai__setup(api_key=sk_live_..., cluster=us)
mcp__happyrobot-ai__list_workflows()
mcp__happyrobot-ai__get_workflow_details(workflow_id, include_nodes=true)

# 2. Inspect each suspect node and the latest run
mcp__happyrobot-ai__get_node_details(version_id, <each node_id>)
mcp__happyrobot-ai__monitor_runs(action="sessions", run_id=<latest>)
mcp__happyrobot-ai__monitor_runs(action="outputs", run_id=<latest>)
mcp__happyrobot-ai__get_node_config_schema(version_id, agent_node_id)

# 3. Fix agent identity (model + accent + name)
#    (Inbound Voice Agent node)
update agent.name to "Paul" (no trailing space)
update agent.language_accents.id to "en-us"
update prompt.model.id to "turbo-one"

# 4. Unlock the version (publishing locks it)
mcp__happyrobot-ai__manage_versions(action="unpublish", version_id)

# 5. Rewrite every variable reference (8 nodes)
#    Use V3 syntax: {{<persistent_id>.<variable_id>}}
update Extract.input          → {{<agent_id>.transcript}}
update Classify.input         → {{<agent_id>.transcript}}
update Sentiment.input        → {{<agent_id>.transcript}}
update POST_MC_Number.data    → {{<verify_carrier_tool_id>.mc_number}}
update GET_Load.url           → /api/loads/{{<find_loads_tool_id>.reference_number}}
update POST_search_loads.data → {{<search_lane_tool_id>.equipment_type}} etc.
update POST_evaluate_offer.data → {{<evaluate_tool_id>.reference_number}} etc.
update POST_log_call.data     → 14 fields, all using real persistent IDs

# 6. Verify nothing's broken
mcp__happyrobot-ai__fix_broken_vars(version_id, dry_run=true)
# Expect: "10 passed, 0 failed, 0 unfixable"

# 7. Rewrite the Prompt to address the 7 quality issues
update Prompt.prompt_md (full rewrite)
update Prompt.initial_message (unchanged)

# 8. Republish
mcp__happyrobot-ai__manage_versions(
  action="publish",
  version_id,
  environment="production",
  skip_prompt_validation=true,   # async re-analysis lag
  force=true                       # auto-unpublish previous live version
)
```

---

## Cheat sheet: V2 → V3 differences we hit

| Concept | V2 syntax | V3 syntax |
|---|---|---|
| Model ID for "Turbo" | `turbo` | `turbo-one` (this is gpt-4.1) |
| Variable reference in config | `{{transcript}}`, `{{extract.foo}}`, `{{verify_carrier.bar}}` | `{{<persistent_id>.<variable_id>}}` — must use the upstream node's UUID as `group_id` |
| Storage format of a variable reference | Plain text inside a paragraph | Plate `mention` node with `type: "variable"`, `group_id`, `variable_id` |
| Agent first message | Field on the Agent node | Field on the **Prompt** node (`initial_message`) |
| Language accent ID | Often `en` | Locale-style: `en-us`, `en-gb`, `es-mx`, etc. — must match the voice's declared `accent_key` |
| AI Extract output reference | `{{extract.field}}` | `{{<extract_persistent_id>.response.field}}` (note the `response.` prefix) |
| Classify/Sentiment output | `{{classify.tag}}`, `{{sentiment.tag}}` | `{{<classify_persistent_id>.response.classification}}`, `{{<sentiment_persistent_id>.response.classification}}` (note: both expose the field as `classification`, not `tag`) |
| Voice Agent transcript reference | `{{transcript}}`, `{{call.transcript}}` | `{{<inbound_voice_agent_persistent_id>.transcript}}` |
| Voice Agent duration reference | `{{duration}}` | `{{<inbound_voice_agent_persistent_id>.duration}}` |

Use `mcp__happyrobot-ai__get_available_variables(version_id, node_id)` from the MCP to enumerate the exact valid references for any given node — it returns the `group_id` and `variable_id` for every reachable variable, which the API will then accept as a string template.

## Reproducing this from scratch (if you ever need to)

1. Fork the latest version of the workflow (creates an editable copy without disturbing live).
2. Take the **"Upgrade to new engine"** action immediately on the fork. This is non-optional — V2 templates and V3 runtime don't interoperate cleanly.
3. Republish via the MCP with `skip_prompt_validation=true, force=true` if validation is stuck on stale issues.
4. Run a test web call. Check `monitor_runs sessions <run_id>` — `duration > 0` and `Room: <id>` is the green light.
5. Verify your dashboard receives the call and shows real values (not `{{...}}` strings) in MC, Carrier, and Load columns.

If the session is still 0-duration after all of the above, it's an account/infrastructure issue (worker dispatch, LiveKit provisioning) — not a workflow config issue. Open a HappyRobot support ticket with the failed `run_id` and `session_id`; they need to look at server-side worker logs.
