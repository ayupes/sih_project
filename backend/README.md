# Backend — Saarthi AI

A Flask API. It has 3 endpoints. That's the whole backend for now.

## Run it

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Leave that terminal running. Open `http://127.0.0.1:5000/api/health` in a
browser — if you see `{"status": "ok", ...}`, it's working.

**Mac users:** if port 5000 doesn't respond, it's usually AirPlay Receiver
using it. Either turn that off (System Settings → General → AirDrop &
Handoff), or change `port=5000` to `port=5001` in `app.py` (and tell the
frontend team to update their URL to match).

## The 3 endpoints

| Method | URL | What it does |
|---|---|---|
| GET | `/api/health` | "Am I alive?" check |
| GET | `/api/schemes` | Returns all 4 schemes as-is |
| POST | `/api/match` | The real logic — send an applicant, get matches back |

## `/api/match` — the contract

This is the exact shape the frontend and backend agreed on. If both sides
stick to this, they don't need to coordinate on anything else.

**Send this:**
```json
{
  "is_sc": true,
  "annual_income": 320000,
  "project_cost": 300000
}
```

**Get this back (eligible):**
```json
{
  "eligible": true,
  "message": "Found 2 matching scheme(s).",
  "schemes": [
    {
      "name": "Term Loan",
      "estimated_loan": 270000,
      "applicant_contribution": 30000,
      "interest_rate": "8%",
      "repayment_years": 7,
      "source_url": "https://nsfdc.nic.in/scheme"
    }
  ]
}
```

**Get this back (not eligible):**
```json
{
  "eligible": false,
  "message": "Annual family income exceeds the Rs 500,000 limit for these schemes.",
  "schemes": []
}
```

## Where the scheme data lives

`schemes.csv`. It's already filled in with the 4 real NSFDC schemes so the
app works right now. Whoever is doing the CSV research just needs to edit
the **values** in this file — don't rename the columns, `app.py` reads them
by name.

## Giving this to Antigravity

Don't ask it to build a backend from scratch — this one already works.
Ask it to **extend** it. Open the `backend` folder in Antigravity and give
it small, specific jobs, one at a time, e.g.:

> This Flask app in app.py matches applicants to schemes in schemes.csv.
> Add a new field "moratorium_months" to schemes.csv and include it in the
> /api/match response for each matched scheme. Don't change anything else
> about the response shape or the existing endpoints.

Test after every change (`python app.py`, hit `/api/health`) before asking
for the next one. If something breaks, paste the error back to it —
that's a much better prompt than re-describing the whole feature.
