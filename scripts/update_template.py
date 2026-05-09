"""Composable Google Ads update template.

This combines two common actions in one dated script:

1. Add campaign-level negative keywords.
2. Raise selected keyword bids.

Usage:
    python scripts/update_template.py
    python scripts/update_template.py --apply
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from google.ads.googleads.errors import GoogleAdsException

sys.path.insert(0, str(Path(__file__).parent))
from create_campaign_template import CAMPAIGN_NAME_PREFIX, keyword_match_type, load_client, micros


MASTER_CSV = Path(__file__).resolve().parents[1] / "keywords" / "_negative_keywords_master.csv"

NEW_NEGATIVES: list[tuple[str, str, str]] = [
    ("internship", "broad", "student or job seeker intent"),
    ("resume", "broad", "job seeker intent"),
    ("excel template", "phrase", "template download intent"),
]

BID_UPDATES: list[dict] = [
    {
        "keyword_text": "project management tool",
        "new_bid": 5.50,
        "campaign_fragments": ["US Core", "US Enterprise"],
    },
    {
        "keyword_text": "team collaboration software",
        "new_bid": 5.25,
        "campaign_fragments": ["Remote Teams"],
    },
]


def gaql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def get_campaigns(client, customer_id: str) -> list[dict]:
    service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT campaign.name, campaign.resource_name, campaign.status
        FROM campaign
        WHERE campaign.name LIKE '{CAMPAIGN_NAME_PREFIX}%'
        AND campaign.status != REMOVED
        ORDER BY campaign.name
    """
    seen: set[str] = set()
    results: list[dict] = []
    for row in service.search(customer_id=customer_id, query=query):
        resource_name = row.campaign.resource_name
        if resource_name in seen:
            continue
        seen.add(resource_name)
        results.append(
            {
                "name": row.campaign.name,
                "resource_name": resource_name,
                "status": row.campaign.status,
            }
        )
    return results


def existing_negatives(client, customer_id: str, campaign_resource: str) -> set[str]:
    service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT campaign_criterion.keyword.text
        FROM campaign_criterion
        WHERE campaign.resource_name = '{campaign_resource}'
        AND campaign_criterion.negative = TRUE
        AND campaign_criterion.type = KEYWORD
    """
    return {
        row.campaign_criterion.keyword.text.lower()
        for row in service.search(customer_id=customer_id, query=query)
    }


def get_keyword_criteria(
    client,
    customer_id: str,
    keyword_text: str,
    campaign_fragments: list[str],
) -> list[dict]:
    service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT campaign.name, ad_group.name,
               ad_group_criterion.resource_name,
               ad_group_criterion.keyword.text,
               ad_group_criterion.keyword.match_type,
               ad_group_criterion.cpc_bid_micros,
               ad_group_criterion.status
        FROM ad_group_criterion
        WHERE ad_group_criterion.type = KEYWORD
        AND ad_group_criterion.keyword.text = '{gaql_string(keyword_text)}'
        AND ad_group_criterion.status != REMOVED
        ORDER BY campaign.name
    """
    results: list[dict] = []
    for row in service.search(customer_id=customer_id, query=query):
        campaign_name = row.campaign.name
        if not any(fragment in campaign_name for fragment in campaign_fragments):
            continue
        results.append(
            {
                "campaign_name": campaign_name,
                "ad_group_name": row.ad_group.name,
                "resource_name": row.ad_group_criterion.resource_name,
                "match_type": row.ad_group_criterion.keyword.match_type,
                "current_bid_micros": row.ad_group_criterion.cpc_bid_micros,
            }
        )
    return results


def update_master_csv(new_rows: list[tuple[str, str, str]]) -> None:
    existing: set[str] = set()
    rows: list[dict] = []
    with MASTER_CSV.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
            existing.add(row["keyword"].lower())

    added = 0
    for keyword, match_type, reason in new_rows:
        if keyword.lower() in existing:
            continue
        rows.append({"keyword": keyword, "match_type": match_type, "reason": reason})
        existing.add(keyword.lower())
        added += 1

    with MASTER_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["keyword", "match_type", "reason"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n  Master CSV: +{added} new rows ({len(rows)} total)")


def print_google_ads_exception(exc: GoogleAdsException, indent: str = "  ") -> None:
    print(f"{indent}ERROR request_id={exc.request_id}")
    for error in exc.failure.errors:
        print(f"{indent}  {error.error_code}: {error.message}")
        if error.location:
            path = " > ".join(f.field_name for f in error.location.field_path_elements)
            print(f"{indent}    field: {path}")


def add_negatives(client, customer_id: str, campaigns: list[dict], apply: bool) -> bool:
    criterion_service = client.get_service("CampaignCriterionService")
    failed = False
    for campaign in campaigns:
        existing = existing_negatives(client, customer_id, campaign["resource_name"])
        to_add = [
            (keyword, match_type, reason)
            for keyword, match_type, reason in NEW_NEGATIVES
            if keyword.lower() not in existing
        ]
        if not to_add:
            print(f"  {campaign['name']}: all already present, skipped")
            continue
        print(f"  {campaign['name']}: adding {len(to_add)} negatives")
        for keyword, match_type, _ in to_add:
            print(f"    + [{match_type}] {keyword!r}")
        if not apply:
            continue
        operations = []
        for keyword_text, match_type_str, _ in to_add:
            op = client.get_type("CampaignCriterionOperation")
            criterion = op.create
            criterion.campaign = campaign["resource_name"]
            criterion.negative = True
            criterion.keyword.text = keyword_text
            criterion.keyword.match_type = keyword_match_type(client, match_type_str)
            operations.append(op)
        try:
            criterion_service.mutate_campaign_criteria(
                customer_id=customer_id,
                operations=operations,
            )
            print(f"    OK - {len(operations)} added")
        except GoogleAdsException as exc:
            failed = True
            print_google_ads_exception(exc, indent="    ")
    return failed


def update_bids(client, customer_id: str, apply: bool) -> bool:
    criterion_service = client.get_service("AdGroupCriterionService")
    failed = False
    for spec in BID_UPDATES:
        keyword_text = spec["keyword_text"]
        new_bid_micros = micros(spec["new_bid"])
        criteria = get_keyword_criteria(
            client,
            customer_id,
            keyword_text,
            spec["campaign_fragments"],
        )
        if not criteria:
            print(f"  {keyword_text!r}: no matching criteria found, skipped")
            continue
        for criterion in criteria:
            match_name = {2: "EXACT", 3: "PHRASE", 4: "BROAD"}.get(
                criterion["match_type"],
                str(criterion["match_type"]),
            )
            old_bid = criterion["current_bid_micros"] / 1_000_000
            print(f"  [{match_name}] {keyword_text!r}")
            print(f"    {criterion['campaign_name']} / {criterion['ad_group_name']}")
            print(f"    {old_bid:.2f} -> {spec['new_bid']:.2f}")
            if not apply:
                continue
            op = client.get_type("AdGroupCriterionOperation")
            op.update.resource_name = criterion["resource_name"]
            op.update.cpc_bid_micros = new_bid_micros
            op.update_mask.paths.append("cpc_bid_micros")
            try:
                criterion_service.mutate_ad_group_criteria(
                    customer_id=customer_id,
                    operations=[op],
                )
                print("    OK")
            except GoogleAdsException as exc:
                failed = True
                print_google_ads_exception(exc, indent="    ")
    return failed


def run(apply: bool) -> None:
    client, customer_id = load_client()
    campaigns = get_campaigns(client, customer_id)
    mode = "APPLYING" if apply else "DRY RUN"
    print(f"{'=' * 72}")
    print(f"update_template [{mode}] customer: {customer_id}")
    print(f"{'=' * 72}\n")

    print("Action 1: add negative keywords")
    negative_errors = add_negatives(client, customer_id, campaigns, apply)
    print()

    print("Action 2: update keyword bids")
    bid_errors = update_bids(client, customer_id, apply)
    print()

    if apply and not negative_errors and not bid_errors:
        print("Updating master CSV")
        update_master_csv(NEW_NEGATIVES)
        print()
    elif apply:
        print("One or more API calls failed. Master CSV was not updated.")

    print("Done." if apply else "Dry run complete. Pass --apply to execute.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Actually push changes.")
    args = parser.parse_args()
    try:
        run(apply=args.apply)
    except GoogleAdsException as exc:
        print_google_ads_exception(exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
