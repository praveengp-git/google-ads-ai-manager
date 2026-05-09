#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

echo "=== GA4 conversion event check ==="
python scripts/query_ga4_events_template.py

cat <<'EOF'

=== Google Ads MCP queries to run in your AI agent ===

Campaign performance:
SELECT campaign.name, metrics.impressions, metrics.clicks, metrics.ctr,
       metrics.average_cpc, metrics.conversions, metrics.cost_micros
FROM campaign
WHERE segments.date DURING LAST_7_DAYS
ORDER BY metrics.cost_micros DESC

Ad group performance:
SELECT campaign.name, ad_group.name, metrics.impressions, metrics.clicks,
       metrics.ctr, metrics.average_cpc, metrics.conversions
FROM ad_group
WHERE segments.date DURING LAST_7_DAYS
ORDER BY metrics.impressions DESC

Search terms:
SELECT search_term_view.search_term, metrics.impressions, metrics.clicks,
       metrics.ctr, metrics.conversions, campaign.name, ad_group.name
FROM search_term_view
WHERE segments.date DURING LAST_7_DAYS
ORDER BY metrics.impressions DESC
LIMIT 50

After reading the MCP output, produce a report using reports/sample_routine_report.md
as the format and wait for human approval before creating any write script.
EOF

