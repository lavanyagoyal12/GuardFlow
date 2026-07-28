# GuardFlow Backend

FastAPI backend for Android event ingestion, browser-extension page analysis,
and deterministic fraud-risk scoring.

## Active flow

1. Android posts events to `POST /api/v1/events`.
2. URL events are dispatched to the browser extension over `/ws` as
   `ANALYZE_URL`.
3. The extension returns its unchanged `PAGE_ANALYSIS` structured JSON.
4. The backend stores the full JSON in `Event.payload`.
5. `POST /api/v1/score/{session_id}` selects the latest page analysis and
   calculates the deterministic score from URL, content, behaviour, and
   transaction data.
6. Local Qwen converts the calculated level and two or three strongest reasons
   into a short mobile explanation. The exact score and level still come only
   from `risk_engine.py`. If GenieX is unavailable, a deterministic explanation
   is returned instead.

## Services

```text
app/services/
├── event_processor.py     # event persistence
├── feature_extractor.py   # normalize extension JSON + Android events
├── website_analyzer.py    # deterministic observations + compact LLM evidence
├── risk_engine.py         # only scoring authority
└── llm_service.py         # local GenieX/Qwen semantic + explanation adapter
```

## Local Qwen setup on Snapdragon AI PC

```powershell
geniex pull Qwen/Qwen2.5-3B-Instruct-GGUF
# Select model type: llm, precision: Q4_0
geniex serve
```

Copy `.env.example` to `.env`. The backend calls the OpenAI-compatible GenieX
endpoint at `http://127.0.0.1:18181/v1/chat/completions`. Keep the GenieX
terminal open while GuardFlow is running.

The existing score response now fills its already-supported optional
`explanation` field. Android displays it in the current risk card and uses it
for LOW, MEDIUM, HIGH, and CRITICAL notifications. No additional mobile API
call is required.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

For macOS/Linux activation, use `source .venv/bin/activate`.

## Test

```bash
python -m unittest -v
```

The database schema, Android request/response contracts, existing REST paths,
and browser-extension WebSocket protocol are unchanged.
