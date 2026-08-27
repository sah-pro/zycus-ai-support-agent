# Loom Walkthrough Script

Core script below runs ~5:45, inside the assignment PDF's 3–6 minute
guidance. The optional "if time allows" beats after sections 2, 5, and 6
let this comfortably stretch to ~7–10 minutes (matching the longer window
mentioned in the follow-up email) without changing what's actually
required — the live Task 1/Task 2 demo and the evaluation walkthrough are
the same either way.

## 1. Problem understanding (30s)
"This is a support triage and TAM account-health tool built on the supplied
mock dataset — 500 tickets, 50 accounts, 8 knowledge-base docs. Two
problems: help support engineers classify and respond to tickets faster,
and help TAMs prep for QBRs in minutes instead of 30+."

## 2. Architecture (60s)
- Walk through the README's mermaid diagram.
- Call out the two pipelines share the same LLM-provider abstraction
  (`LLMClient`), the same BM25 retrieval index, and the same evaluation
  harness.
- Mention the mock-by-default design: "Everything you're about to see runs
  with zero API calls — `LLM_PROVIDER=mock` is the default, and switching
  to real Anthropic calls is a one-line env var change."
- *If time allows:* briefly show the repository layout (`src/agents`,
  `src/retrieval`, `src/evaluation`, `src/prompts`) and note the prompt
  versioning file (`src/prompts/CHANGELOG.md`).

## 3. Task 1 live demo (60s)
```
python app.py triage --file examples/ticket.json
```
- Point out: deterministic error-code detection (`ERR_CONNECTION_TIMEOUT`)
  feeding into `known_issue: true`, the KB match with document/section/score,
  the routing decision, and the draft response.
- Optionally hit `POST /triage` via curl with `python app.py serve` running,
  to show the same result over HTTP.

## 4. Task 2 live demo (60s)
```
python app.py account-health --account-id ACC-3336
```
- Point out the executive summary synthesizing health/trend/ARR/tickets,
  the risk flags each carrying a verbatim quote tied to a real ticket ID or
  escalation note, and the talking points.
- Show `account-health --account-id ACC-00000` to demonstrate graceful
  handling of an unknown account — no crash, a clear explanation instead.

## 5. Evaluation harness (45s)
```
python app.py eval
```
- Open `eval_report.md`: point out per-case pass/fail and scores, that a
  couple of cases score below 1.0 (not gamed to look perfect), and that
  cases are built from real dataset records (name the specific P1 ticket
  and Churning account used).
- *If time allows:* open one of the guardrail ("bad LLM") cases and explain
  that it injects a scripted misbehaving client directly, so the test
  proves the deterministic layer catches bad output rather than just
  hoping the model behaves.

## 6. Evaluation results & key engineering decisions (45s)
- Overall score 0.9525 — Task 1 8/8 (avg 0.9575), Task 2 7/7 (avg 1.0),
  guardrails 9/9 (avg 0.9); mock provider, fully reproducible across runs.
- Highlight one decision in depth: the quote-grounding check in
  `account_health_agent.py` that drops any risk whose quote isn't literally
  present in its source ticket, rather than trusting the LLM's claim.
- *If time allows:* walk through the scoring weights in `scoring.py` and
  explain why schema validity is a hard gate while draft-response tone is
  weighted lowest (most subjective, deliberately not LLM-judged).

## 7. Production considerations (30s)
- Summarize `DESIGN.md`'s three failure modes in one sentence each
  (malformed LLM output, fabricated quotes, prompt injection) and the
  scaling bottleneck (LLM throughput/rate limits at 10x volume).

## 8. Close (15s)
"Full requirement matrix and clean-install verification is in
docs/AUDIT.md. Happy to go deeper on any part."
