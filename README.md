# EdgeRoute

![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue?style=flat-square&logo=python&logoColor=white)

## Introduction

EdgeRoute is a small service that tells a video player which CDN to fetch a stream from. It's
also an exercise. You'll join a team that has already started the work, pick up their tickets,
and deliver them the way a professional software team does: in branches, through pull requests,
behind a CI pipeline, with tests, documentation and written-down decisions.

You're expected to use a coding agent (Claude Code or similar) as much as you like. You'll build
both sides of a working product, the API and a web console on top of it, and see how quickly an
agent gets you something that runs. What we are assessing is your judgement, not your typing:
what you ask for, what you check, what you accept and what you push back on.

## Background

Northwind Media is a fictional broadcaster that streams its live channels to viewers across Europe
through three commercial CDNs. Today traffic is split across those CDNs with fixed weights. When
one of them degrades in a region, someone in operations notices (eventually) and edits the weights
by hand, often at 3am.

EdgeRoute replaces that. Before playback starts, the player calls `GET /api/v1/steer` with the
viewer's region and the asset it wants, and gets back the URL to use. Probe agents running in each
region request a test object from every CDN every few minutes and export the results. EdgeRoute
should use those measurements to stop sending viewers to a CDN that is failing.

A colleague built the first version: CDN management, weighted steering and the start of probe
ingestion. They have since moved to another team. These tickets are now yours:

- **NWM-101: CI that tells the truth.** Our CI pipeline has been green for weeks. Make it a real
  quality gate. It must run on every pull request into `main` and every push to `main`, install
  the project the same way developers do, run the linter and the test suite, and fail the build
  when either fails. Add a minimum test coverage of 80%. Protect `main` so that nothing reaches it
  without a pull request and a passing pipeline. In the PR description, explain what each gate
  protects us from.
- **NWM-102: Probe ingestion.** Finish `POST /api/v1/probes/import`. It must accept uploads from
  both generations of probe agent, CSV (v1) and JSON Lines (v2), described in
  [vendor-feeds](docs/vendor-feeds.md). Validate each row, normalise TTFB to milliseconds, store
  valid probes, and report every rejected row with the reason. Importing the same file twice must
  not create duplicates, and a probe that appears in both exports must be stored once. Sample
  exports are in `data/`. A partial implementation exists in `app/probes/ingest.py`, with tests.
  Review it carefully before building on top of it.
- **NWM-103: Health-aware steering.** Extend the routing endpoint at `/api/v1/route` so it only
  sends viewers to healthy CDNs. A CDN is unhealthy in a region when, over its last
  `EDGEROUTE_PROBE_WINDOW` probes in that region, the error rate is above 2% or the p95 TTFB is
  above 800 ms. Unhealthy CDNs receive no new sessions. A viewer who sends the same `session_id`
  must keep getting the same CDN while it stays healthy, so players don't hop between CDNs
  mid-stream. Decide what happens when every CDN is unhealthy, or when there is no probe data yet,
  and record the decision as an ADR (see `docs/adr/`).
- **NWM-104: Ship it.** A teammate must be able to run the service with one command, in a
  container, without losing data when it restarts. Add a `/readyz` endpoint that reports whether
  the service can actually serve (for example, whether the database is reachable). Add a release
  workflow: pushing a tag like `v1.2.3` builds the container image and publishes it to the GitHub
  Container Registry, tagged with that version. Finish by releasing `v0.1.0`.
- **NWM-105: Code review.** Inês opened PR #1 just before going on leave. Review it the way you
  would review a teammate's work: leave a GitHub review with comments on specific lines, then
  approve or request changes. Decide what should happen to the PR, and say why in the review.
  PR #1 lives in the original repository (`LunaeMons/edgeroute`), not in your fork: review it
  there.
- **NWM-106: Scaling note.** Northwind wants EdgeRoute in front of every playback start. At a big
  football final that is 50,000 steering requests per second, across 20 regions, with 500 probe
  agents reporting. Write `docs/design/scaling.md` (one or two pages, diagrams welcome): what
  breaks first in the current design, what you would change, how you would deploy new versions
  without dropping viewers, what you would monitor and alert on, and how you would roll back. No
  code is needed for this one.
- **NWM-107: Operations console.** Operations shouldn't need curl or Swagger to run EdgeRoute.
  Build a web front end for the operations team that talks to the EdgeRoute API. An operator must
  be able to:
  - see every CDN with its weight and whether it is enabled, and change both;
  - see the health of each CDN in each region (error rate, p95 TTFB, healthy or not, using the
    rules from NWM-103);
  - upload a probe export and see which rows were rejected and why;
  - enter a region and a session ID and see where that viewer would be steered.

  Pick the stack you prefer (for example React with Vite, or pages served by FastAPI) and record
  the choice in an ADR. The console lives in this repo, is linted, built and tested in CI like the
  API, and starts together with the API using the one command from NWM-104. The admin token must
  never be written into the front-end code or the built bundle. Expect to change the API where
  the console needs something it doesn't offer yet.

> **TIP** Include the ticket number in your branch names, commit messages and PR titles.

## Getting started

### 1. Fork the repository

You work in your own copy of this repository, a **fork**, and that is also how you hand the work
in. You'll need a free [GitHub account](https://github.com/signup).

1. Click **Fork** at the top of this page and create the fork under your account (keeping only
   the `main` branch is fine). Everything else in this README, including "push", "pull request",
   "CI" and "`main`", refers to **your fork** from here on.
2. Clone your fork, not this repository: `git clone https://github.com/<you>/edgeroute.git`.
3. Turn on the features that GitHub switches off for forks:
   - **Actions** tab → *I understand my workflows, go ahead and enable them*. Without this, no
     pipeline will ever run.
   - **Settings → General → Features → Issues**, so you can track work and record decisions.
4. Point the GitHub CLI at your fork, if you use it: `gh repo set-default <you>/edgeroute`.

> **TIP** When you open a pull request in a fork, GitHub proposes the *original* repository as the
> base. Change **base repository** to `<you>/edgeroute` every time. Your pull requests go into
> your own `main`, never into `LunaeMons/edgeroute`.

You own your fork, so you hold the admin rights the tickets need (for example, the branch rules in
NWM-101).

### 2. Run it

Read the [contributing guide](docs/CONTRIBUTING.md) first: it describes how this team works with
Git and pull requests. Then follow the [quickstart](docs/quickstart.md) to run the project. In
short:

```bash
make install
make seed
make run      # then open http://localhost:8080/docs
```

New to working in a software team? [The primer](docs/primer.md) explains the why behind branches,
pull requests, CI and CD, with links for further reading.

## Tasks

- [ ] **NWM-101** CI that tells the truth
- [ ] **NWM-102** Probe ingestion
- [ ] **NWM-103** Health-aware steering
- [ ] **NWM-104** Ship it
- [ ] **NWM-105** Code review
- [ ] **NWM-106** Scaling note
- [ ] **NWM-107** Operations console (front end)
- [ ] **Documentation**: keep the README, quickstart and other docs accurate as you change things.
  New endpoints, environment variables, dependencies and setup steps must be documented so that
  another developer can pick up where you left off.
- [ ] **AI log**: keep a short `AI_LOG.md`. For each ticket, note what you asked the agent to do,
  what you checked, and what you changed or rejected, and why. A few lines per ticket is enough.

Tickets are written by people. They can be incomplete or contradict each other, as in any real
team. When something is unclear, ask us in an issue on the original repository
([LunaeMons/edgeroute](https://github.com/LunaeMons/edgeroute/issues)), or make a decision and
write down why (an issue in your fork, an ADR or the PR description).

## How to work in this repo

- One branch and one pull request per ticket, inside your fork. Never push directly to `main`.
- CI must be green before you merge. There is no reviewer on call, so you merge your own PRs, but
  write each PR as if someone will review it tomorrow.
- Small, meaningful commits. Your Git history is part of what we review.

## Submitting your work

All your work stays in your fork. When you're done:

1. Release `v0.1.0` from your fork (NWM-104), and make the container package public (**Packages**
   → the package → **Package settings** → *Change visibility*) so we can pull the image.
2. Open an issue titled **Submission** on the
   [original repository](https://github.com/LunaeMons/edgeroute/issues) with:
   - the link to your fork;
   - a short note: what you did, what you didn't get to, and what you would do next.

Don't open pull requests against the original repository: we review your fork as it is, including
its history, pull requests, CI runs and issues.

There's no deadline. Most people need three or four focused evenings. If you don't finish
everything, that's fine: tell us what you would have done.

> **TIP** We review your Git history and pull requests, the CI runs, your tests, the decisions you
> wrote down, the documentation, and your AI log. If you're unsure, aim for the work you'd be
> proud to hand over to a colleague.

## Copyright

Training material. You may fork it to do the exercise. Please don't copy or redistribute it for
anything else. See [LICENSE](LICENSE).
