# Working like a software team: a primer

You already know how to design systems that must not fall over. This primer covers the habits
that let a team change software every day without breaking it, and why each one exists. Each
section ends with something to read if you want to go deeper.

## 1. Git: history is documentation

- **A commit is one logical change**, with a message that says why. Six months from now,
  `git log` and `git blame` are how someone (often you) finds out why a line exists. "fix stuff"
  tells them nothing. `NWM-102 fix(probes): treat status 0 as a timeout` tells them everything.
- **A branch per change** keeps unfinished work away from `main`, so `main` stays releasable.
- **A pull request (PR)** is where a change is proposed, explained, checked by CI and reviewed
  before it joins `main`. Its description is a short design note: what, why, how it was tested,
  how to roll it back.
- **Never rewrite shared history** (`git push --force` on `main`). Rewriting your own branch
  before it is merged is fine.
- **Git never forgets.** Anything ever committed stays in the history, even after you delete the
  file, unless the history is rewritten. Treat a secret that was ever pushed as leaked: rotate it.

Read: [Pro Git, chapters 2 and 3](https://git-scm.com/book/en/v2) ·
[Conventional Commits](https://www.conventionalcommits.org/)

## 2. Tests are an executable specification

- A test states what the code must do, and checks it on every change, for free, forever.
- A test is only worth something if it **can fail**. A test that passes whatever the code does,
  or that is skipped, gives false confidence, which is worse than having no test.
- Test the edges, not only the happy path: empty input, zero, missing fields, duplicates, the
  failure modes you would ask about in a design review.
- When you fix a bug, first write the test that fails because of it, then fix the code and watch
  the test pass. The bug can't silently come back.

Read: [Martin Fowler, Test Pyramid](https://martinfowler.com/bliki/TestPyramid.html)

## 3. Continuous Integration (CI)

CI runs the same checks (install, lint, tests) on every change, on a clean machine, before the
change reaches `main`. Why it matters:

- **Fast feedback.** Problems surface minutes after they are written, not weeks later.
- **One standard for everyone.** It doesn't matter what is installed on your laptop.
- **A trustworthy `main`.** If `main` is always green, anyone can branch from it or release it.

A green build is only as meaningful as the checks it actually runs and enforces. A pipeline that
can't go red is decoration.

Read: [GitHub Actions: Understanding workflows](https://docs.github.com/en/actions/writing-workflows) ·
[Martin Fowler, Continuous Integration](https://martinfowler.com/articles/continuousIntegration.html)

## 4. Continuous Delivery (CD)

- **Build once, deploy many.** CI produces one immutable artifact (here, a container image) and
  that exact artifact is promoted from test to production. You never rebuild "the same thing" per
  environment.
- **Versions are tags.** A Git tag like `v1.4.0` marks exactly what was released, following
  [Semantic Versioning](https://semver.org/): MAJOR for breaking changes, MINOR for features,
  PATCH for fixes.
- **Rollback is a deploy of the previous version.** That only works when every release is a
  tagged, immutable artifact.
- **Configuration comes from the environment, not the image**, so the same image runs everywhere
  and secrets never end up inside it.

Read: [The Twelve-Factor App](https://12factor.net/) (especially III Config, V Build/release/run,
IX Disposability)

## 5. Systems thinking for services

You know this territory from CDNs. The same questions apply to a small API:

- **What happens when a dependency fails?** Fail open (keep serving, possibly degraded) or fail
  closed (refuse)? For each failure, which is worse for the viewer?
- **Liveness vs readiness.** "The process is running" and "the process can serve requests" are
  different questions, and orchestrators act on them differently.
- **State.** Where does it live, what happens when there are ten instances instead of one, and
  what happens when the container restarts?
- **Observability.** What would you need to see at 3am to know what is wrong?

Read: [Google SRE book: Monitoring distributed systems](https://sre.google/sre-book/monitoring-distributed-systems/) ·
[Handling overload](https://sre.google/sre-book/handling-overload/)

## 6. Front end and back end

- **The API is a contract.** FastAPI publishes it as OpenAPI (`/openapi.json`, browsable at
  `/docs`). A front end built against that contract, ideally with a typed client generated from
  it, breaks at build time rather than in front of a user when the API changes.
- **Everything sent to the browser is public.** Code, configuration and anything baked into the
  bundle can be read by whoever opens the page. Secrets stay on the server, or come from the user
  at runtime.
- **Browsers enforce origins.** A page served from one origin (scheme, host and port) calling an
  API on another is subject to CORS rules. Understand them before you loosen them.
- **A front end is a build artifact too.** It gets linted, tested and built in CI, versioned and
  shipped like the API. Decide whether the API serves the built files or something else does.
- **Test what the user sees.** A few end-to-end tests that drive a real browser (for example with
  Playwright) catch the integration problems that unit tests on either side miss.

Read: [MDN: CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS) ·
[Vite: Getting started](https://vite.dev/guide/) ·
[Playwright](https://playwright.dev/docs/intro)

## 7. Working with a coding agent

- **Give it context and constraints**: the ticket, the relevant files, the conventions in
  CONTRIBUTING.
- **Ask it to explain before it edits.** "Read `ingest.py` and the sample files and tell me what
  you think is wrong" is often worth more than "implement NWM-102".
- **Review every diff as if a stranger wrote it.** You are accountable for what you commit.
- **Run things yourself.** Run the tests, call the endpoint, import the real sample file, read the
  output.
- **Watch for an agent "fixing" a failing test by changing the test.** Sometimes the test is
  wrong. Make sure you know which one it is.
- **Keep the agent's changes small**, one ticket and one concern at a time, so they stay reviewable.
- **Hold its code to the team's standard.** Agents write code fast, so readability is what keeps
  you in control of it. Ask for docstrings and comments that follow CONTRIBUTING, then read
  them. A docstring that doesn't match the code means either the docstring or the code is wrong.

Read: [Claude Code best practices](https://www.anthropic.com/engineering/claude-code-best-practices)
