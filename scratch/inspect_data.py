# -*- coding: utf-8 -*-
import sys, json, os
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

print("ALLOW_REAL_DATA_MUTATION in os.environ:", os.environ.get("ALLOW_REAL_DATA_MUTATION"))

# 1. class_roster.json
roster_path = Path("backend/class_roster.json")
if roster_path.exists():
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    print(f"\n--- class_roster.json (Count: {len(roster)}) ---")
    for i, m in enumerate(roster):
        print(f"  {i+1}: MSSV={m.get('mssv')}, Tên={m.get('name')}, Vai trò={m.get('role')}, Ví={m.get('wallet')}")

# 2. announcements.json
ann_path = Path("backend/announcements.json")
if ann_path.exists():
    ann = json.loads(ann_path.read_text(encoding="utf-8"))
    print(f"\n--- announcements.json (Keys: {list(ann.keys())}) ---")
    if "notifications" in ann:
        print(f"Notifications count: {len(ann['notifications'])}")
        for n in ann["notifications"]:
            print(f"  ID={n.get('id')}, Status={n.get('status')}, Title={n.get('title')}, classSize={n.get('classSize')}, targetAmountEth={n.get('targetAmountEth')}, createdAt={n.get('createdAt')}, endedAt={n.get('endedAt')}")
    if "active" in ann:
        print(f"Active key: {ann.get('active')}")
    if "history" in ann:
        print(f"History count: {len(ann.get('history', []))}")
        for h in ann.get("history", []):
            print(f"  History item: ID={h.get('id')}, Status={h.get('status')}, Title={h.get('title')}, classSize={h.get('classSize')}, finalProgress={h.get('finalProgress')}")

# 3. announcements.json.pre_fix_backup
bak_path = Path("backend/announcements.json.pre_fix_backup")
if bak_path.exists():
    bak = json.loads(bak_path.read_text(encoding="utf-8"))
    print(f"\n--- announcements.json.pre_fix_backup (Keys: {list(bak.keys())}) ---")
    print(f"Backup Active: ID={bak.get('active', {}).get('id')}, classSize={bak.get('active', {}).get('classSize')}, title={bak.get('active', {}).get('title')}")
    for h in bak.get("history", []):
        print(f"Backup History: ID={h.get('id')}, classSize={h.get('classSize')}, title={h.get('title')}, finalProgress={h.get('finalProgress')}")

# 4. campaign_contributions.json
camp_path = Path("backend/campaign_contributions.json")
if camp_path.exists():
    camp = json.loads(camp_path.read_text(encoding="utf-8"))
    print(f"\n--- campaign_contributions.json (Keys: {list(camp.keys())}) ---")
    campaigns = camp.get("campaigns", {})
    for cid, cdata in campaigns.items():
        print(f"  Campaign ID={cid}: status={cdata.get('status')}, totalContributors={cdata.get('totalContributors')}, targetClassSize={cdata.get('targetClassSize')}, finalProgress={cdata.get('finalProgress')}")

