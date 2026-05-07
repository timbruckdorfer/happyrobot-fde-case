# Pre-meeting email — Carlos Becker

**To:** c.becker@happyrobot.ai
**Cc:** <recruiter email>
**Subject:** Inbound carrier-sales POC — links and what to expect on our call

---

Hi Carlos,

Ahead of our meeting I wanted to share what I built for the inbound carrier-sales use
case so you can poke at it before we connect.

The proof of concept covers the full flow end-to-end: a HappyRobot inbound web-call
agent that vets carriers via the FMCSA API, pitches a matching load, negotiates within
a server-enforced margin band (max 3 rounds), mocks the transfer to a sales rep, and
logs the extracted fields plus an outcome and sentiment classification per call. On top
of that, I built a custom React dashboard that turns the call log into the KPIs a
freight broker would actually use day-to-day — conversion, margin Δ vs listed rate,
average rounds, sentiment, eligible-rate, and outcome / equipment / lane distributions.

Everything is containerized in a single Docker image, deployed on Fly.io with HTTPS and
API-key auth, with reproducible setup via a `Makefile` and a 10-minute runbook.

**Links:**

- Dashboard: <https://happyrobot-fde-tb.fly.dev/>
- Repo: <https://github.com/your-handle/happyrobot-fde>
- HappyRobot workflow: <link from the platform>
- 5-minute walkthrough video: <Loom link>
- Build doc (written as if for a freight-broker prospect): in the repo at
  `docs/build_doc.md`.

On our call I'll do a short setup overview, run three live web calls (happy-path,
counter-offer, and ineligible carrier), and tour the dashboard. Happy to take it deeper
on any piece — architecture, the negotiation policy, security, or what I'd build next.

Looking forward to it.

Best,
Tim
