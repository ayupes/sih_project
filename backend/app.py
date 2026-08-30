"""
Saarthi AI - Backend API
-------------------------
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)
CORS(app)

_gemini_client = genai.Client()

GEMINI_SYSTEM_PROMPT = """\
You are a structured-data extraction assistant for a government-scheme eligibility checker called Saarthi AI.

The user will send a free-form message in Hindi or English (or a mix).
Your job is to extract ONLY the fields listed below from that message and return them as a JSON object.

FIELDS TO EXTRACT:
- purpose          : "business", "education", or "skill" - only if explicitly mentioned, else null
- is_sc            : true or false - only if the user mentions SC / Scheduled Caste status, else null
- annual_income    : number (rupees, no commas/symbols) - only if mentioned, else null
- project_cost     : number (rupees) - only if mentioned, else null
- project_type     : one of exactly these values: "Tailoring/garments", "Food processing",
                     "Retail/shop", "Manufacturing/handicrafts", "Transport", "Services",
                     "Agriculture-allied", "Other" - pick the closest match; use "Other"
                     if the business doesn't clearly fit any category; null if not mentioned
- course_fee       : number (rupees) - only if mentioned and purpose is education, else null
- study_location   : "India" or "Abroad" - only if mentioned, else null

STRICT RULES:
1. If a field is not clearly mentioned, set it to null. Do NOT guess or infer.
2. Convert amounts written as words ("5 lakh", "5 lakh") to plain numbers (500000).
3. "SC", "Scheduled Caste" -> is_sc: true.
4. Output ONLY the JSON object - no explanation, no markdown, no extra text.

OUTPUT FORMAT (always exactly this shape):
{
  "purpose": "business" | "education" | "skill" | null,
  "is_sc": true | false | null,
  "annual_income": number | null,
  "project_cost": number | null,
  "project_type": string | null,
  "course_fee": number | null,
  "study_location": "India" | "Abroad" | null
}
"""

REQUIRED_FIELDS = ["purpose", "is_sc", "annual_income", "project_cost"]

CSV_DIR = os.path.dirname(__file__)
schemes_df = pd.read_csv(os.path.join(CSV_DIR, "schemes.csv"))
documents_df = pd.read_csv(os.path.join(CSV_DIR, "documents.csv"))


def load_schemes():
    return schemes_df.to_dict(orient="records")


def get_documents_for_scheme(scheme_id):
    rows = documents_df[documents_df["scheme_id"] == scheme_id].sort_values("display_order")
    return [{"name": r["document_name"], "mandatory": r["mandatory"] == "Yes"} for _, r in rows.iterrows()]


def format_interest_display(min_r, max_r):
    return f"{min_r}%" if min_r == max_r else f"{min_r}%-{max_r}%"


def build_reason(scheme, annual_income, project_cost, purpose):
    if purpose != scheme["purpose"]:
        return f"This scheme is for {scheme['purpose']} purposes; your stated purpose was {purpose}."
    if scheme["max_income"] > 0 and annual_income > scheme["max_income"]:
        return f"Your annual income of Rs {annual_income:,.0f} exceeds this scheme's Rs {scheme['max_income']:,.0f} limit."
    if project_cost < scheme["min_project_cost"]:
        return f"Your project cost of Rs {project_cost:,.0f} is below this scheme's minimum of Rs {scheme['min_project_cost']:,.0f}."
    if project_cost > scheme["max_project_cost"]:
        return f"Your project cost of Rs {project_cost:,.0f} exceeds this scheme's maximum of Rs {scheme['max_project_cost']:,.0f}."
    if scheme["max_income"] == 0:
        income_part = "No income limit applies for this scheme"
    else:
        income_part = f"Your income of Rs {annual_income:,.0f} is within the Rs {scheme['max_income']:,.0f} limit"
    return (f"{income_part}, "
            f"and your project cost of Rs {project_cost:,.0f} fits this scheme's "
            f"Rs {scheme['min_project_cost']:,.0f}–Rs {scheme['max_project_cost']:,.0f} range.")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "schemes_loaded": len(schemes_df), "documents_loaded": len(documents_df)})


@app.route("/api/schemes", methods=["GET"])
def get_all_schemes():
    return jsonify(load_schemes())


@app.route("/api/match", methods=["POST"])
def match_schemes():
    data = request.get_json(force=True, silent=True) or {}
    is_sc = data.get("is_sc")
    annual_income = data.get("annual_income")
    project_cost = data.get("project_cost")
    purpose = data.get("purpose")

    if is_sc is None or annual_income is None or project_cost is None or purpose is None:
        return jsonify({
            "eligible": False,
            "message": "Missing one of: is_sc, annual_income, project_cost, purpose",
            "schemes": []
        }), 400

    if not is_sc:
        return jsonify({"eligible": False, "message": "These schemes require Scheduled Caste status.", "schemes": []})

    evaluated = []
    for scheme in load_schemes():
        purpose_ok = purpose == scheme["purpose"]
        cost_ok = scheme["min_project_cost"] <= project_cost <= scheme["max_project_cost"]
        income_ok = scheme["max_income"] == 0 or annual_income <= scheme["max_income"]
        eligible = purpose_ok and cost_ok and income_ok

        entry = {
            "name": scheme["name"],
            "description": scheme["description"],
            "scheme_type": scheme["scheme_type"],
            "purpose": scheme["purpose"],
            "eligible": eligible,
            "reason": build_reason(scheme, annual_income, project_cost, purpose),
            "source_url": scheme["source_url"],
        }
        if eligible:
            estimated_loan = min(project_cost * scheme["finance_percent"] / 100, scheme["max_loan"])
            entry.update({
                "estimated_loan": round(estimated_loan),
                "applicant_contribution": round(project_cost - estimated_loan),
                "max_loan": scheme["max_loan"],
                "interest_rate": format_interest_display(scheme["interest_rate_min"], scheme["interest_rate_max"]),
                "interest_rate_min": scheme["interest_rate_min"],
                "interest_rate_max": scheme["interest_rate_max"],
                "repayment_years": int(scheme["repayment_years"]),
                "moratorium_months": int(scheme["moratorium_months"]),
                "documents_required": get_documents_for_scheme(scheme["scheme_id"]),
            })
        evaluated.append(entry)

    eligible_schemes = sorted([s for s in evaluated if s["eligible"]], key=lambda s: s["interest_rate_min"])
    not_eligible = [s for s in evaluated if not s["eligible"]]
    for i, s in enumerate(eligible_schemes):
        s["rank"] = i + 1
    for s in not_eligible:
        s["rank"] = None

    if not eligible_schemes:
        return jsonify({"eligible": False, "message": "No scheme matches this applicant.", "schemes": not_eligible})
    return jsonify({
        "eligible": True,
        "message": f"Found {len(eligible_schemes)} matching scheme(s), ranked by lowest interest rate.",
        "schemes": eligible_schemes + not_eligible
    })


@app.route("/api/parse", methods=["POST"])
def parse_user_text():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Request body must include a non-empty 'text' field."}), 400
    try:
        response = _gemini_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=text,
            config=types.GenerateContentConfig(
                system_instruction=GEMINI_SYSTEM_PROMPT,
                response_mime_type="application/json",
            ),
        )
        extracted = json.loads(response.text)
    except Exception as exc:
        return jsonify({"error": f"Gemini API call failed: {exc}"}), 503

    missing = [f for f in REQUIRED_FIELDS if extracted.get(f) is None]
    extracted["missing_fields"] = missing
    return jsonify(extracted)


if __name__ == "__main__":
    app.run(debug=False, port=5000)
