#!/usr/bin/env python3
"""
Import services into the EOSCnode MariaDB schema from a CSV exported from the provided Excel template.

Usage:
  python3 import_services.py --csv services.csv --db eoscnode --user eoscnode --password 'PASSWORD'

Dependencies on Debian:
  sudo apt install python3-pymysql
"""
import argparse
import csv
import sys
from typing import Dict, Any, List

try:
    import pymysql
except ImportError:
    print("Missing dependency: pymysql. Install it with: sudo apt install python3-pymysql", file=sys.stderr)
    sys.exit(2)

EOSCDATA_COLUMNS = [
    "avain", "abbreviation", "description_en", "description_fi", "detaileddescription_en", "detaileddescription_fi",
    "determiner_en", "determiner_fi", "end_user_guidance_en", "end_user_guidance_fi", "geographicalAvailabilities",
    "how_to_obtain_the_service_en", "how_to_obtain_the_service_fi", "interoperable_services", "interoperable_services_urns",
    "interoperable_services_websites", "languageAvailabilities", "link_to_service_en", "link_to_service_fi", "link_to_sla_en",
    "link_to_sla_fi", "link_to_training_material_en", "link_to_training_material_fi", "link_to_user_guide_en", "link_to_user_guide_fi",
    "link_to_user_support_contact_form", "logo", "name_en", "name_fi", "persistent_identifier", "pricingpolicy_en", "pricingpolicy_fi",
    "privacy_policy_en", "privacy_policy_fi", "protection_level_max_en", "protection_level_max_fi", "protection_level_min_en",
    "protection_level_min_fi", "purpose_of_the_service", "purpose_of_the_service_fi", "securityContactEmail", "service_owner",
    "service_provider", "support_email_address", "tagline_en", "tagline_fi", "technical_requirements_en", "technical_requirements_fi",
    "terms_of_use_en", "terms_of_use_fi", "toms_en", "toms_fi", "topics_for_website_en", "topics_for_website_fi", "tou_info_en",
    "tou_info_fi", "tou_specific_en", "tou_specific_fi", "tou_specific_title_en", "tou_specific_title_fi", "tou_title_en", "tou_title_fi",
    "trl", "urn", "website", "accessTypes", "nodeId", "customer_segment", "end_user_groups"
]

INT_COLUMNS = {"trl", "accessTypes", "nodeId", "purpose_of_the_service", "customer_segment", "end_user_groups"}
ALIASES = {
    "access_type_id": "accessTypes",
    "node_id": "nodeId",
    "purpose_id": "purpose_of_the_service",
    "customer_segment_id": "customer_segment",
    "end_user_group_id": "end_user_groups",
}

REQUIRED = ["avain", "name_en", "description_en", "trl", "access_type_id", "node_id"]


def normalize(row: Dict[str, str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in row.items():
        if key is None:
            continue
        k = key.strip()
        if not k:
            continue
        k = ALIASES.get(k, k)
        v = value.strip() if isinstance(value, str) else value
        if v == "":
            v = None
        out[k] = v
    for col in INT_COLUMNS:
        if col in out and out[col] is not None:
            try:
                out[col] = int(out[col])
            except ValueError:
                raise ValueError(f"Column {col} must be an integer, got {out[col]!r}")
    return out


def service_legacy_id(row: Dict[str, Any], index: int) -> int:
    # Used by EOSCnode's manual bridge tables. Prefer an explicit legacy_service_id column.
    # If omitted, use the row number starting from 1.
    value = row.get("legacy_service_id")
    if value not in (None, ""):
        return int(value)
    return index


def read_rows(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        reader = csv.DictReader(f, dialect=dialect)
        rows = []
        for row in reader:
            if not any((v or "").strip() for v in row.values() if isinstance(v, str)):
                continue
            rows.append(normalize(row))
        return rows


def validate(rows: List[Dict[str, Any]]) -> None:
    for i, row in enumerate(rows, start=1):
        for col in REQUIRED:
            actual = ALIASES.get(col, col)
            if not row.get(actual):
                raise ValueError(f"Row {i}: missing required column {col}")


def upsert_services(conn, rows: List[Dict[str, Any]], dry_run: bool = False) -> None:
    cols = EOSCDATA_COLUMNS
    placeholders = ", ".join(["%s"] * len(cols))
    col_sql = ", ".join(f"`{c}`" for c in cols)
    updates = ", ".join(f"`{c}`=VALUES(`{c}`)" for c in cols if c != "avain")
    sql = f"INSERT INTO eoscdata ({col_sql}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {updates}"

    bridge_sql = [
        ("br_eoscdata_purpose", "palvelu", "purpose", "purpose_of_the_service"),
        ("br_eoscdata_customer_segment", "id", "cs_id", "customer_segment"),
        ("br_eoscdata_end_user_groups", "id", "eug_id", "end_user_groups"),
    ]

    with conn.cursor() as cur:
        for idx, row in enumerate(rows, start=1):
            values = [row.get(c) for c in cols]
            if dry_run:
                print(f"DRY-RUN service {row.get('avain')}: {row.get('name_en')}")
                continue
            cur.execute(sql, values)
            legacy_id = service_legacy_id(row, idx)
            for table, c1, c2, source_col in bridge_sql:
                vocab_id = row.get(source_col)
                if vocab_id is not None:
                    cur.execute(
                        f"INSERT IGNORE INTO `{table}` (`{c1}`, `{c2}`) VALUES (%s, %s)",
                        (legacy_id, int(vocab_id)),
                    )
    if not dry_run:
        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Import EOSCnode services from CSV into MariaDB")
    parser.add_argument("--csv", required=True, help="CSV file exported from the Services sheet")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--db", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rows = read_rows(args.csv)
    validate(rows)
    print(f"Loaded {len(rows)} service row(s) from {args.csv}")

    if args.dry_run:
        upsert_services(None, rows, dry_run=True)
        return 0

    conn = pymysql.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.db,
        charset="utf8mb4",
        autocommit=False,
    )
    try:
        upsert_services(conn, rows)
    finally:
        conn.close()
    print("Import completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
