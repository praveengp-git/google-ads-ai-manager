"""Add campaign-level negative keywords for the fictional Acme Corp account.

The script checks existing campaign negatives first, prints a dry-run preview,
and updates the master CSV only after --apply succeeds.

Usage:
    python scripts/add_negatives_template.py
    python scripts/add_negatives_template.py --apply
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from google.ads.googleads.errors import GoogleAdsException

sys.path.insert(0, str(Path(__file__).parent))
from create_campaign_template import CAMPAIGN_NAME_PREFIX, keyword_match_type, load_client


MASTER_CSV = Path(__file__).resolve().parents[1] / "keywords" / "_negative_keywords_master.csv"

NEW_NEGATIVES: list[tuple[str, str, str]] = [
    ("free template", "phrase", "free template intent, unlikely to convert"),
    ("project manager salary", "phrase", "job seeker intent"),
    ("project management jobs", "phrase", "job seeker intent"),
    ("certification", "broad", "training or learning intent"),
    ("open source", "phrase", "non-commercial software intent"),
]


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

    print(f"\n  Master CSV: +{added} rows added ({len(rows)} total)")


def print_google_ads_exception(exc: GoogleAdsException, indent: str = "  ") -> None:
    print(f"{indent}ERROR request_id={exc.request_id}")
    for error in exc.failure.errors:
        print(f"{indent}  {error.error_code}: {error.message}")
        if error.location:
            path = " > ".join(f.field_name for f in error.location.field_path_elements)
            print(f"{indent}    field: {path}")


def run(apply: bool) -> None:
    client, customer_id = load_client()
    campaigns = get_campaigns(client, customer_id)
    criterion_service = client.get_service("CampaignCriterionService")
    failed = False

    mode = "APPLYING" if apply else "DRY RUN"
    print(f"{'=' * 72}")
    print(f"add_negatives_template [{mode}] customer: {customer_id}")
    print(f"{'=' * 72}\n")

    if not campaigns:
        print("No matching campaigns found. Check CAMPAIGN_NAME_PREFIX and customer ID.")
        return

    for campaign in campaigns:
        print(f"  {campaign['name']}")
    print()

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

        print(f"  {campaign['name']}: adding {len(to_add)}")
        for keyword, match_type, reason in to_add:
            print(f"    + [{match_type}] {keyword!r} - {reason}")

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

    if apply and not failed:
        update_master_csv(NEW_NEGATIVES)
        print("\nDone.")
    elif apply and failed:
        print("\nOne or more API calls failed. Master CSV was not updated.")
    else:
        print("\nDry run complete. Run with --apply to push to Google Ads and update CSV.")


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
