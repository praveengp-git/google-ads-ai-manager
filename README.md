# Google Ads AI Manager

Manage Google Ads with AI. MCP for reads, dated Python scripts for writes, automated monitoring, human approval for every change.

This repository is a public template for running Google Ads operations with AI coding agents such as Claude Code, Codex, or similar tools.

The core idea is simple:

- Use MCP for read-only account analysis.
- Use Python scripts for all writes.
- Keep every write as a dated file.
- Run every script in dry-run mode before applying.
- Require a human to approve money-moving changes.

## Why This Exists

Creating properly segmented search campaigns is slow in the Google Ads UI.

Google Ads Editor handles bulk uploads well when the structure is straightforward. It is less comfortable when the workflow needs conditional logic:

- Different negative keywords per campaign or geography.
- Keyword decisions cross-checked against GA4 conversion data.
- Ad copy generated from structured audience and positioning inputs.
- Reusable safety checks before live account changes.
- A permanent audit trail outside the Google Ads UI.

This repo demonstrates a pattern I use for that kind of work.

## The Approach

The system uses a read/write split.

MCP is used for reads: campaign performance, search terms, keyword issues, and routine account monitoring.

Python scripts are used for writes: campaign creation, negative keyword additions, bid changes, and other account mutations.

That split is intentional. Google's official Ads MCP tooling is read-oriented. Third-party MCP servers can support writes, but I still prefer version-controlled scripts for account changes because they create a durable artifact I can review, diff, rerun, or hand to a different AI tool later.

The AI can help write the script. The script is the system of record.

## Architecture

```text
                         READ PATH

   Google Ads Account
          |
          v
   MCP Server / GAQL
          |
          v
   AI Agent Review
   - campaign performance
   - search terms
   - keyword gaps
   - budget pacing


                         WRITE PATH

   Human Request
   "Add these negatives"
   "Create this campaign"
   "Raise these bids"
          |
          v
   AI Coding Agent
   writes dated Python script
          |
          v
   Dry Run Preview
   no account mutation
          |
          v
   Human Approval Gate
          |
          v
   python scripts/<date_script>.py --apply
          |
          v
   Google Ads API
          |
          v
   Live Account Change
   plus local script audit trail


                         MONITORING LOOP

   Scheduled Routine
          |
          v
   Google Ads MCP reads + GA4 API reads
          |
          v
   Cross-reference:
   - spend
   - CTR
   - search terms
   - conversion events
   - campaign/ad group attribution
          |
          v
   Report:
   recommendations awaiting human go-ahead
```

## Human Approval Gates

These actions should never be applied automatically:

- Budget changes.
- Campaign go-live.
- Negative keyword additions.
- Ad copy updates.
- Bid changes above a defined threshold.
- Any change that can materially affect spend or lead quality.

The template scripts default to dry-run mode. You must pass `--apply` before any write reaches Google Ads.

## Repository Structure

```text
.
|-- README.md
|-- CLAUDE.md
|-- AGENTS.md
|-- .env.example
|-- .mcp.json.example
|-- keywords/
|   |-- _negative_keywords_master.csv
|   `-- sample_keywords.csv
|-- reports/
|   `-- sample_routine_report.md
`-- scripts/
    |-- create_campaign_template.py
    |-- add_negatives_template.py
    |-- update_template.py
    |-- query_ga4_events_template.py
    `-- run_routine.sh
```

## Stack

- Python
- `google-ads` Python library
- Google Analytics Data API
- Claude Code, Codex, or another AI coding agent
- MCP for read-only Google Ads queries

## Setup

### 1. Create a Google Cloud project

Create a project in [Google Cloud Console](https://console.cloud.google.com/) and enable:

- [Google Ads API](https://console.cloud.google.com/flows/enableapi?apiid=googleads.googleapis.com)
- [Google Analytics Data API](https://console.cloud.google.com/flows/enableapi?apiid=analyticsdata.googleapis.com)

### 2. Create OAuth credentials

Create an OAuth Client ID for a desktop app in the [Google Cloud Credentials page](https://console.cloud.google.com/apis/credentials).

Use that client to generate a refresh token for the Google account that has access to your Google Ads manager account and GA4 property. See the [OAuth setup guide](https://developers.google.com/google-ads/api/docs/get-started/oauth-cloud-project) for details.

### 3. Get a Google Ads developer token

You need a [Google Ads Manager (MCC) account](https://ads.google.com/home/tools/manager-accounts/) to get a developer token.

Once you have one, go to [API Center](https://ads.google.com/aw/apicenter) to find your token and apply for the access level you need. See [developer token docs](https://developers.google.com/google-ads/api/docs/get-started/dev-token) for details.

Developer token approval can take a few days. The API itself is free. Your normal ad spend still applies.

### 4. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 5. Configure environment variables

Copy `.env.example` to `.env` and fill in your own values.

Never commit `.env`, OAuth client secrets, refresh tokens, service account files, or downloaded credential JSON files.

### 6. Configure MCP reads

Copy `.mcp.json.example` to `.mcp.json` and adjust the command/env fields for your MCP server.

The official Google Ads MCP server is at [googleads/google-ads-mcp](https://github.com/googleads/google-ads-mcp). Follow its README for installation.

Use MCP to inspect the account. Use scripts for writes.

### 7. Run scripts in dry-run mode first

```bash
python scripts/create_campaign_template.py
python scripts/add_negatives_template.py
python scripts/update_template.py
```

Dry-run mode prints the plan and does not mutate the account.

Apply only after review:

```bash
python scripts/add_negatives_template.py --apply
```

## Notes

This repo uses a fictional Acme Corp SaaS account. Replace the campaign specs, keywords, URLs, and conversion event names with your own data before running anything against a live account.

Start with low budgets and paused campaigns. Review everything in the Google Ads UI before enabling.

## References

- [Google Ads API docs](https://developers.google.com/google-ads/api/docs/start)
- [Google Analytics Data API docs](https://developers.google.com/analytics/devguides/reporting/data/v1)
- [Google Ads MCP server](https://github.com/googleads/google-ads-mcp)
- [google-ads Python library](https://github.com/googleads/google-ads-python)

