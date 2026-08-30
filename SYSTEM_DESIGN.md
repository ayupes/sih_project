

## 1. The big picture, in plain words

Two separate programs, running at the same time, talking to each other:

- **Backend** = a Python program that sits and waits. When it's asked a
  question ("can this applicant get a loan?"), it does the math and
  replies with an answer, formatted as **JSON** (just text, structured
  like `{"name": "value"}` — both Python and JavaScript can read it).
  It has no buttons, no colors, nothing pretty. It's the brain.

- **Frontend** = the actual webpage a person clicks around on. It has
  no brain of its own — every time it needs an answer, it sends a
  message to the backend and waits for the reply, then displays it
  nicely. It's the face.

They talk over HTTP, the same protocol your browser uses to load any
website. Concretely: the frontend does `fetch("http://127.0.0.1:5000/api/match", ...)`,
the backend hears that, runs `match_schemes()`, sends JSON back.

That's the entire mental model. Everything below is detail.

```
   ┌─────────────┐        POST /api/match          ┌──────────────┐
   │  FRONTEND   │ ────── {income, cost, is_sc} ──▶ │   BACKEND    │
   │ (the page   │                                  │ (Flask, on   │
   │  a person   │ ◀──── {eligible, schemes[]} ──── │  port 5000)  │
   │  sees)      │        JSON response             │              │
   └─────────────┘                                  └──────────────┘
                                                             │
                                                       reads │
                                                             ▼
                                                      schemes.csv
```

## 2. Folder structure

You already have this shape — here's what goes in it:

```
sih_project/
├── backend/
│   ├── app.py              ← the Flask API (already written, already works)
│   ├── schemes.csv         ← the 4 schemes' numbers (already filled in)
│   ├── requirements.txt
│   └── README.md           ← setup + API contract + how to brief Antigravity
├── frontend/
│   ├── fallback/
│   │   └── index.html      ← a plain backup UI, already works, zero setup
│   └── README.md           ← how to prompt AI Studio Build safely
└── SYSTEM_DESIGN.md         ← this file
```

Everything in `backend/` and `frontend/fallback/` is real, tested code —
not a plan, an actual working prototype. Drop these files straight into
your existing repo folders. I ran it before giving it to you: sending
`{is_sc: true, annual_income: 320000, project_cost: 300000}` correctly
returns Term Loan and Udyam Nidhi Yojana with a ₹2,70,000 loan estimate
and ₹30,000 applicant contribution.

**Do this literally first, before touching Antigravity or AI Studio:**
run the backend (`backend/README.md` has the exact commands), then open
`frontend/fallback/index.html` in a browser and click "Find schemes."
If that works, you already have a demoable prototype. Everything from
here is improving on a working thing, not building from zero.

## 3. The API contract (the most important section)

This is the one thing that lets the backend pair and the frontend
people work at the same time without waiting on each other or getting
on a call to sync up. As long as both sides match this shape, they can
build independently and it'll click together at the end.

Full detail is in `backend/README.md`. The short version:

- Frontend sends: `{is_sc, annual_income, project_cost}`
- Backend replies: `{eligible, message, schemes: [...]}`

Anyone changing this shape must tell both teams immediately — this is
the one thing that isn't safe to change unilaterally.

## 4. Your tools, mapped to this design

**Antigravity (backend pair):** point it at the `backend/` folder. It
already contains a working `app.py`. Don't ask it to build a backend —
ask it to extend the one that's there, one small feature at a time (add
a field, add validation, add another endpoint). `backend/README.md` has
an example prompt and a note on picking "review-driven" mode so you can
see each change before it's applied, which matters for two reasons:
you'll be able to explain the code to judges, and you'll catch it if it
quietly changes something outside what you asked for.

**Google AI Studio (frontend):** its Build mode generates a full app
INCLUDING its own backend by default — that's the main risk here, since
you already have a backend and don't want a second one. `frontend/README.md`
has the exact prompt to use so it builds only the UI and calls your real
API instead of inventing its own.

**The CSV teammate:** send them `backend/schemes.csv` as the template.
They only need to edit the values (project cost ranges, interest rates,
max loan amounts) — the column names must stay exactly as they are,
since `app.py` reads them by name.

## 5. Two-day timeline

**Tomorrow (Day 1)**
- Morning: everyone installs Python + gets the repo pulled. Backend pair
  runs `backend/app.py` as-is and confirms `/api/health` responds — that
  alone proves your laptop setup works, before any real coding starts.
- Late morning: backend pair opens Antigravity, starts on real features
  (first ask it to explain the existing code back to you, so you both
  understand what you're extending — then make small additions).
- Afternoon: frontend team starts on AI Studio Build using the prompt in
  `frontend/README.md`. They don't need to wait for backend changes —
  the contract is already fixed, and the fallback page proves it works.
- End of day 1 goal: backend running with real CSV data from your
  teammate; frontend showing a UI (even if not yet wired to the real
  API). Fallback page still working as your safety net.

**Day 2**
- Morning: wire the real frontend to the real backend. Change every
  `127.0.0.1:5000` to match wherever the backend is actually running.
  This is where CORS/connection errors show up — see troubleshooting
  below.
- Midday: run 8-10 test cases through the real UI (see test cases
  below). Polish wording, add the disclaimer, handle the "not eligible"
  case gracefully.
- Afternoon: prep your demo using one consistent example applicant
  (income ₹3.2L, project cost ₹3L, SC = yes) so every run of the demo
  shows the same numbers and nobody gets a surprise on stage. Rehearse
  it twice.
- Evening: buffer. Something will break here. That's normal — it's why
  this slot exists.

## 6. Test cases worth running

- SC = yes, income 3,20,000, cost 3,00,000 → should show Term Loan and
  Udyam Nidhi Yojana, ~₹2.7L loan, ~₹30K contribution
- SC = yes, income 3,00,000, cost 1,00,000 → should show Micro Finance
  Scheme and Aajeevika Micro-Finance
- SC = yes, income 6,00,000, cost 3,00,000 → not eligible (income over
  limit)
- SC = no → not eligible regardless of other numbers
- cost = 0 or blank → shouldn't crash the page

## 7. Common errors and what they actually mean

- **"Failed to fetch" / network error in the browser console** — the
  backend isn't running, or it's running on a different port than the
  frontend is calling. Check the terminal running `app.py` is still
  open with no errors.
- **CORS error mentioning "Access-Control-Allow-Origin"** — normally
  this means the backend needs to allow the frontend's origin.
  `app.py` already has `CORS(app)` enabled for everything, so if you
  still see this, it usually means you're calling the wrong URL/port,
  not an actual CORS problem — double check the address first.
- **"Address already in use" when starting Flask** — something else is
  already using port 5000. On Mac this is often AirPlay Receiver; see
  `backend/README.md` for the fix.
- **Numbers look wrong (e.g. loan larger than project cost)** — check
  `schemes.csv` wasn't edited with a stray extra zero or a percentage
  typed as `90` vs `0.9` (it should be `90`, the code divides by 100).

## 8. What NOT to do with your two days

- Don't ask either AI tool to "build the whole SIH-winning app." Broad
  prompts produce bloated code nobody on the team can explain — and
  judges will ask you to explain it.
- Don't let AI Studio's generated backend and your Flask backend both
  end up in the mix. Pick one — the Flask one — and only take the UI
  code from AI Studio.
- Don't skip testing the backend alone before wiring up the frontend.
  If `/api/health` and a raw `/api/match` call work, any frontend bugs
  you hit afterward are frontend bugs, not mystery full-stack bugs.
