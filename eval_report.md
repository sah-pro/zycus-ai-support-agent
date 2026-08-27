# Evaluation Report

- Timestamp: 2026-08-27T10:00:49.135909+00:00
- LLM provider: mock
- Overall score: **0.9525**

## Task 1 -- Triage (8/8 passed, avg score 0.9575)

| Case | Passed | Score | Notes |
|---|---|---|---|
| t1_clear_p1_incident | ✅ | 1.0 | - |
| t1_billing_request | ✅ | 0.93 | - |
| t1_integration_issue | ✅ | 0.8 | - |
| t1_known_kb_error_code | ✅ | 1.0 | - |
| t1_onboarding_howto | ✅ | 0.93 | - |
| t1_ambiguous_mixed_signals | ✅ | 1.0 | - |
| t1_adversarial_prompt_injection | ✅ | 1.0 | - |
| t1_adversarial_empty_body | ✅ | 1.0 | - |

## Task 2 -- Account Health (7/7 passed, avg score 1.0)

| Case | Passed | Score | Notes |
|---|---|---|---|
| t2_healthy_account | ✅ | 1.0 | - |
| t2_at_risk_account | ✅ | 1.0 | - |
| t2_churning_account | ✅ | 1.0 | - |
| t2_account_with_matched_tickets | ✅ | 1.0 | - |
| t2_account_zero_tickets | ✅ | 1.0 | - |
| t2_incomplete_data_null_nps | ✅ | 1.0 | - |
| t2_adversarial_unknown_account | ✅ | 1.0 | - |

## Guardrails -- adversarial 'bad LLM' cases (9/9 passed, avg score 0.9)

Adversarial 'bad LLM' cases: each injects a deliberately misbehaving LLM client and asserts the deterministic guardrail layer, not the model, produced the correct final result.

| Case | Passed | Score | Notes |
|---|---|---|---|
| g1_bad_llm_p1_downgrade_rejected | ✅ | 0.95 | - |
| g1_bad_llm_invalid_category_rejected | ✅ | 0.95 | - |
| g1_bad_llm_invalid_urgency_rejected | ✅ | 0.95 | - |
| g1_bad_llm_hallucinated_kb_rejected | ✅ | 0.95 | - |
| g1_bad_llm_malformed_json_degrades | ✅ | 0.9 | - |
| g1_bad_llm_missing_fields_degrades | ✅ | 0.9 | - |
| g2_bad_llm_fabricated_quote_rejected | ✅ | 1.0 | - |
| g2_bad_llm_malformed_json_degrades | ✅ | 0.75 | - |
| g2_bad_llm_missing_fields_degrades | ✅ | 0.75 | - |
