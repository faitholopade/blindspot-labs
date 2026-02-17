"""
download_data.py — Download and process Dublin City Council planning data

Uses the public ArcGIS Feature Service for Irish Planning Applications,
hosted by the Department of Housing. This API is reliable and requires
no authentication.

Source: https://services.arcgis.com/NzlPQPKn5QF9v2US/arcgis/rest/services/
        IrishPlanningApplications/FeatureServer/0
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime, timezone

# Data directory
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# ArcGIS Feature Service endpoint — public, no auth needed
ARCGIS_BASE = "https://services.arcgis.com/NzlPQPKn5QF9v2US/arcgis/rest/services/IrishPlanningApplications/FeatureServer/0/query"

# We want Dublin City Council records only
PLANNING_AUTHORITY = "Dublin City Council"

# How many records to fetch per request (ArcGIS max is usually 2000)
PAGE_SIZE = 2000

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def fetch_record_count():
    """Get total number of Dublin City Council records."""
    params = {
        "where": f"PlanningAuthority='{PLANNING_AUTHORITY}'",
        "returnCountOnly": "true",
        "f": "json",
    }
    
    response = requests.get(ARCGIS_BASE, params=params, headers=HEADERS, timeout=60)
    response.raise_for_status()
    data = response.json()
    
    if "count" in data:
        return data["count"]
    else:
        print(f"  Warning: Unexpected response: {json.dumps(data)[:200]}")
        return 0


def fetch_page(offset, page_size=PAGE_SIZE):
    """Fetch a page of records from the ArcGIS API."""
    params = {
        "where": f"PlanningAuthority='{PLANNING_AUTHORITY}'",
        "outFields": "*",
        "resultOffset": str(offset),
        "resultRecordCount": str(page_size),
        "orderByFields": "OBJECTID ASC",
        "f": "json",
    }
    
    response = requests.get(ARCGIS_BASE, params=params, headers=HEADERS, timeout=120)
    response.raise_for_status()
    data = response.json()
    
    if "features" in data:
        return [f["attributes"] for f in data["features"]]
    elif "error" in data:
        print(f"\n  API error: {data['error']}")
        return []
    else:
        return []


def download_all_data():
    """Download all Dublin City Council planning records via ArcGIS API."""
    print("=" * 60)
    print("STEP 1: Downloading Dublin City Council Planning Data")
    print("       (via ArcGIS Irish Planning Applications API)")
    print("=" * 60)
    print()
    
    # Check if already downloaded
    raw_path = DATA_DIR / "raw_records.json"
    if raw_path.exists() and raw_path.stat().st_size > 10000:
        print(f"  Already downloaded ({raw_path.stat().st_size // 1024}KB)")
        print(f"    Delete {raw_path} to re-download")
        return True
    
    # Get total count
    print(f"  Querying record count for '{PLANNING_AUTHORITY}'...")
    try:
        total = fetch_record_count()
    except Exception as e:
        print(f"  Failed to query API: {e}")
        return False
    
    if total == 0:
        print("  No records found. The API may be temporarily unavailable.")
        return False
    
    print(f"  Found {total:,} planning records for Dublin City Council")
    print()
    
    # Fetch all records in pages
    all_records = []
    offset = 0
    page_num = 0
    
    while offset < total:
        page_num += 1
        try:
            records = fetch_page(offset)
            
            if not records:
                print(f"\n  Warning: Empty page at offset {offset}, retrying...")
                time.sleep(2)
                records = fetch_page(offset)
                if not records:
                    print(f"  Skipping to next page...")
                    offset += PAGE_SIZE
                    continue
            
            all_records.extend(records)
            pct = min(100, (len(all_records) / total) * 100)
            print(f"\r  Progress: {pct:.1f}% -- {len(all_records):,} / {total:,} records (page {page_num})", end="", flush=True)
            
            offset += PAGE_SIZE
            
            # Small delay to be respectful to the API
            if page_num % 5 == 0:
                time.sleep(0.5)
                
        except requests.exceptions.RequestException as e:
            print(f"\n  Warning: Request failed at offset {offset}: {e}")
            print(f"  Waiting 5 seconds and retrying...")
            time.sleep(5)
            try:
                records = fetch_page(offset)
                if records:
                    all_records.extend(records)
                offset += PAGE_SIZE
            except Exception:
                print(f"  Skipping batch at offset {offset}")
                offset += PAGE_SIZE
    
    print(f"\n\n  Downloaded {len(all_records):,} records")
    
    # Save raw data
    with open(raw_path, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, default=str)
    
    print(f"  Saved to {raw_path} ({raw_path.stat().st_size // 1024}KB)")
    return True


def format_date(epoch_ms):
    """Convert ArcGIS epoch milliseconds to readable date string."""
    if not epoch_ms or str(epoch_ms).strip() in ('None', 'nan', '', '0'):
        return ''
    try:
        if isinstance(epoch_ms, (int, float)):
            dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d")
        else:
            return str(epoch_ms).strip()
    except (ValueError, TypeError, OSError):
        return ''


def clean_and_process_data():
    """Clean and process the downloaded records into structured format."""
    print()
    print("=" * 60)
    print("STEP 2: Cleaning and Processing Data")
    print("=" * 60)
    print()
    
    raw_path = DATA_DIR / "raw_records.json"
    if not raw_path.exists():
        print("  Raw data not found. Run download first.")
        return False
    
    print("  Loading raw records...")
    with open(raw_path, 'r', encoding='utf-8') as f:
        raw_records = json.load(f)
    
    print(f"  Loaded {len(raw_records):,} records")
    
    # Process into clean structured records
    records = []
    for raw in raw_records:
        record = {
            "ref": _clean(raw.get("ApplicationNumber")),
            "location": _clean(raw.get("DevelopmentAddress")),
            "postcode": _clean(raw.get("DevelopmentPostcode")),
            "proposal": _clean(raw.get("DevelopmentDescription")),
            "long_proposal": _clean(raw.get("DevelopmentDescription")),
            "app_type": _clean(raw.get("ApplicationType")),
            "app_status": _clean(raw.get("ApplicationStatus")),
            "decision": _clean(raw.get("Decision")),
            "reg_date": format_date(raw.get("ReceivedDate")),
            "dec_date": format_date(raw.get("DecisionDate")),
            "grant_date": format_date(raw.get("GrantDate")),
            "expiry_date": format_date(raw.get("ExpiryDate")),
            "appeal_ref": _clean(raw.get("AppealRefNumber")),
            "appeal_status": _clean(raw.get("AppealStatus")),
            "appeal_decision": _clean(raw.get("AppealDecision")),
            "appeal_decision_date": format_date(raw.get("AppealDecisionDate")),
            "fi_request_date": format_date(raw.get("FIRequestDate")),
            "fi_received_date": format_date(raw.get("FIRecDate")),
            "num_units": _clean(raw.get("NumResidentialUnits")),
            "floor_area": _clean(raw.get("FloorArea")),
            "link": _clean(raw.get("LinkAppDetails")),
            "has_appeal": bool(
                _clean(raw.get("AppealRefNumber")) or 
                _clean(raw.get("AppealStatus"))
            ),
            "appeal_details": [],
        }
        
        # Build appeal details if present
        if record['has_appeal']:
            appeal_info = {}
            if record['appeal_ref']:
                appeal_info['AppealRef'] = record['appeal_ref']
            if record['appeal_status']:
                appeal_info['Status'] = record['appeal_status']
            if record['appeal_decision']:
                appeal_info['Decision'] = record['appeal_decision']
            if record['appeal_decision_date']:
                appeal_info['DecisionDate'] = record['appeal_decision_date']
            if appeal_info:
                record['appeal_details'] = [appeal_info]
        
        # Fix decision display
        if record['decision'] in ('N/A', ''):
            if record['app_status'] in ('DEEMED WITHDRAWN', 'WITHDRAWN', 'INCOMPLETED APPLICATION'):
                record['decision'] = record['app_status']
            elif not record['decision']:
                record['decision'] = 'Pending'
        
        # ── Land & development classification (public vs private value-add) ──
        # This classification enables the commercial insight Kevin identified:
        # public land developments vs private land, and categorisation for
        # targeted access (developers, solicitors, architects, etc.)
        proposal_lower = (record['proposal'] or '').lower()
        location_lower = (record['location'] or '').lower()
        
        # Development category
        if any(kw in proposal_lower for kw in ['dwelling', 'house', 'residential', 'apartment', 'flat', 'duplex']):
            record['dev_category'] = 'residential'
        elif any(kw in proposal_lower for kw in ['office', 'commercial', 'retail', 'shop', 'restaurant', 'hotel']):
            record['dev_category'] = 'commercial'
        elif any(kw in proposal_lower for kw in ['industrial', 'warehouse', 'factory', 'storage']):
            record['dev_category'] = 'industrial'
        elif any(kw in proposal_lower for kw in ['school', 'college', 'university', 'creche', 'childcare']):
            record['dev_category'] = 'education'
        elif any(kw in proposal_lower for kw in ['church', 'hospital', 'clinic', 'community', 'public']):
            record['dev_category'] = 'public_institutional'
        elif any(kw in proposal_lower for kw in ['extension', 'conversion', 'alteration', 'renovation']):
            record['dev_category'] = 'modification'
        elif any(kw in proposal_lower for kw in ['demolition', 'demolish']):
            record['dev_category'] = 'demolition'
        else:
            record['dev_category'] = 'other'
        
        # Land type indicator (public vs private land signals)
        if any(kw in location_lower for kw in ['council', 'public', 'park', 'civic', 'library', 'garda']):
            record['land_type'] = 'public'
        elif any(kw in proposal_lower for kw in ['social housing', 'affordable housing', 'council housing', 'part v']):
            record['land_type'] = 'public_housing'
        else:
            record['land_type'] = 'private'
        
        # Scale indicator (useful for targeting developers vs homeowners)
        num_units = record.get('num_units', '')
        try:
            units = int(num_units) if num_units else 0
        except (ValueError, TypeError):
            units = 0
        
        if units >= 50 or any(kw in proposal_lower for kw in ['strategic housing development', 'shd', 'large-scale']):
            record['dev_scale'] = 'large'
        elif units >= 10:
            record['dev_scale'] = 'medium'
        elif units >= 2:
            record['dev_scale'] = 'small_multi'
        else:
            record['dev_scale'] = 'single'
        
        # Skip records with no reference
        if not record['ref']:
            continue
        
        records.append(record)
    
    print(f"  Processed {len(records):,} valid records")
    
    # Save processed records
    processed_path = DATA_DIR / "processed_records.json"
    with open(processed_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"  Saved to {processed_path}")
    
    # Print stats
    from collections import Counter
    decisions = [r['decision'] for r in records if r['decision']]
    decision_counts = Counter(decisions)
    print(f"\n  Decision breakdown (top 10):")
    for decision, count in decision_counts.most_common(10):
        print(f"    {decision}: {count:,}")
    
    appeal_count = sum(1 for r in records if r['has_appeal'])
    print(f"\n  Records with appeals: {appeal_count:,}")
    
    return True


def _clean(value):
    """Clean a value: convert None/nan/N/A to empty string."""
    if value is None:
        return ''
    s = str(value).strip()
    if s in ('None', 'nan', 'N/A'):
        return ''
    return s


def main():
    print()
    print("=" * 58)
    print("  Blindspot Labs -- Dublin Planning Data Acquisition")
    print("  The Strange Data Project | Nomad AI Competition")
    print("=" * 58)
    print()
    
    # Step 1: Download
    if not download_all_data():
        print("\nData download failed.")
        sys.exit(1)
    
    # Step 2: Clean and process
    if not clean_and_process_data():
        print("\nData processing failed.")
        sys.exit(1)
    
    # Step 3: Build vector database
    print()
    print("=" * 60)
    print("STEP 3: Building Vector Database")
    print("=" * 60)
    print()
    print("  Running build_vectordb.py...")
    
    from build_vectordb import build_vector_database
    build_vector_database()
    
    print()
    print("=" * 58)
    print("  Setup complete!")
    print()
    print("  Run the chat interface:")
    print("    streamlit run app.py")
    print("=" * 58)


if __name__ == "__main__":
    main()
