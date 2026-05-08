# Loom Teleprompter Script

Paste the block below into Loom's teleprompter. It's the spoken script, broken into
short readable lines, with `[STAGE: …]` cues for what to do on screen.

The action plan (timing, pre-flight, etc.) is in `demo_script.md`. This file is just
the words.

---

## ✂️ START COPY HERE ✂️

[STAGE: README on screen]

Hi, I'm Tim. This is the inbound carrier-sales proof of concept I built
for HappyRobot's FDE case study.

The system has three pieces.

A HappyRobot voice agent that handles the conversation.

A FastAPI backend that owns the business logic — FMCSA verification,
load matching, and a server-enforced negotiation policy.

And a custom React dashboard that surfaces the KPIs a freight broker
actually cares about.

Everything runs as one Docker image on Fly dot io with HTTPS and
API-key auth.

[STAGE: scroll to repo layout, then to backend/app/api]

The negotiation rules live in code, not in a prompt — so the agent
literally cannot commit the broker to a price below the floor. That's
testable, repeatable, and unit-tested.

[STAGE: switch to HappyRobot editor]

Here's the workflow on the HappyRobot side.

Web-call trigger at the top. Inbound voice agent in the middle.

Four tools — verify carrier, find available loads, search loads by
lane, and evaluate offer. Each one calls a webhook into the FastAPI
backend.

After the call ends, three AI nodes — Classify, Sentiment, Extract —
parse the transcript. Then POST log_call ships everything to the
backend for persistence.

[STAGE: open Prompt node briefly]

The system prompt has three hard rules: always verify before pitching,
never go beyond three negotiation rounds, never promise below the
floor that evaluate offer returns.

HappyRobot owns the conversation. The API owns the rules of the game.

[STAGE: switch to web-call test panel, dashboard visible side-by-side]

Now let's see it run. I'll do two live calls.

[STAGE: click Start call]

[CALL A — let the agent greet, then say:]

Hi, I'm calling about a load.

[Agent asks for reference number. Say:]

Yes, R E F one zero zero one.

[Agent asks for MC number. Say:]

MC one two three four five six.

[Agent verifies, confirms carrier name. Say:]

Yes.

[Agent pitches the load. Say:]

Sounds good, I'll take it at the rate.

[Agent confirms booking. Wait ~4 seconds for silence-hold to end the call.]

[STAGE: dashboard tab]

That's the happy path. The agent verified the carrier through F M C S A,
pulled the load, confirmed the rate, and booked it. The call landed in
the dashboard with the transcript, the extracted fields, and the
agreed price.

[STAGE: web-call panel — second call]

One more call to show the ineligible-carrier path.

[Click Start. Agent greets. Say:]

Hi, I'm calling about R E F one zero zero two.

[Agent asks for MC. Say:]

MC nine nine nine nine nine nine.

[Agent verifies, declines politely. Let it close.]

[STAGE: dashboard tab, click Refresh]

Both calls are now in the dashboard.

KPI row at the top: total calls went up, conversion rate ticked,
average rounds updated, average sentiment held steady.

Outcome distribution shows booked, declined, and ineligible carrier
all represented.

[STAGE: click the most recent call row]

Click any row and the drawer opens with the full transcript and every
extracted field. Filters at the top, CSV export at the right.

This is what an ops manager opens with their morning coffee.

[STAGE: scroll to top]

That's the demo.

Next steps would be live transfer integration with the broker's
existing dialer, dynamic pricing floors driven by lane and day-of-week,
and a TMS sync so the load board stays current.

The repo and the dashboard are linked in the README. Thanks for
watching.

## ✂️ END COPY HERE ✂️
