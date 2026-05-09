# Agent Instructions

This repo is intended for Codex, Claude Code, and similar AI coding agents.

## Operating Principle

You may help generate and modify scripts, but you must not apply live Google Ads changes without explicit human approval.

## Read vs Write

Reads:

- Use MCP for Google Ads reads where available.
- Use `scripts/query_ga4_events_template.py` for GA4 reads.
- Summarize findings and recommend actions.

Writes:

- Create or edit Python scripts.
- Use dry-run mode first.
- Require `--apply` for live mutations.
- Never bypass the script layer for Google Ads writes.

## Script Workflow

When asked to make a change:

1. Create a dated script from the closest template.
2. Keep the change set small and reviewable.
3. Print a dry-run preview.
4. Explain what will change.
5. Wait for explicit approval.
6. Run with `--apply` only after approval.
7. Update the master CSV when adding negative keywords.
8. Report the Google Ads request ID if the API returns an error.

## Safety Rules

- Campaigns created by scripts must be paused by default.
- Do not change budgets unless the user specifically asks.
- Do not enable campaigns unless the user specifically asks.
- Do not add negative keywords without showing the list first.
- Do not delete entities unless the user specifically asks.
- Prefer pausing over deleting.
- Keep secrets out of the repo.

## Sanitization Rules

This is a public template repo. Do not add:

- Real customer IDs.
- Real MCC IDs.
- Real GA4 property IDs.
- API keys.
- OAuth secrets.
- Client names.
- Private search-term exports.
- Private domain names.

Use the fictional Acme Corp SaaS example unless the user explicitly provides sanitized replacement data.

## Code Style

- Keep scripts plain Python.
- Keep dependencies minimal.
- Prefer dataclasses for campaign specs.
- Keep helper functions explicit and easy to inspect.
- Catch `GoogleAdsException` and print request IDs, error codes, messages, and field paths.
- Do not hide planned mutations behind vague abstractions.

