# InvoiceRadar

A small local Streamlit prototype. AI extracts invoice fields and recommends
NORMAL or INSPECT. Only a human button click approves or denies an invoice.
Confidence refers to extraction and assessment, never payment authorization.

## Run

From the project workspace:

```sh
cd invoice-triage
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

No API key is needed: the ten included invoices have realistic cached mock
assessments, clearly labeled in the dashboard. New or edited text without a key
requires manual inspection rather than invented extraction.

For live AI, copy `.env.example` to `.env` and set `OPENAI_API_KEY`. Restart
Streamlit. The app automatically replaces sample mock caches with live results.
`OPENAI_MODEL` defaults to `gpt-4o-mini` and can be changed in `.env`.
The live call uses the OpenAI SDK's Responses API with a strict JSON schema;
see the [official structured outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs).
Invoice text is sent to OpenAI only when a key is configured and an assessment
is needed. API failures are labeled, cached, and recommend INSPECT. To retry a
failed call, remove that invoice's JSON sidecar and rerun the app.

## Demo

1. The full sample set has two routine invoices marked NORMAL and eight marked
   INSPECT. The suspicious unsolicited email sorts first in Pending and has 7%
   mock confidence because its key invoice fields cannot be reliably extracted.
2. Inspect the bank change or forwarded email to see raw text, reasons, missing
   information, and the question for a human.
3. Click Approve or Deny. The text and JSON sidecar move together and appear in
   the corresponding tab. Approval only records your decision; it sends no payment.
   Deny opens a popup requiring a reason; Cancel leaves the invoice pending.
   Decisions save reviewer Ravee in the sidecar, and archive tables show the
   reviewer plus denial reasons. Earlier demo decisions display Ravee with no
   invented denial reason.
4. Add other `.txt` invoices to `invoices/pending/`. An optional `Source:` line
   supplies the source label. This prototype expects USD amounts.

State is just files; no database. To reset the demo, move the sample `.txt` and
`.json` pairs from Approved/Denied back to Pending while the app is stopped.
Cache hashes invalidate assessments when the text changes. The app does not
check external payment history or vendor records; duplicate concerns come from
the supplied text. Use one local app session for the demo.

The top profile menu uses a picture placeholder and the name Raveendra hegde.
It starts signed in for the demo; Log out shows a mock login screen. This is a
UI demo, not authentication or access control.
