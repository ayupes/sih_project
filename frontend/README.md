f# Frontend — Saarthi AI

## Two things live in this folder

1. **`fallback/index.html`** — already works, right now, zero setup.
   Open it in a browser (after starting the backend) and it calls the
   real API. This is your insurance policy — if the AI Studio frontend
   isn't ready in time, or breaks the night before, you still have a
   working demo.

2. Whatever Google AI Studio Build generates — this is your *real*
   frontend, the one you'll polish and actually demo with.

## Important: how to prompt AI Studio Build

By default, AI Studio's Build mode generates a **full-stack** app — its
own frontend *and* its own backend (Node.js, sometimes Firebase/Firestore
for data and auth). You don't want that. You already have a backend, in
Python, built separately by the backend team. Two backends that don't
know about each other is the #1 way this integration breaks.

So be explicit in your very first prompt. Something like:

> Build only a frontend web app — no backend, no database, no
> authentication, no Firebase. It's a form with three inputs: a Yes/No
> select for "Does the applicant belong to the Scheduled Caste
> community?", a number input for "Annual family income", and a number
> input for "Estimated project cost". A "Find schemes" button sends a
> POST request to http://127.0.0.1:5000/api/match with JSON body
> { is_sc: boolean, annual_income: number, project_cost: number }.
> The response looks like { eligible: boolean, message: string, schemes:
> [{ name, estimated_loan, applicant_contribution, interest_rate,
> repayment_years, source_url }] }. Show each matched scheme as a card
> with those fields. If eligible is false, show the message as a warning.
> Style it cleanly — this is for Scheduled Caste entrepreneurs in India,
> so keep the language simple and the layout uncluttered.

That prompt hands it the exact contract from `backend/README.md`, so
whatever it builds should plug straight into the real API.

## If it insists on generating its own backend anyway

That's fine — just don't use that part. Take only the generated
frontend code/component, drop the fetch call in pointing at
`http://127.0.0.1:5000/api/match`, and ignore whatever server files it
made. You don't have to use 100% of what a generator gives you.

## Before you demo

Change every `http://127.0.0.1:5000` in your frontend code to wherever
the backend is actually running at demo time (same value backend
README uses). This is the single most common last-minute bug — search
your frontend code for `5000` or `localhost` right before you present.
