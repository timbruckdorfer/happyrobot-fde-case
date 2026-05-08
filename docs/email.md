# Pre-meeting email — Carlos Becker

**To:** c.becker@happyrobot.ai
**Cc:** <recruiter email>          ← fill in or drop the Cc line at send time
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

- 5-minute walkthrough video: <Loom link>          ← fill in at send time
- Dashboard: <https://happyrobot-fde-tb.fly.dev/>
- Repo: <https://github.com/timbruckdorfer/happyrobot-fde-case>
- Build doc (written as if for a freight-broker prospect): in the repo at
  `docs/build_doc.md`.

The walkthrough runs through two live calls — a happy-path booking on REF1001 and a
negotiation that closes on the second round — followed by a quick tour of the
dashboard, which already shows an ineligible-carrier outcome alongside the two live
ones. Happy to take it deeper on any piece on the call — architecture, the
negotiation policy, security, or what I'd build next.

Looking forward to it.

Best,
Tim
