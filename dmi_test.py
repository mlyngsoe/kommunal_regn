#!/usr/bin/env python3
"""
DMI municipal precipitation test
- Tests annual and daily acc_precip for a municipality
- Reports dates, record counts, missing years/days and annual totals
- Saves raw responses and CSV output

Install: pip install requests pandas
Run:    python dmi_test.py --municipality 0751 --name Aarhus --start 2016 --end 2025
"""
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests

BASE = "https://opendataapi.dmi.dk/v2/climateData/collections/municipalityValue/items"


def get_features(url, params=None):
    """Read GeoJSON pages by following DMI's rel=next link."""
    all_features = []
    session = requests.Session()
    while url:
        response = session.get(url, params=params, timeout=60)
        response.raise_for_status()
        payload = response.json()
        all_features.extend(payload.get("features", []))
        next_url = next(
            (link["href"] for link in payload.get("links", [])
             if link.get("rel") == "next"),
            None,
        )
        url = urljoin(response.url, next_url) if next_url else None
        params = None  # next link already contains query parameters
    return all_features


def to_frame(features):
    rows = []
    for feature in features:
        p = feature.get("properties", {})
        rows.append({
            "from": p.get("from"),
            "to": p.get("to"),
            "value_mm": p.get("value"),
            "validity": p.get("validity"),
            "qcStatus": p.get("qcStatus"),
            "municipalityId": p.get("municipalityId"),
            "municipalityName": p.get("municipalityName"),
            "timeResolution": p.get("timeResolution"),
            "normalOrReference": p.get("normalOrReference"),
            "noValuesInCalculation": p.get("noValuesInCalculation"),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["from"] = pd.to_datetime(df["from"], errors="coerce", utc=True)
        df["to"] = pd.to_datetime(df["to"], errors="coerce", utc=True)
        df["value_mm"] = pd.to_numeric(df["value_mm"], errors="coerce")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--municipality", default="0751", help="4-digit DMI municipality ID (Aarhus=0751)")
    ap.add_argument("--name", default="municipality", help="Name used in output filenames")
    ap.add_argument("--start", type=int, default=2016)
    ap.add_argument("--end", type=int, default=2025)
    ap.add_argument("--out", default="dmi_test_output")
    args = ap.parse_args()

    if args.end < args.start:
        ap.error("--end must be >= --start")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    common = {
        "municipalityId": args.municipality.zfill(4),
        "parameterId": "acc_precip",
    }

    print(f"Testing DMI municipalityValue: {args.name} ({common['municipalityId']})")
    print(f"Period: {args.start}-{args.end}")
    print("API:", BASE)

    # 1) Annual values: useful test, but API annual records may be absent for this collection.
    annual_params = dict(common, timeResolution="year", limit=300000)
    try:
        annual_features = get_features(BASE, annual_params)
        annual = to_frame(annual_features)
        annual.to_csv(out / "annual_api.csv", index=False)
        (out / "annual_api.json").write_text(
            json.dumps(annual_features, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nAnnual API records returned: {len(annual)}")
        if not annual.empty:
            print(annual[["from", "to", "value_mm", "validity", "qcStatus"]].to_string(index=False))
    except Exception as exc:
        print(f"Annual query failed: {exc}")
        annual = pd.DataFrame()

    # 2) Daily values for selected years, queried one calendar year at a time.
    daily_parts = []
    for year in range(args.start, args.end + 1):
        start = f"{year}-01-01T00:00:00Z"
        end = f"{year+1}-01-01T00:00:00Z"
        params = dict(common, timeResolution="day",
                      datetime=f"{start}/{end}", limit=300000)
        try:
            features = get_features(BASE, params)
            df = to_frame(features)
            # Keep only records whose interval starts in the requested year.
            if not df.empty:
                df = df[df["from"].dt.year == year]
            daily_parts.append(df)
            print(f"{year}: {len(df):4d} daily records")
        except Exception as exc:
            print(f"{year}: ERROR - {exc}")
            daily_parts.append(pd.DataFrame())

    daily = pd.concat(daily_parts, ignore_index=True) if daily_parts else pd.DataFrame()
    daily.to_csv(out / "daily_api.csv", index=False)
    (out / "daily_api.json").write_text(
        json.dumps([f for part in daily_parts for f in []], ensure_ascii=False), encoding="utf-8"
    )

    if daily.empty:
        print("\nNo daily records returned. Check municipality ID/API response.")
        print(f"Output folder: {out.resolve()}")
        return

    # Coverage and sums. Count records with valid numeric value; validity is reported separately.
    daily["year"] = daily["from"].dt.year
    report = []
    for year in range(args.start, args.end + 1):
        subset = daily[daily["year"] == year]
        expected = 366 if pd.Timestamp(year, 12, 31).dayofyear == 366 else 365
        numeric = subset["value_mm"].notna().sum()
        valid_true = (subset["validity"] == True).sum()  # noqa: E712
        report.append({
            "year": year,
            "records": len(subset),
            "numeric_values": int(numeric),
            "validity_true": int(valid_true),
            "expected_days": expected,
            "coverage_numeric_pct": round(100 * numeric / expected, 2),
            "annual_sum_mm": subset["value_mm"].sum(min_count=1),
        })
    summary = pd.DataFrame(report)
    summary.to_csv(out / "annual_sums_from_daily.csv", index=False)

    print("\nAnnual sums from daily data:")
    print(summary.to_string(index=False))
    complete = summary[summary["coverage_numeric_pct"] >= 99.9]
    if not complete.empty:
        print(f"\nMean over complete years ({len(complete)}): "
              f"{complete['annual_sum_mm'].mean():.1f} mm/year")
    else:
        print("\nNo year reached 99.9% numeric daily coverage.")
    print(f"\nCSV files saved in: {out.resolve()}")


if __name__ == "__main__":
    main()
