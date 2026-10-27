"""
Generate synthetic data for an Epic go-live at a fictional hospital
(Northbridge Regional Medical Center). No real tickets or hospital data.

Writes to ./data:
  departments.csv    clinical units in scope for the go-live
  workstations.csv   every device deployed (WOWs, desktops, printers, scanners...)
  tdr_results.csv    Technical Device Readiness testing done before go-live
  tickets.csv        support tickets from 7 days before through 14 days after go-live

Built-in patterns the SQL is meant to uncover:
  * volume peaks on go-live day 1-2, then decays
  * printing and login issues dominate the first 72 hours; workflow questions take over after
  * devices that failed TDR (or were never retested) generate far more tickets
  * night shift tickets wait longer; ATE resolves most workflow issues at the elbow

Usage:
    python generate_data.py
    python generate_data.py --seed 7
"""
import argparse
import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

DATA = Path(__file__).parent / "data"
GO_LIVE = datetime(2026, 10, 1, 0, 0)   # Day 1 starts at midnight

DEPARTMENTS = [
    # id, name, unit_type, staff, weight (ticket share)
    (1, "Emergency Department", "Emergency", 140, 1.5),
    (2, "PACU", "Perioperative", 45, 1.1),
    (3, "Main OR", "Perioperative", 90, 1.2),
    (4, "Pre-Op / Same Day Surgery", "Perioperative", 40, 0.8),
    (5, "Med-Surg 4 West", "Inpatient", 70, 1.0),
    (6, "Medical ICU", "Critical Care", 55, 0.9),
    (7, "Labor & Delivery", "Inpatient", 50, 0.8),
    (8, "Inpatient Pharmacy", "Ancillary", 30, 0.7),
    (9, "Laboratory", "Ancillary", 35, 0.9),
    (10, "Patient Registration", "Access", 40, 0.9),
]

DEVICE_TYPES = [  # type, share of fleet, base failure risk at TDR
    ("Workstation on Wheels", 0.30, 0.08), ("Desktop", 0.30, 0.05), ("Label Printer", 0.12, 0.18),
    ("Laser Printer", 0.08, 0.12), ("Badge Tap Reader", 0.10, 0.10), ("Barcode Scanner", 0.10, 0.09),
]
TDR_FAIL_REASONS = {
    "Workstation on Wheels": ["Wireless drops on unit", "Battery not holding charge", "Missing Epic shortcut"],
    "Desktop": ["Wrong default printer mapped", "Missing Epic shortcut", "Display scaling cuts off Epic"],
    "Label Printer": ["Not mapped in Epic print table", "Wrong label stock size", "Driver mismatch"],
    "Laser Printer": ["Not mapped in Epic print table", "Wrong tray default", "Driver mismatch"],
    "Badge Tap Reader": ["Tap-and-go not configured", "Reader not detected", "Firmware outdated"],
    "Barcode Scanner": ["Wrong scanner profile", "Not reading wristband barcode", "Cable damaged"],
}

# category -> (subcategories, default resolver, at-elbow resolvable share)
CATEGORIES = {
    "Printing": (["Label printer not printing", "Printed to wrong printer", "Specimen label misaligned",
                  "Printer not in Epic list", "AVS not printing"], "Command Center - Technical", 0.25),
    "Login / Access": (["Cannot log in", "Missing security template", "Badge tap not working",
                        "Wrong department context", "Password reset"], "Security / Access", 0.35),
    "Hardware / Device": (["WOW not connecting to wifi", "Scanner not reading", "Monitor issue",
                           "Battery dead on WOW", "Keyboard / mouse failure"], "Desktop Support", 0.20),
    "Workflow / Training": (["How to document in flowsheet", "Cannot find order set", "MAR scanning workflow",
                             "Intraop documentation question", "Handoff report question",
                             "How to sign / cosign orders"], "ATE Floor Support", 0.85),
    "Application / Build": (["Order set missing item", "Flowsheet row missing", "Wrong default in order",
                             "Navigator section missing", "Report not pulling data"], "Epic Application Team", 0.05),
    "Interface": (["Lab results not crossing", "Pharmacy orders not reaching dispensing cabinet",
                   "Device vitals not filing", "ADT not updating bed board"], "Interface Team", 0.0),
}
ROLES = ["RN", "RN", "RN", "MD / Provider", "CRNA / Anesthesia", "Unit Clerk", "Pharmacist", "Lab Tech", "Registrar"]
DEPT_ROLE_BIAS = {8: "Pharmacist", 9: "Lab Tech", 10: "Registrar", 2: "RN", 3: "CRNA / Anesthesia"}
DEPT_CATEGORY_BIAS = {  # extra weight for categories that hit some units harder
    9: {"Printing": 2.5, "Interface": 2.0}, 2: {"Printing": 1.6, "Workflow / Training": 1.3},
    3: {"Workflow / Training": 1.6, "Application / Build": 1.4}, 8: {"Interface": 2.5, "Application / Build": 1.5},
    1: {"Login / Access": 1.5, "Hardware / Device": 1.3}, 10: {"Printing": 1.8, "Login / Access": 1.3},
}
SLA_HOURS = {"P1": 1, "P2": 4, "P3": 24, "P4": 72}


def category_weights(day, dept_id):
    """Category mix shifts over the go-live: technical issues early, workflow later."""
    early = math.exp(-max(day, 0) / 2.5)          # 1.0 at go-live, fades over ~a week
    w = {
        "Printing": 3.0 * early + 0.6,
        "Login / Access": 3.2 * early + 0.4,
        "Hardware / Device": 1.4 * early + 0.5,
        "Workflow / Training": 1.2 + 2.2 * (1 - early),
        "Application / Build": 0.8 + 0.6 * (1 - early),
        "Interface": 0.5 * early + 0.15,
    }
    if day < 0:   # pre-live: dress rehearsal / TDR period
        w = {"Printing": 2.0, "Login / Access": 1.5, "Hardware / Device": 2.0,
             "Workflow / Training": 0.3, "Application / Build": 0.6, "Interface": 0.4}
    for c, m in DEPT_CATEGORY_BIAS.get(dept_id, {}).items():
        w[c] *= m
    return w


def daily_volume(day):
    if day < 0:
        return 18 + 4 * (7 + day)                      # ramping pre-live volume
    return int(260 * math.exp(-day / 3.2) + 35)        # spike on day 0/1, decays toward a steady state


def pick(d):
    keys = list(d)
    return random.choices(keys, weights=[d[k] for k in keys], k=1)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    random.seed(args.seed)
    DATA.mkdir(exist_ok=True)

    # ---- workstations + TDR ----
    workstations, tdr = [], []
    ws_id = 0
    for dept_id, name, *_ in DEPARTMENTS:
        n_devices = random.randint(28, 55)
        for _ in range(n_devices):
            ws_id += 1
            dtype = random.choices([d[0] for d in DEVICE_TYPES], weights=[d[1] for d in DEVICE_TYPES])[0]
            risk = next(d[2] for d in DEVICE_TYPES if d[0] == dtype)
            prefix = {"Workstation on Wheels": "WOW", "Desktop": "PC", "Label Printer": "LBL",
                      "Laser Printer": "LZR", "Badge Tap Reader": "TAP", "Barcode Scanner": "SCN"}[dtype]
            device = f"NRMC-{dept_id:02d}-{prefix}{ws_id:04d}"
            workstations.append({"workstation_id": ws_id, "device_name": device, "department_id": dept_id,
                                 "device_type": dtype, "location": f"Room {random.randint(1, 40):02d}"})
            test_dt = GO_LIVE - timedelta(days=random.randint(10, 21), hours=random.randint(8, 16))
            failed = random.random() < risk
            if failed:
                retest = random.random()
                if retest < 0.65:
                    final, retest_dt = "Pass on retest", test_dt + timedelta(days=random.randint(1, 5))
                elif retest < 0.85:
                    final, retest_dt = "Failed retest", test_dt + timedelta(days=random.randint(1, 5))
                else:
                    final, retest_dt = "Not retested", None
                reason = random.choice(TDR_FAIL_REASONS[dtype])
            else:
                final, retest_dt, reason = "Pass", None, ""
            tdr.append({"tdr_id": ws_id, "workstation_id": ws_id, "tested_dt": test_dt.strftime("%Y-%m-%d %H:%M"),
                        "initial_result": "Fail" if failed else "Pass", "fail_reason": reason,
                        "final_status": final,
                        "retest_dt": retest_dt.strftime("%Y-%m-%d %H:%M") if retest_dt else ""})

    status_by_ws = {t["workstation_id"]: t["final_status"] for t in tdr}
    ws_by_dept = {}
    for w in workstations:
        ws_by_dept.setdefault(w["department_id"], []).append(w)
    # devices that slipped through TDR are the repeat offenders
    ws_weight = {w["workstation_id"]: {"Pass": 1.0, "Pass on retest": 1.8, "Failed retest": 6.0,
                                       "Not retested": 7.0}[status_by_ws[w["workstation_id"]]]
                 for w in workstations}
    hot = random.sample([w["workstation_id"] for w in workstations if status_by_ws[w["workstation_id"]] == "Pass"], 6)
    for h in hot:
        ws_weight[h] = 5.0   # a few passed TDR but still break: TDR isn't perfect

    # ---- tickets ----
    tickets = []
    tid = 0
    dept_weights = {d[0]: d[4] for d in DEPARTMENTS}
    for day in range(-7, 14):   # 7 pre-live days, then go-live days 1-14
        for _ in range(daily_volume(day)):
            tid += 1
            dept_id = pick(dept_weights)
            # more tickets 07:00-11:00 (shift start + morning med pass) and 19:00-21:00
            hour = random.choices(range(24), weights=[1, 1, 1, 1, 1, 1, 2, 6, 7, 7, 6, 5, 4, 4, 4, 3, 3, 3, 3, 5, 4, 2, 1, 1])[0]
            created = GO_LIVE + timedelta(days=day, hours=hour, minutes=random.randint(0, 59))
            category = pick(category_weights(day, dept_id))
            subs, resolver, elbow_share = CATEGORIES[category]
            sub = random.choice(subs)
            if category == "Interface":   # interface issues belong to the unit that consumes the feed
                sub = {8: "Pharmacy orders not reaching dispensing cabinet", 9: "Lab results not crossing"}.get(
                    dept_id, random.choice(["Device vitals not filing", "ADT not updating bed board", "Lab results not crossing"]))

            device_categories = ("Printing", "Hardware / Device", "Login / Access")
            ws = None
            if category in device_categories:
                pool = ws_by_dept[dept_id]
                if category == "Printing":
                    kind = "Label Printer" if sub in ("Label printer not printing", "Specimen label misaligned") else "Laser Printer"
                    pool = [w for w in pool if w["device_type"] == kind] or pool
                elif category == "Login / Access" and "Badge" in sub:
                    pool = [w for w in pool if w["device_type"] == "Badge Tap Reader"] or pool
                elif category == "Login / Access":
                    pool = [w for w in pool if w["device_type"] in ("Workstation on Wheels", "Desktop")] or pool
                elif category == "Hardware / Device":
                    pool = [w for w in pool if w["device_type"] in ("Workstation on Wheels", "Desktop", "Barcode Scanner")] or pool
                ws = random.choices(pool, weights=[ws_weight[w["workstation_id"]] for w in pool])[0]

            # priority
            if category == "Interface":
                priority = random.choices(["P1", "P2", "P3"], weights=[3, 5, 2])[0]
            elif category == "Application / Build":
                priority = random.choices(["P2", "P3", "P4"], weights=[2, 6, 2])[0]
            elif sub in ("Cannot log in", "Label printer not printing", "Specimen label misaligned") and dept_id in (1, 2, 3, 6, 9):
                priority = random.choices(["P1", "P2"], weights=[1, 3])[0]
            else:
                priority = random.choices(["P2", "P3", "P4"], weights=[2, 6, 3])[0]

            night = hour >= 19 or hour < 7
            at_elbow = day >= 0 and random.random() < elbow_share * (0.75 if night else 1.0)
            if at_elbow:
                resolver_group = "ATE Floor Support"
                minutes = random.uniform(4, 35)
                resolution = "Training provided at elbow" if category == "Workflow / Training" else "Fixed at elbow"
                first_response = random.uniform(1, 8)
            else:
                resolver_group = resolver
                base = {"P1": 50, "P2": 180, "P3": 600, "P4": 1500}[priority]
                if category == "Application / Build":
                    base *= 2.2   # build changes go through change control
                minutes = random.lognormvariate(math.log(base), 0.6)
                if night:
                    minutes *= 1.6   # thinner support coverage overnight
                resolution = {"Printing": "Printer remapped", "Login / Access": "Security / access corrected",
                              "Hardware / Device": "Device repaired or swapped", "Workflow / Training": "Tip sheet sent / follow-up training",
                              "Application / Build": "Build change migrated", "Interface": "Interface reprocessed"}[category]
                first_response = random.uniform(3, 25) * (1.8 if night else 1.0)
                if random.random() < 0.04:
                    resolution = "Duplicate ticket"
                    minutes = random.uniform(5, 60)
            resolved = created + timedelta(minutes=minutes)
            end_window = GO_LIVE + timedelta(days=15)
            status = "Resolved" if resolved < end_window else "Open"
            role = DEPT_ROLE_BIAS.get(dept_id) if random.random() < 0.5 else random.choice(ROLES)
            tickets.append({
                "ticket_id": f"INC{1000000 + tid}", "created_dt": created.strftime("%Y-%m-%d %H:%M"),
                "resolved_dt": resolved.strftime("%Y-%m-%d %H:%M") if status == "Resolved" else "",
                "status": status, "go_live_day": day + 1 if day >= 0 else day,  # Day 1 = go-live day; negatives = pre-live
                "department_id": dept_id, "workstation_id": ws["workstation_id"] if ws else "",
                "category": category, "subcategory": sub, "priority": priority, "reported_by_role": role,
                "resolver_group": resolver_group, "resolution": resolution if status == "Resolved" else "",
                "resolved_at_elbow": int(at_elbow), "first_response_min": round(first_response, 1),
                "shift": "Night" if night else "Day"})

    tables = {
        "departments": [dict(zip(["department_id", "name", "unit_type", "staff_count"], d[:4])) for d in DEPARTMENTS],
        "workstations": workstations, "tdr_results": tdr, "tickets": tickets,
        "sla_targets": [{"priority": p, "target_hours": h} for p, h in SLA_HOURS.items()],
    }
    for name, rows in tables.items():
        with open(DATA / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"{name:13s} {len(rows):>6,} rows")


if __name__ == "__main__":
    main()
