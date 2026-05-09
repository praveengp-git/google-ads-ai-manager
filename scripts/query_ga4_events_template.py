"""Query GA4 for event counts and Google Ads attribution.

Usage:
    python scripts/query_ga4_events_template.py
"""

from __future__ import annotations

import os
from pathlib import Path

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Filter,
    FilterExpression,
    Metric,
    RunReportRequest,
)
from google.oauth2.credentials import Credentials


ROOT = Path(__file__).resolve().parents[1]
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
CONVERSION_EVENTS = ("generate_lead", "sign_up", "demo_request")


def load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value or value.startswith("YOUR_"):
        raise SystemExit(f"Missing {name}. Copy .env.example to .env and fill it in.")
    return value


def build_client() -> BetaAnalyticsDataClient:
    load_dotenv()
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return BetaAnalyticsDataClient()

    creds = Credentials(
        token=None,
        refresh_token=required_env("GOOGLE_ADS_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=required_env("GOOGLE_ADS_CLIENT_ID"),
        client_secret=required_env("GOOGLE_ADS_CLIENT_SECRET"),
        scopes=SCOPES,
    )
    return BetaAnalyticsDataClient(credentials=creds)


def property_name() -> str:
    return f"properties/{required_env('GA4_PROPERTY_ID')}"


def run_report(
    client: BetaAnalyticsDataClient,
    dimensions: list[str],
    metrics: list[str],
    date_start: str,
    date_end: str,
    event_filter: str | None = None,
) -> list[dict]:
    request = RunReportRequest(
        property=property_name(),
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=date_start, end_date=date_end)],
    )
    if event_filter:
        request.dimension_filter = FilterExpression(
            filter=Filter(
                field_name="eventName",
                string_filter=Filter.StringFilter(
                    value=event_filter,
                    match_type=Filter.StringFilter.MatchType.EXACT,
                ),
            )
        )

    response = client.run_report(request)
    dimension_headers = [h.name for h in response.dimension_headers]
    metric_headers = [h.name for h in response.metric_headers]
    rows: list[dict] = []
    for row in response.rows:
        item = {
            header: value.value
            for header, value in zip(dimension_headers, row.dimension_values, strict=True)
        }
        item.update(
            {
                header: value.value
                for header, value in zip(metric_headers, row.metric_values, strict=True)
            }
        )
        rows.append(item)
    return rows


def fmt_table(rows: list[dict], columns: list[str]) -> str:
    if not rows:
        return "  (no data)"
    widths = {
        column: max(len(column), max(len(str(row.get(column, ""))) for row in rows))
        for column in columns
    }
    sep = "  "
    header = sep.join(column.ljust(widths[column]) for column in columns)
    lines = [header, "-" * len(header)]
    for row in rows:
        lines.append(sep.join(str(row.get(column, "")).ljust(widths[column]) for column in columns))
    return "\n".join(lines)


def main() -> None:
    client = build_client()

    print("\n=== 1. ALL EVENTS - last 14 days ===")
    rows = run_report(
        client,
        dimensions=["eventName"],
        metrics=["eventCount", "totalUsers"],
        date_start="14daysAgo",
        date_end="yesterday",
    )
    rows.sort(key=lambda row: -int(row["eventCount"]))
    print(fmt_table(rows, ["eventName", "eventCount", "totalUsers"]))

    print("\n=== 2. CONVERSION EVENTS by source / medium ===")
    for event in CONVERSION_EVENTS:
        print(f"\n  [{event}]")
        rows = run_report(
            client,
            dimensions=["sessionSourceMedium"],
            metrics=["eventCount"],
            date_start="14daysAgo",
            date_end="yesterday",
            event_filter=event,
        )
        rows.sort(key=lambda row: -int(row["eventCount"]))
        print(fmt_table(rows, ["sessionSourceMedium", "eventCount"]))

    print("\n=== 3. DAILY TREND - key conversion events ===")
    rows = run_report(
        client,
        dimensions=["date", "eventName"],
        metrics=["eventCount"],
        date_start="14daysAgo",
        date_end="yesterday",
    )
    rows = [row for row in rows if row["eventName"] in CONVERSION_EVENTS]
    rows.sort(key=lambda row: (row["date"], row["eventName"]))
    print(fmt_table(rows, ["date", "eventName", "eventCount"]))

    print("\n=== 4. GOOGLE ADS ATTRIBUTION ===")
    rows = run_report(
        client,
        dimensions=["sessionGoogleAdsCampaignName", "sessionGoogleAdsAdGroupName", "eventName"],
        metrics=["eventCount"],
        date_start="14daysAgo",
        date_end="yesterday",
    )
    rows = [row for row in rows if row["eventName"] in CONVERSION_EVENTS]
    rows.sort(key=lambda row: -int(row["eventCount"]))
    print(
        fmt_table(
            rows,
            ["sessionGoogleAdsCampaignName", "sessionGoogleAdsAdGroupName", "eventName", "eventCount"],
        )
    )


if __name__ == "__main__":
    main()

