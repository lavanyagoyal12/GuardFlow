# GuardFlow Backend

FastAPI backend for Android event ingestion, browser-extension page analysis,
and deterministic fraud-risk scoring.

## Active flow

1. Android posts events to `POST /api/v1/events`.
2. URL events are dispatched to the browser extension over `/ws` as
   `ANALYZE_URL`.
3. The extension returns its unchanged `PAGE_ANALYSIS` structured JSON.
4. The backend stores the full JSON in `Event.payload`.
5. `POST /api/v1/score/{session_id}` selects the latest page analysis, sends a
   compact evidence subset to local Qwen through Qualcomm GenieX, and combines
   validated semantic flags with URL, content, behaviour, and transaction data.
6. `risk_engine.py` alone converts evidence into fixed points and calculates
   the explainable final score. If GenieX is disabled or unavailable, the
   existing deterministic scoring path continues normally.

## Services

```text
app/services/
├── event_processor.py     # event persistence
├── feature_extractor.py   # normalize extension JSON + Android events
├── website_analyzer.py    # deterministic observations + compact LLM evidence
├── risk_engine.py         # only scoring authority
└── llm_service.py         # local GenieX/Qwen semantic adapter
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
