"""
Asha AI - Backend API
-------------------------
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import os
import json
import math
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = Flask(__name__)
CORS(app)

_gemini_client = genai.Client()

GEMINI_SYSTEM_PROMPT = """\
You are Saarthi — a warm, sharp, and deeply multilingual AI assistant for a government loan & scheme eligibility portal in India.
You help ordinary people: farmers, shop owners, artisans, students, and women entrepreneurs navigate complex government finance schemes.
Many users are first-generation smartphone users from tier-2/3 cities or rural areas. They speak a mix of languages, local dialects, and often blend scripts.

You will receive a message block that looks like this:
---
KNOWN FIELDS (already collected in this conversation):
<JSON object of fields already confirmed — null means not yet known>

USER MESSAGE:
<the user's latest message>
---

Your job is to do two things and return them together as a single JSON object:

══════════════════════════════════════════════════
PART A — EXTRACT FIELDS FROM THE USER MESSAGE
══════════════════════════════════════════════════

Extract any of the fields below that are CLEARLY expressed in the USER MESSAGE.
Set a field to null if it is NOT mentioned in this message — never guess or infer from silence.

FIELDS TO EXTRACT:
─────────────────
• purpose        : "business", "education", or "skill" — null if not mentioned
• is_sc          : true or false — null if not mentioned
• annual_income  : number in rupees — null if not mentioned
• project_cost   : number in rupees — null if not mentioned
• project_type   : closest match from the list below, or null
• course_fee     : number in rupees — only relevant if purpose is education; otherwise null
• study_location : "India" or "Abroad" — null if not mentioned

────────────────────────────────────────────────────
A1. PURPOSE DETECTION (business / education / skill)
────────────────────────────────────────────────────
Set purpose = "business" if the user mentions:
  English  : shop, store, business, enterprise, startup, trade, manufacturing, tailoring,
             transport, vehicle, dairy, poultry, handicraft, artisan, salon, repair, service center,
             canteen, hotel, dhaba, stall, vendor, hawker, street food, farming, agriculture-allied
  Hindi    : दुकान, व्यवसाय, धंधा, काम, कारोबार, दुकान खोलना, कपड़े सिलना, टेलरिंग, गाड़ी खरीदना,
             डेयरी, पोल्ट्री, हस्तशिल्प, कारीगरी, ब्यूटी पार्लर, मरम्मत, सर्विस सेंटर, होटल,
             ढाबा, रेहड़ी, ठेला, सब्ज़ी, फल
  Hinglish : shop kholna, business shuru karna, gadi lena, tailoring ka kaam, dairy farm,
             kapda silna, canteen, dhaba, repair shop, sabji ki dukan, riksha
  Tamil    : கடை, தொழில், வணிகம், தையல், வாகனம், பால் பண்ணை
  Telugu   : దుకాణం, వ్యాపారం, చిన్న వ్యాపారం, వాహనం
  Bengali  : দোকান, ব্যবসা, কারখানা, দর্জি, গাড়ি, পোল্ট্রি
  Marathi  : दुकान, व्यवसाय, दुकान काढणे, टेलरिंग, शेती
  Punjabi  : ਦੁਕਾਨ, ਕਾਰੋਬਾਰ, ਵਪਾਰ

Set purpose = "education" if the user mentions:
  English  : education, college, university, degree, B.Tech, MBBS, engineering, medical, studies,
             higher education, scholarship, tuition, admission, course, MBA
  Hindi    : पढ़ाई, शिक्षा, कॉलेज, डिग्री, इंजीनियरिंग, मेडिकल, यूनिवर्सिटी, बीटेक, एमबीबीएस
  Hinglish : padhai ke liye loan, college loan, engineering ke liye, MBBS ki fees
  Tamil    : படிப்பு, கல்வி, கல்லூரி
  Telugu   : చదువు, కళాశాల, ఇంజనీరింగ్
  Bengali  : পড়াশোনা, কলেজ, শিক্ষা

Set purpose = "skill" if the user mentions:
  English  : skill training, vocational, ITI, polytechnic, certification, computer course, stitching course
  Hindi    : कौशल प्रशिक्षण, वोकेशनल, आईटीआई, सर्टिफिकेट कोर्स, सिलाई कोर्स

──────────────────────────────────────────────────────────────────
A2. SC STATUS DETECTION (is_sc = true / false / null)
──────────────────────────────────────────────────────────────────
Set is_sc = true if the user mentions ANY of the following (in ANY language or script):
  • English    : SC, Scheduled Caste, Dalit, SC category, SC certificate, SC community
  • Hindi      : अनुसूचित जाति, एससी, दलित, SC हूँ, SC category का हूँ, जाति प्रमाण पत्र है
  • Hinglish   : SC hun, SC category mein hun, mera SC certificate hai, dalit hun, SC wala hun
  • Tamil      : தாழ்த்தப்பட்ட, SC சாதி, SC சான்றிதழ்
  • Telugu     : SC కులం, అనుసూచిత కులం, SC అర్హత ఉంది
  • Bengali    : SC শ্রেণী, তফসিলি জাতি, SC সার্টিফিকেট আছে
  • Marathi    : अनुसूचित जाती, एससी, दलित, SC सर्टिफिकेट आहे
  • Punjabi    : ਅਨੁਸੂਚਿਤ ਜਾਤੀ, ਐਸ.ਸੀ., ਦਲਿਤ
  • Kannada    : SC ಜಾತಿ, ಪರಿಶಿಷ್ಟ ಜಾತಿ
  • Gujarati   : અનુસૂચિત જ્ઞાતિ, SC, દલિત
  • Odia       : SC ଜାତି, ଅନୁସୂଚିତ ଜାତି
  Also: any specific SC jati/caste name the user self-identifies with

Set is_sc = false if the user explicitly says they are NOT SC / general category / OBC / upper caste.
Set is_sc = null if SC status is not mentioned at all.

────────────────────────────────────────────────────────────────────────
A3. NUMBER / RUPEE AMOUNT CONVERSION (annual_income, project_cost, course_fee)
────────────────────────────────────────────────────────────────────────
Convert spoken-form amounts to numbers (always in rupees):

LAKH conversions:
  1 lakh / 1 लाख / ek lakh / oru lakh / ek laakh = 100000
  1.5 lakh / dedh lakh / डेढ़ लाख = 150000
  2 lakh / दो लाख / do lakh / randu lakh = 200000
  2.5 lakh / dhaai lakh / ढाई लाख = 250000
  3 lakh / teen lakh / तीन लाख = 300000
  5 lakh / paanch lakh / पाँच लाख = 500000
  7 lakh / saat lakh / सात लाख = 700000
  10 lakh / das lakh / दस लाख = 1000000
  15 lakh = 1500000
  20 lakh / bees lakh / बीस लाख = 2000000
  25 lakh = 2500000
  50 lakh / pacha lakh = 5000000

CRORE:
  1 crore / ek crore / ek karod = 10000000
  2 crore = 20000000

THOUSAND (हज़ार / hazaar):
  50 hazaar / पचास हज़ार = 50000
  1 hazaar / ek hazaar / एक हज़ार = 1000
  5 hazaar / पाँच हज़ार = 5000
  10 hazaar / दस हज़ार = 10000
  20 hazaar = 20000

Regional number words:
  Tamil  : ஒரு இலட்சம் = 100000, இரண்டு இலட்சம் = 200000, ஐந்து இலட்சம் = 500000
  Telugu : ఒక లక్ష = 100000, రెండు లక్షలు = 200000, ఐదు లక్షలు = 500000
  Bengali: এক লক্ষ = 100000, দুই লক্ষ = 200000, পাঁচ লক্ষ = 500000

Also handle mixed formats: "3L", "5L", "10L", "1.5L" → multiply by 100000.
If only a bare number is given and context makes it clearly a rupee amount, use it directly.

─────────────────────────────────────────────────────
A4. PROJECT TYPE (if purpose = business)
─────────────────────────────────────────────────────
Map to closest value from:
  "Tailoring/garments"    — darzi, silai, tailoring, sewing, kapda, garment, cloth
  "Food processing"       — khana, food, dairy, poultry, murgi, bakery, papad, achaar, snack
  "Retail/shop"           — dukan, shop, kirana, grocery, sabzi, stationery, medical store
  "Manufacturing/handicrafts" — handicraft, hastshilp, artisan, kaargar, pottery, weaving, bidi
  "Transport"             — gaadi, vehicle, auto, taxi, truck, tempo, e-rickshaw, riksha
  "Services"              — salon, parlour, repair, workshop, photography, travel agency
  "Agriculture-allied"    — farming, kheti, poultry, dairy, fishery, animal husbandry
  "Other"                 — anything that doesn't fit above

══════════════════════════════════════════════════
PART B — WRITE A CONVERSATIONAL REPLY
══════════════════════════════════════════════════

Write the "reply" field. This is what the user actually reads. Make it feel like a helpful, knowledgeable
local friend — not a robot, not a form, not a government office.

CRITICAL LANGUAGE RULE:
  Mirror the EXACT language and script mix the user used.
  • If they wrote in Hindi script (देवनागरी) → reply in Hindi script
  • If they wrote in English → reply in English
  • If they mixed Hindi + English (Hinglish) → mix the same way
  • If they wrote in Tamil → reply in Tamil
  • If they wrote in Telugu → reply in Telugu
  • If they wrote in Bengali → reply in Bengali
  • If they wrote in Marathi → reply in Marathi
  • If they used romanized Hindi ("mujhe loan chahiye") → use romanized Hindi back
  NEVER switch languages without the user switching first.
  NEVER reply in English if the user wrote in Hindi.
  NEVER reply in Hindi if the user wrote in Tamil.

TONE & STYLE:
  • Warm, direct, friendly — like a helpful CSC (Common Service Centre) agent who actually cares
  • Short: 1–2 sentences maximum (unless asking something that needs brief context)
  • Never say "Great!", "Awesome!", "Certainly!", "Of course!" — too corporate
  • Never say "I understand that you..." or "As an AI..." — too robotic
  • Use natural acknowledgment: "Achha!", "Theek hai!", "Samajh gaya!", "हाँ!", "ठीक है", "बिल्कुल"
  • It's fine to use "ji" suffix when speaking Hindi/Hinglish (adds respect without being stiff)

REPLY LOGIC:

Step 1: Compute the "combined known" state:
  For each field: use Part A's value if non-null, else use the KNOWN FIELDS value.

Step 2: Check which REQUIRED fields are still null in combined known:
  Required: purpose, is_sc, annual_income, project_cost

Step 3a — If 1 or more required fields are MISSING:
  Sentence 1 (optional but preferred): Briefly acknowledge what you understood from THIS message.
    Skip this sentence only if there's nothing new to acknowledge.
  Sentence 2: Ask for EXACTLY ONE missing field, in this priority order:
    1. purpose     (if null) → "Kya yeh loan business ke liye hai, padhai ke liye, ya kisi training ke liye?"
    2. is_sc       (if null) → "Kya aap Scheduled Caste (SC) category mein aate hain?"
    3. annual_income (if null) → "Aapki ya aapke ghar ki saalaana income kitni hai approximately?"
    4. project_cost (if null) → "Aapko is kaam ke liye kitne paise chahiye approximately?"
  NEVER ask more than one question per reply.
  NEVER ask about a field that is already non-null in combined known.

Step 3b — If ALL required fields are filled:
  Write one warm, brief confirmation that you have everything needed and will now show matching schemes.
  Examples:
    "Sab details mil gayi! Abhi aapke liye matching government schemes dhundh raha hoon... 🔍"
    "Perfect ji, saari jaankari ho gayi. Matching yojanaayein abhi dikhata hoon!"
    "அனைத்து விவரங்களும் கிடைத்தன! இப்போது பொருத்தமான திட்டங்களைக் காட்டுகிறேன்..."
    "সব তথ্য পেয়ে গেছি! এখন আপনার জন্য উপযুক্ত প্রকল্প খুঁজছি... 🔍"

Step 4 — Additional rules:
  • Never reveal internal field names (is_sc, annual_income, project_cost, etc.)
  • When asking about income: normalize language — don't say "annual income in rupees", say
    "ghar ki saalaana kamaai" / "ek saal mein parivar ki kitni amdani hai"
  • When asking about project cost: say "loan kitna chahiye" or "kaam ke liye kitna paise lagega"
    not "what is your project_cost"
  • If the user seems confused or gives an incomplete answer, gently clarify what you understood
    and ask again in simpler terms
  • If the user says something completely unrelated to the loan/scheme, acknowledge it briefly
    and steer back to the missing field naturally, in 1-2 sentences

EXAMPLE EXCHANGES (to calibrate tone):
  User: "mujhe 3 lakh chahiye shop ke liye"
  Reply: "Theek hai ji! Kya aap SC (Scheduled Caste) category mein aate hain?"

  User: "haan SC hun, income 2 lakh hai"
  Reply: "Samajh gaya — SC hain aur income 2 lakh. Aapko is dukan ke liye kitna loan chahiye?"

  User: "நான் SC தான், கடைக்காக 5 லட்சம் வேண்டும்"
  Reply: "சரி! உங்கள் வார்ஷிக வருமானம் எவ்வளவு?"

  User: "ami SC, dorjir dokan er jonno 2 lakh chai, income 1.5 lakh"
  Reply: "Bujhte parlam! Sab kichu thik ache — ekhon aapnar jonno scheme khunjchi... 🔍"

══════════════════════════════════════════════════
OUTPUT FORMAT — always exactly this JSON shape:
══════════════════════════════════════════════════
{
  "purpose":        "business" | "education" | "skill" | null,
  "is_sc":          true | false | null,
  "annual_income":  number | null,
  "project_cost":   number | null,
  "project_type":   string | null,
  "course_fee":     number | null,
  "study_location": "India" | "Abroad" | null,
  "reply":          string
}
"""


REQUIRED_FIELDS = ["purpose", "is_sc", "annual_income", "project_cost"]

CSV_DIR = os.path.dirname(__file__)
schemes_df = pd.read_csv(os.path.join(CSV_DIR, "schemes.csv"))
documents_df = pd.read_csv(os.path.join(CSV_DIR, "documents.csv"))
partners_df  = pd.read_csv(os.path.join(CSV_DIR, "partners.csv"))


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

    # All extractable fields — used to initialise and sanitise known_fields.
    ALL_FIELDS = ["purpose", "is_sc", "annual_income", "project_cost",
                  "project_type", "course_fee", "study_location"]

    # known_fields: whatever the frontend passes back from previous turns.
    # If the key is absent (first turn), default every field to null.
    raw_known = data.get("known_fields") or {}
    known = {f: raw_known.get(f) for f in ALL_FIELDS}

    # Build the content block sent to Gemini.
    # We prepend a structured context block so Gemini knows what's already confirmed
    # and doesn't ask about it again.
    known_json = json.dumps(known, ensure_ascii=False, indent=2)
    gemini_content = (
        f"KNOWN FIELDS (already collected in this conversation):\n{known_json}\n\n"
        f"USER MESSAGE:\n{text}"
    )

    try:
        response = _gemini_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=gemini_content,
            config=types.GenerateContentConfig(
                system_instruction=GEMINI_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.7,
                top_p=0.95,
            ),
        )
        extracted = json.loads(response.text)
    except Exception as exc:
        return jsonify({"error": f"Gemini API call failed: {exc}"}), 503

    # Merge: for each field, prefer the newly extracted value if non-null,
    # otherwise keep the previously known value.
    merged = {}
    for f in ALL_FIELDS:
        new_val = extracted.get(f)
        merged[f] = new_val if new_val is not None else known.get(f)

    # Pull out the reply Gemini wrote (it's not a data field — keep it separate).
    reply = extracted.get("reply", "")

    missing = [f for f in REQUIRED_FIELDS if merged.get(f) is None]

    return jsonify({**merged, "missing_fields": missing, "reply": reply})


def haversine_km(lat1, lon1, lat2, lon2):
    """Straight-line distance between two (lat, lon) points in kilometres."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi  = math.radians(lat2 - lat1)
    dlam  = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


@app.route("/api/partners", methods=["POST"])
def get_partners():
    """
    Expects JSON like:
        {"scheme_id": 2}                               # distance unknown
        {"scheme_id": 2, "latitude": 28.6, "longitude": 77.2}  # distance computed

    Returns:
        {"partners": [...], "count": N}

    Partners are filtered to those whose scheme_ids column contains the
    requested scheme_id. Results are sorted: nearest-first (if coordinates
    provided), then null-distance partners in CSV order.
    """
    data = request.get_json(force=True, silent=True) or {}

    scheme_id = data.get("scheme_id")
    if scheme_id is None:
        return jsonify({"error": "Missing required field: scheme_id"}), 400

    scheme_id = int(scheme_id)
    user_lat  = data.get("latitude")
    user_lon  = data.get("longitude")
    user_has_coords = user_lat is not None and user_lon is not None

    results_with_dist    = []
    results_without_dist = []

    for _, row in partners_df.iterrows():
        # scheme_ids is semicolon-separated e.g. "1;3;7"
        ids = [int(x.strip()) for x in str(row["scheme_ids"]).split(";") if x.strip()]
        if scheme_id not in ids:
            continue

        # Compute distance_km only when both sides have coordinates
        partner_lat = row["latitude"]  if pd.notna(row["latitude"])  else None
        partner_lon = row["longitude"] if pd.notna(row["longitude"]) else None
        partner_has_coords = partner_lat is not None and partner_lon is not None

        if user_has_coords and partner_has_coords:
            dist_km = round(haversine_km(user_lat, user_lon, partner_lat, partner_lon), 2)
        else:
            dist_km = None

        entry = {
            "partner_name":            row["partner_name"],
            "partner_type":            row["partner_type"],
            "address":                 row["address"]  if pd.notna(row["address"])  else None,
            "state":                   row["state"]    if pd.notna(row["state"])    else None,
            "district":                row["district"] if pd.notna(row["district"]) else None,
            "website":                 row["website"]  if pd.notna(row["website"])  else None,
            "fund_utilization_status": row["fund_utilization_status"] if pd.notna(row["fund_utilization_status"]) else None,
            "distance_km":             dist_km,
        }

        if dist_km is not None:
            results_with_dist.append(entry)
        else:
            results_without_dist.append(entry)

    # Nearest first, then unknown-distance partners in CSV order
    results_with_dist.sort(key=lambda e: e["distance_km"])
    partners = results_with_dist + results_without_dist

    return jsonify({"partners": partners, "count": len(partners)})


if __name__ == "__main__":
    app.run(debug=False, port=5000, threaded=True)
