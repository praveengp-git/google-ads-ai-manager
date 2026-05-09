"""Create fictional Acme Corp Google Search campaigns.

This is a public template. It creates campaigns, ad groups, keywords, and
responsive search ads for a SaaS company selling project management software.

Safety defaults:
  - All campaigns are created as PAUSED.
  - All ad groups are created as PAUSED.
  - All ads are created as PAUSED.
  - Without --apply, this script only prints a dry-run preview.

Usage:
    python scripts/create_campaign_template.py
    python scripts/create_campaign_template.py --apply
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException


ROOT = Path(__file__).resolve().parents[1]
KEYWORDS_DIR = ROOT / "keywords"
NEGATIVE_KEYWORDS_CSV = KEYWORDS_DIR / "_negative_keywords_master.csv"
SAMPLE_KEYWORDS_CSV = KEYWORDS_DIR / "sample_keywords.csv"

SITE_ROOT = os.environ.get("SITE_ROOT", "https://www.acme-corp.example")
LANGUAGE_CONSTANT_ENGLISH = "languageConstants/1000"
CAMPAIGN_NAME_PREFIX = "Acme Search |"


@dataclass(frozen=True)
class KeywordSpec:
    text: str
    match_type: str
    bid: float


@dataclass(frozen=True)
class AdVariant:
    headlines: tuple[str, ...]
    descriptions: tuple[str, ...]


@dataclass(frozen=True)
class AdGroupSpec:
    name: str
    landing_path: str
    default_cpc: float
    keywords: tuple[KeywordSpec, ...]
    variants: tuple[AdVariant, ...]


@dataclass(frozen=True)
class CampaignSpec:
    name: str
    daily_budget: float
    locations: tuple[tuple[str, str], ...]
    audience_label: str
    ad_groups: tuple[AdGroupSpec, ...]


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Tiny .env loader to avoid adding a dependency for templates."""
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


def load_client() -> tuple[GoogleAdsClient, str]:
    load_dotenv()
    client = GoogleAdsClient.load_from_dict(
        {
            "developer_token": required_env("GOOGLE_ADS_DEVELOPER_TOKEN"),
            "client_id": required_env("GOOGLE_ADS_CLIENT_ID"),
            "client_secret": required_env("GOOGLE_ADS_CLIENT_SECRET"),
            "refresh_token": required_env("GOOGLE_ADS_REFRESH_TOKEN"),
            "login_customer_id": required_env("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
            "use_proto_plus": True,
        }
    )
    return client, required_env("GOOGLE_ADS_CUSTOMER_ID")


def micros(amount: float) -> int:
    return int(round(amount * 1_000_000))


def require_length(label: str, value: str, limit: int) -> str:
    if len(value) > limit:
        raise ValueError(f"{label} exceeds {limit} chars ({len(value)}): {value!r}")
    return value


def keyword_match_type(client: GoogleAdsClient, match_type: str):
    mapping = {
        "broad": client.enums.KeywordMatchTypeEnum.BROAD,
        "phrase": client.enums.KeywordMatchTypeEnum.PHRASE,
        "exact": client.enums.KeywordMatchTypeEnum.EXACT,
    }
    if match_type not in mapping:
        raise ValueError(f"Unsupported match type: {match_type!r}")
    return mapping[match_type]


def normalize_keyword_text(text: str, match_type: str) -> str:
    cleaned = text.strip().strip('"')
    if match_type == "exact" and cleaned.startswith("[") and cleaned.endswith("]"):
        return cleaned[1:-1]
    return cleaned


def final_url(landing_path: str) -> str:
    return f"{SITE_ROOT.rstrip('/')}/{landing_path.lstrip('/')}"


def read_negative_keywords() -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    with NEGATIVE_KEYWORDS_CSV.open(newline="") as f:
        for row in csv.DictReader(f):
            entries.append((row["keyword"].strip(), row["match_type"].strip().lower()))
    return entries


def read_sample_keywords() -> tuple[KeywordSpec, ...]:
    entries: list[KeywordSpec] = []
    with SAMPLE_KEYWORDS_CSV.open(newline="") as f:
        for row in csv.DictReader(f):
            entries.append(
                KeywordSpec(
                    text=row["keyword"].strip(),
                    match_type=row["match_type"].strip().lower(),
                    bid=float(row["bid"]),
                )
            )
    return tuple(entries)


COLLAB_KEYWORDS: tuple[KeywordSpec, ...] = (
    KeywordSpec("team collaboration software", "phrase", 4.25),
    KeywordSpec("team collaboration software", "exact", 4.75),
    KeywordSpec("remote team collaboration tool", "phrase", 4.50),
    KeywordSpec("team task management software", "phrase", 4.00),
    KeywordSpec("workflow collaboration platform", "phrase", 4.25),
)


PROJECT_MANAGEMENT_VARIANTS: tuple[AdVariant, ...] = (
    AdVariant(
        headlines=(
            "Project Management Software",
            "Plan Work Across Teams",
            "Track Projects In One Place",
            "Built For Growing Teams",
            "Manage Tasks And Timelines",
            "See Work Before It Slips",
            "Acme Corp Project Hub",
            "Bring Projects Into Focus",
            "Simple Project Planning",
            "Workflows Your Team Uses",
            "Launch Projects Faster",
            "No More Status Guesswork",
            "Try Acme Corp Today",
            "Project Visibility For Teams",
            "Built For SaaS Teams",
        ),
        descriptions=(
            "Plan projects, owners, timelines, and blockers in one workspace.",
            "Give every team a clear view of work, deadlines, and status.",
            "Acme Corp helps growing teams ship projects with less follow-up.",
            "Use structured workflows without forcing your team into spreadsheets.",
        ),
    ),
)


COLLAB_VARIANTS: tuple[AdVariant, ...] = (
    AdVariant(
        headlines=(
            "Team Collaboration Software",
            "Run Better Team Workflows",
            "Tasks Timelines And Owners",
            "Remote Team Project Hub",
            "Keep Teams Aligned",
            "Move Work Out Of Chats",
            "Acme Corp For Remote Teams",
            "Plan Work With Clarity",
            "Track Ownership Clearly",
            "Reduce Status Meetings",
            "One Workspace For Teams",
            "Workflows Without Sprawl",
            "Try Acme Corp Today",
            "Built For Modern Teams",
            "Make Team Work Visible",
        ),
        descriptions=(
            "Centralize tasks, project owners, timelines, and blockers.",
            "Help remote teams see what is moving, stuck, or waiting for review.",
            "Replace scattered status updates with structured team workflows.",
            "Acme Corp keeps collaboration visible without extra meeting load.",
        ),
    ),
)


SITELINKS: tuple[tuple[str, str, str, str], ...] = (
    (
        "Project Templates",
        f"{SITE_ROOT}/templates",
        "Start with proven workflows",
        "Customize for your team",
    ),
    (
        "Remote Teams",
        f"{SITE_ROOT}/remote-teams",
        "Run work across locations",
        "Track owners and blockers",
    ),
    (
        "Enterprise Workflows",
        f"{SITE_ROOT}/enterprise",
        "Visibility for larger teams",
        "Governance without sprawl",
    ),
    (
        "Book A Demo",
        f"{SITE_ROOT}/demo",
        "See Acme Corp in action",
        "Talk to a product expert",
    ),
)

CALLOUTS: tuple[str, ...] = (
    "Built For SaaS Teams",
    "Fast Setup",
    "Workflow Templates",
    "Owner-Level Tracking",
    "Remote Team Ready",
    "Demo Available",
)

STRUCTURED_SNIPPET_HEADER = "Features"
STRUCTURED_SNIPPET_VALUES: tuple[str, ...] = (
    "Task Tracking",
    "Project Timelines",
    "Team Workflows",
    "Dashboards",
    "Approvals",
)


def build_ad_groups(audience: str) -> tuple[AdGroupSpec, ...]:
    return (
        AdGroupSpec(
            name=f"{audience} | Project Management",
            landing_path="/project-management",
            default_cpc=4.50,
            keywords=read_sample_keywords(),
            variants=PROJECT_MANAGEMENT_VARIANTS,
        ),
        AdGroupSpec(
            name=f"{audience} | Team Collaboration",
            landing_path="/team-collaboration",
            default_cpc=4.25,
            keywords=COLLAB_KEYWORDS,
            variants=COLLAB_VARIANTS,
        ),
    )


def build_campaigns() -> tuple[CampaignSpec, ...]:
    return (
        CampaignSpec(
            name=f"{CAMPAIGN_NAME_PREFIX} US Core",
            daily_budget=75.00,
            locations=(("United States", "Country"),),
            audience_label="US Core",
            ad_groups=build_ad_groups("US Core"),
        ),
        CampaignSpec(
            name=f"{CAMPAIGN_NAME_PREFIX} US Enterprise",
            daily_budget=50.00,
            locations=(("New York", "State"), ("California", "State"), ("Texas", "State")),
            audience_label="US Enterprise",
            ad_groups=build_ad_groups("US Enterprise"),
        ),
        CampaignSpec(
            name=f"{CAMPAIGN_NAME_PREFIX} Remote Teams",
            daily_budget=40.00,
            locations=(("United States", "Country"),),
            audience_label="Remote Teams",
            ad_groups=build_ad_groups("Remote Teams"),
        ),
    )


def validate_campaigns(campaigns: Iterable[CampaignSpec]) -> None:
    for campaign in campaigns:
        for ad_group in campaign.ad_groups:
            for variant in ad_group.variants:
                for headline in variant.headlines:
                    require_length(f"[{campaign.name}|{ad_group.name}] headline", headline, 30)
                for description in variant.descriptions:
                    require_length(f"[{campaign.name}|{ad_group.name}] description", description, 90)


def preview(campaigns: tuple[CampaignSpec, ...]) -> None:
    total_daily = sum(c.daily_budget for c in campaigns)
    print("\n# Acme Corp Google Ads launch preview")
    print(f"  Total daily budget: {total_daily:.2f}")
    print("  All campaigns, ad groups, and ads will be created as PAUSED.\n")
    for campaign in campaigns:
        locs = ", ".join(name for name, _ in campaign.locations)
        print(f"Campaign: {campaign.name}  [{campaign.daily_budget:.2f}/day | PAUSED]")
        print(f"  Geo: {locs}")
        for ad_group in campaign.ad_groups:
            print(
                f"  Ad group: {ad_group.name} | "
                f"{len(ad_group.keywords)} keywords | {len(ad_group.variants)} RSA set(s)"
            )
            print(f"    URL: {final_url(ad_group.landing_path)}")


def geo_target_query(name: str) -> str:
    safe = name.replace("'", "\\'")
    return (
        "SELECT geo_target_constant.resource_name, geo_target_constant.name, "
        "geo_target_constant.target_type, geo_target_constant.status "
        "FROM geo_target_constant "
        f"WHERE geo_target_constant.name = '{safe}' "
        "AND geo_target_constant.status = ENABLED"
    )


def lookup_geo_targets(
    client: GoogleAdsClient,
    customer_id: str,
    locations: Iterable[tuple[str, str]],
) -> dict[tuple[str, str], str]:
    service = client.get_service("GoogleAdsService")
    resolved: dict[tuple[str, str], str] = {}
    for name, target_type in locations:
        rows = list(service.search(customer_id=customer_id, query=geo_target_query(name)))
        if not rows:
            raise ValueError(f"Could not resolve geo target: {name} ({target_type})")
        for row in rows:
            geo = row.geo_target_constant
            if geo.target_type.lower() == target_type.lower():
                resolved[(name, target_type)] = geo.resource_name
                break
        if (name, target_type) not in resolved:
            available = ", ".join(sorted({row.geo_target_constant.target_type for row in rows}))
            raise ValueError(f"Resolved {name} but no {target_type}. Available: {available}")
    return resolved


def create_campaign_budgets(
    client: GoogleAdsClient,
    customer_id: str,
    campaigns: tuple[CampaignSpec, ...],
) -> dict[str, str]:
    service = client.get_service("CampaignBudgetService")
    operations = []
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for campaign in campaigns:
        op = client.get_type("CampaignBudgetOperation")
        budget = op.create
        budget.name = f"{campaign.name} | Budget | {stamp}"
        budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
        budget.amount_micros = micros(campaign.daily_budget)
        operations.append(op)
    response = service.mutate_campaign_budgets(customer_id=customer_id, operations=operations)
    return {c.name: r.resource_name for c, r in zip(campaigns, response.results, strict=True)}


def create_campaigns(
    client: GoogleAdsClient,
    customer_id: str,
    campaigns: tuple[CampaignSpec, ...],
    budget_map: dict[str, str],
) -> dict[str, str]:
    service = client.get_service("CampaignService")
    operations = []
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for spec in campaigns:
        op = client.get_type("CampaignOperation")
        campaign = op.create
        campaign.name = f"{spec.name} | {stamp}"
        campaign.status = client.enums.CampaignStatusEnum.PAUSED
        campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
        campaign.campaign_budget = budget_map[spec.name]
        campaign.network_settings.target_google_search = True
        campaign.network_settings.target_search_network = False
        campaign.network_settings.target_content_network = False
        campaign.network_settings.target_partner_search_network = False
        campaign.manual_cpc.enhanced_cpc_enabled = False
        operations.append(op)
    response = service.mutate_campaigns(customer_id=customer_id, operations=operations)
    return {spec.name: r.resource_name for spec, r in zip(campaigns, response.results, strict=True)}


def apply_campaign_criteria(
    client: GoogleAdsClient,
    customer_id: str,
    campaigns: tuple[CampaignSpec, ...],
    campaign_map: dict[str, str],
    geo_map: dict[tuple[str, str], str],
) -> None:
    service = client.get_service("CampaignCriterionService")
    operations = []
    negatives = read_negative_keywords()
    for campaign in campaigns:
        resource_name = campaign_map[campaign.name]
        for location in campaign.locations:
            op = client.get_type("CampaignCriterionOperation")
            op.create.campaign = resource_name
            op.create.location.geo_target_constant = geo_map[location]
            operations.append(op)
        lang_op = client.get_type("CampaignCriterionOperation")
        lang_op.create.campaign = resource_name
        lang_op.create.language.language_constant = LANGUAGE_CONSTANT_ENGLISH
        operations.append(lang_op)
        for keyword_text, match_type in negatives:
            op = client.get_type("CampaignCriterionOperation")
            criterion = op.create
            criterion.campaign = resource_name
            criterion.negative = True
            criterion.keyword.text = keyword_text
            criterion.keyword.match_type = keyword_match_type(client, match_type)
            operations.append(op)
    service.mutate_campaign_criteria(customer_id=customer_id, operations=operations)


def create_ad_groups(
    client: GoogleAdsClient,
    customer_id: str,
    campaigns: tuple[CampaignSpec, ...],
    campaign_map: dict[str, str],
) -> dict[tuple[str, str], str]:
    service = client.get_service("AdGroupService")
    operations = []
    ordered_keys: list[tuple[str, str]] = []
    for campaign in campaigns:
        for spec in campaign.ad_groups:
            ordered_keys.append((campaign.name, spec.name))
            op = client.get_type("AdGroupOperation")
            ad_group = op.create
            ad_group.name = f"{campaign.name} | {spec.name}"
            ad_group.campaign = campaign_map[campaign.name]
            ad_group.status = client.enums.AdGroupStatusEnum.PAUSED
            ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
            ad_group.cpc_bid_micros = micros(spec.default_cpc)
            operations.append(op)
    response = service.mutate_ad_groups(customer_id=customer_id, operations=operations)
    return {key: r.resource_name for key, r in zip(ordered_keys, response.results, strict=True)}


def create_keywords(
    client: GoogleAdsClient,
    customer_id: str,
    campaigns: tuple[CampaignSpec, ...],
    ad_group_map: dict[tuple[str, str], str],
) -> None:
    service = client.get_service("AdGroupCriterionService")
    operations = []
    for campaign in campaigns:
        for spec in campaign.ad_groups:
            ad_group_resource = ad_group_map[(campaign.name, spec.name)]
            for keyword in spec.keywords:
                op = client.get_type("AdGroupCriterionOperation")
                criterion = op.create
                criterion.ad_group = ad_group_resource
                criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
                criterion.keyword.text = normalize_keyword_text(keyword.text, keyword.match_type)
                criterion.keyword.match_type = keyword_match_type(client, keyword.match_type)
                criterion.cpc_bid_micros = micros(keyword.bid)
                operations.append(op)
    service.mutate_ad_group_criteria(customer_id=customer_id, operations=operations)


def create_ads(
    client: GoogleAdsClient,
    customer_id: str,
    campaigns: tuple[CampaignSpec, ...],
    ad_group_map: dict[tuple[str, str], str],
) -> None:
    service = client.get_service("AdGroupAdService")
    operations = []
    for campaign in campaigns:
        for spec in campaign.ad_groups:
            ad_group_resource = ad_group_map[(campaign.name, spec.name)]
            url = final_url(spec.landing_path)
            for variant in spec.variants:
                op = client.get_type("AdGroupAdOperation")
                ad = op.create
                ad.ad_group = ad_group_resource
                ad.status = client.enums.AdGroupAdStatusEnum.PAUSED
                ad.ad.final_urls.append(url)
                rsa = ad.ad.responsive_search_ad
                for headline in variant.headlines:
                    asset = client.get_type("AdTextAsset")
                    asset.text = require_length("headline", headline, 30)
                    rsa.headlines.append(asset)
                for description in variant.descriptions:
                    asset = client.get_type("AdTextAsset")
                    asset.text = require_length("description", description, 90)
                    rsa.descriptions.append(asset)
                operations.append(op)
    service.mutate_ad_group_ads(customer_id=customer_id, operations=operations)


def create_sitelinks(
    client: GoogleAdsClient,
    customer_id: str,
    campaigns: tuple[CampaignSpec, ...],
    campaign_map: dict[str, str],
) -> None:
    asset_service = client.get_service("AssetService")
    campaign_asset_service = client.get_service("CampaignAssetService")
    asset_ops = []
    for link_text, url, desc1, desc2 in SITELINKS:
        op = client.get_type("AssetOperation")
        asset = op.create
        asset.final_urls.append(url)
        sitelink = asset.sitelink_asset
        sitelink.link_text = require_length("sitelink", link_text, 25)
        sitelink.description1 = require_length("sitelink desc1", desc1, 35)
        sitelink.description2 = require_length("sitelink desc2", desc2, 35)
        asset_ops.append(op)
    response = asset_service.mutate_assets(customer_id=customer_id, operations=asset_ops)
    asset_names = [r.resource_name for r in response.results]
    campaign_asset_ops = []
    for campaign in campaigns:
        for asset_name in asset_names:
            op = client.get_type("CampaignAssetOperation")
            ca = op.create
            ca.campaign = campaign_map[campaign.name]
            ca.asset = asset_name
            ca.field_type = client.enums.AssetFieldTypeEnum.SITELINK
            campaign_asset_ops.append(op)
    campaign_asset_service.mutate_campaign_assets(
        customer_id=customer_id,
        operations=campaign_asset_ops,
    )


def create_callouts(
    client: GoogleAdsClient,
    customer_id: str,
    campaigns: tuple[CampaignSpec, ...],
    campaign_map: dict[str, str],
) -> None:
    asset_service = client.get_service("AssetService")
    campaign_asset_service = client.get_service("CampaignAssetService")
    asset_ops = []
    for text in CALLOUTS:
        op = client.get_type("AssetOperation")
        op.create.callout_asset.callout_text = require_length("callout", text, 25)
        asset_ops.append(op)
    response = asset_service.mutate_assets(customer_id=customer_id, operations=asset_ops)
    asset_names = [r.resource_name for r in response.results]
    campaign_asset_ops = []
    for campaign in campaigns:
        for asset_name in asset_names:
            op = client.get_type("CampaignAssetOperation")
            ca = op.create
            ca.campaign = campaign_map[campaign.name]
            ca.asset = asset_name
            ca.field_type = client.enums.AssetFieldTypeEnum.CALLOUT
            campaign_asset_ops.append(op)
    campaign_asset_service.mutate_campaign_assets(
        customer_id=customer_id,
        operations=campaign_asset_ops,
    )


def create_structured_snippets(
    client: GoogleAdsClient,
    customer_id: str,
    campaigns: tuple[CampaignSpec, ...],
    campaign_map: dict[str, str],
) -> None:
    asset_service = client.get_service("AssetService")
    campaign_asset_service = client.get_service("CampaignAssetService")
    op = client.get_type("AssetOperation")
    snippet = op.create.structured_snippet_asset
    snippet.header = STRUCTURED_SNIPPET_HEADER
    for value in STRUCTURED_SNIPPET_VALUES:
        snippet.values.append(require_length("snippet value", value, 25))
    response = asset_service.mutate_assets(customer_id=customer_id, operations=[op])
    asset_name = response.results[0].resource_name
    campaign_asset_ops = []
    for campaign in campaigns:
        ca_op = client.get_type("CampaignAssetOperation")
        ca = ca_op.create
        ca.campaign = campaign_map[campaign.name]
        ca.asset = asset_name
        ca.field_type = client.enums.AssetFieldTypeEnum.STRUCTURED_SNIPPET
        campaign_asset_ops.append(ca_op)
    campaign_asset_service.mutate_campaign_assets(
        customer_id=customer_id,
        operations=campaign_asset_ops,
    )


def run(apply: bool) -> None:
    campaigns = build_campaigns()
    validate_campaigns(campaigns)
    preview(campaigns)
    if not apply:
        print("\nDry run only. Re-run with --apply to push changes to Google Ads.")
        return

    client, customer_id = load_client()
    all_locations = list({loc for campaign in campaigns for loc in campaign.locations})
    geo_map = lookup_geo_targets(client, customer_id, all_locations)

    print("\nCreating budgets...")
    budget_map = create_campaign_budgets(client, customer_id, campaigns)
    print("Creating campaigns (PAUSED)...")
    campaign_map = create_campaigns(client, customer_id, campaigns, budget_map)
    print("Applying geo, language, and negatives...")
    apply_campaign_criteria(client, customer_id, campaigns, campaign_map, geo_map)
    print("Creating ad groups (PAUSED)...")
    ad_group_map = create_ad_groups(client, customer_id, campaigns, campaign_map)
    print("Adding keywords...")
    create_keywords(client, customer_id, campaigns, ad_group_map)
    print("Creating ads / RSAs (PAUSED)...")
    create_ads(client, customer_id, campaigns, ad_group_map)
    print("Adding sitelinks...")
    create_sitelinks(client, customer_id, campaigns, campaign_map)
    print("Adding callout extensions...")
    create_callouts(client, customer_id, campaigns, campaign_map)
    print("Adding structured snippets...")
    create_structured_snippets(client, customer_id, campaigns, campaign_map)

    print("\nDone. Created campaigns (all PAUSED):")
    for spec in campaigns:
        print(f"  {spec.name}: {campaign_map[spec.name]}")
    print("\nNext: review in Google Ads UI, then manually enable only approved campaigns.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Push to Google Ads.")
    args = parser.parse_args()
    try:
        run(apply=args.apply)
    except GoogleAdsException as exc:
        print(f"\nGoogle Ads API error request_id={exc.request_id}")
        for error in exc.failure.errors:
            print(f"  {error.error_code}: {error.message}")
            if error.location:
                path = " > ".join(f.field_name for f in error.location.field_path_elements)
                print(f"    field: {path}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()

