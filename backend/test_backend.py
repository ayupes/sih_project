"""
Saarthi AI - Backend Test Suite
--------------------------------
Run this AFTER starting app.py in another terminal, to confirm the
backend is actually working before you push it for your team to build
the frontend against.

HOW TO RUN:
    1. In one terminal: python app.py   (leave it running)
    2. In another terminal: pip install requests --break-system-packages
    3. Then: python test_backend.py

It prints PASS/FAIL for each check and a summary at the end. If
anything fails, DO NOT push yet — fix it first, your team is building
on top of whatever contract this file confirms.
"""

import requests

BASE = "http://127.0.0.1:5000"
passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS  {name}")
        passed += 1
    else:
        print(f"  FAIL  {name}  {detail}")
        failed += 1


print("\n--- /api/health ---")
r = requests.get(f"{BASE}/api/health")
check("returns 200", r.status_code == 200, f"got {r.status_code}")
data = r.json()
check("status is ok", data.get("status") == "ok")
check("schemes_loaded is 17", data.get("schemes_loaded") == 17, f"got {data.get('schemes_loaded')}")

print("\n--- /api/schemes ---")
r = requests.get(f"{BASE}/api/schemes")
check("returns 200", r.status_code == 200)
schemes = r.json()
check("returns a list of 17 schemes", isinstance(schemes, list) and len(schemes) == 17, f"got {len(schemes) if isinstance(schemes, list) else type(schemes)}")

print("\n--- /api/match: valid business case ---")
r = requests.post(f"{BASE}/api/match", json={
    "is_sc": True, "annual_income": 300000, "project_cost": 200000, "purpose": "business"
})
check("returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
data = r.json()
check("eligible is true", data.get("eligible") is True)
eligible_schemes = [s for s in data.get("schemes", []) if s["eligible"]]
check("has at least 1 eligible scheme", len(eligible_schemes) > 0)
check("all eligible schemes have purpose=business", all(s["purpose"] == "business" for s in eligible_schemes),
      f"found: {[s['purpose'] for s in eligible_schemes]}")
check("rank 1 exists and is unique", sum(1 for s in eligible_schemes if s.get("rank") == 1) == 1)
ranks = [s["rank"] for s in eligible_schemes]
check("ranks are sequential starting at 1", ranks == list(range(1, len(ranks) + 1)), f"got {ranks}")
check("top-ranked scheme has lowest interest_rate_min", eligible_schemes[0]["interest_rate_min"] == min(s["interest_rate_min"] for s in eligible_schemes))
check("eligible schemes have documents_required as a non-empty list",
      all(isinstance(s.get("documents_required"), list) and len(s["documents_required"]) > 0 for s in eligible_schemes))
check("eligible schemes have interest_rate as a formatted string",
      all(isinstance(s.get("interest_rate"), str) and "%" in s["interest_rate"] for s in eligible_schemes))

print("\n--- /api/match: purpose mismatch shouldn't leak into results ---")
r = requests.post(f"{BASE}/api/match", json={
    "is_sc": True, "annual_income": 300000, "project_cost": 200000, "purpose": "business"
})
data = r.json()
skill_or_edu_eligible = [s for s in data["schemes"] if s["purpose"] != "business" and s["eligible"]]
check("no education/skill scheme marked eligible for a business request", len(skill_or_edu_eligible) == 0,
      f"found: {[s['name'] for s in skill_or_edu_eligible]}")

print("\n--- /api/match: income too high ---")
r = requests.post(f"{BASE}/api/match", json={
    "is_sc": True, "annual_income": 900000, "project_cost": 200000, "purpose": "business"
})
data = r.json()
check("eligible is false", data.get("eligible") is False)
check("no scheme marked eligible", all(not s["eligible"] for s in data.get("schemes", [])))
income_reasons = [s["reason"] for s in data["schemes"] if "exceeds" in s["reason"] and "income" in s["reason"].lower()]
check("at least one reason explicitly mentions income exceeding the limit", len(income_reasons) > 0)

print("\n--- /api/match: not SC ---")
r = requests.post(f"{BASE}/api/match", json={
    "is_sc": False, "annual_income": 300000, "project_cost": 200000, "purpose": "business"
})
data = r.json()
check("eligible is false", data.get("eligible") is False)
check("schemes list is empty (early exit, not evaluated)", data.get("schemes") == [])

print("\n--- /api/match: missing required field returns 400 ---")
r = requests.post(f"{BASE}/api/match", json={"is_sc": True, "annual_income": 300000})
check("returns 400 when purpose and project_cost are missing", r.status_code == 400, f"got {r.status_code}")

print("\n--- /api/match: education purpose routes correctly ---")
r = requests.post(f"{BASE}/api/match", json={
    "is_sc": True, "annual_income": 250000, "project_cost": 1000000, "purpose": "education"
})
data = r.json()
edu_eligible = [s for s in data["schemes"] if s["eligible"]]
check("education request only matches education-purpose schemes",
      all(s["purpose"] == "education" for s in edu_eligible), f"found: {[s['purpose'] for s in edu_eligible]}")

print("\n--- /api/match: boundary - cost exactly at a scheme's max ---")
r = requests.post(f"{BASE}/api/match", json={
    "is_sc": True, "annual_income": 300000, "project_cost": 140000, "purpose": "business"
})
check("returns 200 without error at boundary value", r.status_code == 200)

print("\n--- /api/parse: empty text returns 400 ---")
r = requests.post(f"{BASE}/api/parse", json={"text": ""})
check("returns 400 for empty text", r.status_code == 400, f"got {r.status_code}")

print("\n--- /api/parse: real extraction (needs a REAL Gemini key + internet) ---")
try:
    r = requests.post(f"{BASE}/api/parse", json={
        "text": "I am SC, my income is 3 lakh, I want to start a tailoring shop costing 2 lakh"
    }, timeout=15)
    if r.status_code == 200:
        data = r.json()
        check("is_sc extracted as true", data.get("is_sc") is True)
        check("annual_income extracted as 300000", data.get("annual_income") == 300000, f"got {data.get('annual_income')}")
        check("project_cost extracted as 200000", data.get("project_cost") == 200000, f"got {data.get('project_cost')}")
        check("purpose extracted as business", data.get("purpose") == "business", f"got {data.get('purpose')}")
        check("project_type is Tailoring/garments", data.get("project_type") == "Tailoring/garments", f"got {data.get('project_type')}")
        check("missing_fields is empty", data.get("missing_fields") == [], f"got {data.get('missing_fields')}")
    else:
        print(f"  SKIP  Gemini call failed ({r.status_code}) - check your GEMINI_API_KEY in .env, this is expected if it's not set up yet")
except requests.exceptions.RequestException as e:
    print(f"  SKIP  Could not reach /api/parse - {e}")

print(f"\n{'='*40}")
print(f"RESULT: {passed} passed, {failed} failed")
print("Safe to push." if failed == 0 else "DO NOT PUSH - fix the failures above first.")
print(f"{'='*40}\n")
