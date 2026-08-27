# Prompt Changelog

## triage_v1 (current)
- Initial version. Enforces enum compliance, KB grounding, untrusted-input
  handling for embedded instructions, and explicit uncertainty statements.

## account_health_v1 (current)
- Initial version. Enforces verbatim quote grounding, FACT/INFERENCE/
  RECOMMENDATION separation, and explicit handling of missing account/ticket
  data.

Both prompt versions are recorded in the `metadata.prompt_version` field of
every structured output and in `eval_report.json`, so a regression in
output quality after a prompt edit can always be traced to a specific
version.
