# Final Repository Audit

## Requirement matrix

| Requirement | Implemented | Tested | Evidence |
|---|---|---|---|
| Task 1 — Triage pipeline | YES | YES | `src/agents/triage_agent.py`, `tests/test_triage_agent.py` |
| Task 1 — REST endpoint | YES | YES | `src/api/main.py` (`POST /triage`), `tests/test_api.py` |
| Task 1 — KB retrieval | YES | YES | `src/retrieval/`, `tests/test_retrieval.py` |
| Task 2 — Account health pipeline | YES | YES | `src/agents/account_health_agent.py`, `tests/test_account_health_agent.py` |
| Task 2 — REST endpoint | YES | YES | `src/api/main.py` (`POST /account-health`), `tests/test_api.py` |
| Task 2 — Quote grounding (no fabrication) | YES | YES | `account_health_agent.py::_quote_is_grounded`, verified in `test_account_health_agent.py` |
| Task 2 — Determinism | YES | YES | fixed temperature, fixed reference date, stable sort; `test_deterministic_output_for_same_input` |
| Task 3 — Evaluation harness | YES | YES | `src/evaluation/`, `tests/test_evaluation.py` |
| Task 3 — ≥5 cases/task + adversarial | YES | YES | 8 Task 1 cases / 7 Task 2 cases / 9 guardrail ("bad LLM") cases, each category includes ≥1 adversarial case |
| Task 3 — Scoring 0–1 + pass/fail + report | YES | YES | `eval_report.json`, `eval_report.md` |
| Task 4 — Design note | YES | N/A | `DESIGN.md` |
| README | YES | N/A | `README.md` |
| Eval report file in repo | YES | YES | `eval_report.json` |
| `.env.example` (no real secrets) | YES | N/A | `.env.example` |
| `.gitignore` excludes `.env` | YES | N/A | `.gitignore` |
| Clean install works (`venv` + `pip install -r requirements.txt`) | YES | YES | see "Clean install log" below |
| No secrets in repo | YES | YES | see "Secret audit" below |
| Mock provider requires no API key | YES | YES | default `LLM_PROVIDER=mock`; full test suite + eval run with no key set |
| Anthropic provider behind env var | YES | YES | `src/agents/llm_client.py::AnthropicLLMClient`, only instantiated when `LLM_PROVIDER=anthropic` |
| Prompt versioning | YES | N/A | `src/prompts/*_v1.txt`, `src/prompts/CHANGELOG.md` |
| Structured logging, no raw content logged | YES | N/A | `src/utils/logging.py` |
| Input validation (account_id, empty body) | YES | YES | `src/api/main.py`, `tests/test_api.py` |
| CLI entry point | YES | YES | `app.py` (`triage`, `account-health`, `eval`, `serve`) |

## Clean install log

```
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
... (installs cleanly, no errors)
$ python app.py eval
Overall score: 0.9525
Task 1: 8/8 passed
Task 2: 7/7 passed
(guardrails: 9/9 passed, avg 0.9 — see eval_report.md; folded into the
 overall score as the mean of the three category averages)
Report written to eval_report.json and eval_report.md
$ python -m pytest -q
48 passed in 0.50s
$ python app.py triage --file examples/ticket.json
(valid TriageResult JSON printed)
```

Verified with `ANTHROPIC_API_KEY` unset and no `.env` file present at all —
the mock provider is the true default, not merely documented as one.

## Secret audit

Searched the full repository (excluding `.venv/`) for API-key-shaped
strings, AWS-style keys, and hardcoded password assignments:

```
grep -rniE "sk-ant-|sk-proj-|AKIA[0-9A-Z]{16}|api[_-]?key\s*=\s*['\"][a-zA-Z0-9]{20,}|password\s*=\s*['\"][^'\"]+['\"]" .
→ No secret patterns found.
```

- `.env.example` contains only placeholders (`ANTHROPIC_API_KEY=` with no
  value).
- No `.env` file exists in the repository.
- `.gitignore` excludes `.env`, `.env.*` (while explicitly un-ignoring
  `.env.example`), plus `.venv/`, `__pycache__/`, `*.py[cod]`,
  `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.DS_Store`, editor
  directories, and `*.log`.

## Bonus items implemented

- Prompt versioning + changelog (`src/prompts/CHANGELOG.md`) — the two
  cheapest, highest-value bonus items given the assignment's guidance to
  prioritize core requirements over bonus scope. UI, streaming, and CI
  were deliberately not attempted so as not to trade off core-requirement
  polish, per the assignment's own instruction: "If time is limited, skip
  the UI and make the engineering quality stronger."
