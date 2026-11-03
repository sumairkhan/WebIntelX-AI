## Project
WebIntelX AI

## Description
WebIntelX AI is a web security intelligence and investigation platform designed to help security teams monitor, investigate, and respond to digital threats across web assets and related telemetry.

## Current Milestone
Milestone 1 — Project Foundation

## Requirements
- Python 3.11+
- VS Code
- Git

## Setup
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Run Backend
```powershell
uvicorn app.main:app --reload --port 8000
```

## Run Dashboard
```powershell
streamlit run dashboard/streamlit_app.py
```

## API
[http://127.0.0.1:8000](http://127.0.0.1:8000/)

## Swagger
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Dashboard
[http://localhost:8501](http://localhost:8501/)

## Tests
```powershell
pytest -q
```

## Milestone 2 — Database Foundation
- SQLite database with SQLAlchemy 2.x
- Database initialization and table creation at application startup
- Database location: WebIntelXAI.db in the project root
- Core tables include users, websites, ingestion credentials, events, findings, incidents, correlations, and feedback
- Authentication, website APIs, and telemetry flows are intentionally not implemented yet

Run the database test suite with:
```powershell
python -m pytest -q
```

## Authentication
Milestone 3 adds a basic secure authentication foundation for user registration, login, JWT issuance, and protected user access.

### Register a user
```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/register" `
  -ContentType "application/json" `
  -Body '{"email":"test@example.com","password":"password123"}'
```

### Login and receive a JWT
```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/login" `
  -ContentType "application/json" `
  -Body '{"email":"test@example.com","password":"password123"}'
```

### Use the token on a protected route
```powershell
$token = (Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/auth/login" `
  -ContentType "application/json" `
  -Body '{"email":"test@example.com","password":"password123"}').access_token

Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/api/auth/me" `
  -Headers @{ Authorization = "Bearer $token" }
```

JWTs are signed using the configured `JWT_SECRET_KEY`, validated against the configured algorithm, and the backend loads the current user from the database using the token subject. The authentication system is intentionally limited to user identity and protection of authenticated routes for this milestone; later milestones will build authorization rules around this identity foundation.

## Ingestion Credentials

WebIntelX ingestion credentials are website-scoped identifiers used for future browser SDK telemetry ingestion. They are not user passwords, JWTs, admin keys, or application secrets. Each credential belongs to one website and is protected by the same authenticated-user ownership model used elsewhere in the platform.

- The raw credential is generated with a secure random value and returned only during creation or rotation.
- The database stores only a SHA-256 hash of the credential.
- A website may have only one active credential at a time; older active credentials are revoked and retained as history.
- Credential status values are limited to `active` and `revoked`.
- The credential is intended for browser SDK ingestion flows and is not a high-privilege backend secret.

### Create a credential
```powershell
$token = (Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/auth/login" -ContentType "application/json" -Body '{"email":"test@example.com","password":"password123"}').access_token

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/websites/1/credentials" `
  -Headers @{ Authorization = "Bearer $token" }
```

### Rotate a credential
```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/websites/1/credentials/1/rotate" `
  -Headers @{ Authorization = "Bearer $token" }
```

### Revoke a credential
```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/websites/1/credentials/1/revoke" `
  -Headers @{ Authorization = "Bearer $token" }
```

Example values are shown as `wix_ing_<generated-value>` placeholders and never include a real credential value.

## JavaScript SDK

The WebIntelX browser SDK is a lightweight, vanilla JavaScript client for website telemetry ingestion. It is designed to be installed on customer websites, validate its configuration, create browser-session context, automatically track page views, and batch safe event payloads without exposing high-privilege backend secrets.

- The SDK uses only the website-scoped ingestion credential, not JWTs or server-side secrets.
- It validates required settings before tracking begins.
- It creates a browser session identifier and tracks page-view events with safe metadata only.
- It supports custom events and a small, bounded queue with periodic flushes.
- The backend ingestion endpoint is implemented as `POST /api/ingest/events` and checks the credential server-side before storing event records.

### Example initialization
```html
<script src="./sdk/src/webintelx.js"></script>
<script>
  WebIntelX.init({
    credential: "wix_ing_<generated-value>",
    endpoint: "http://127.0.0.1:8000/api/ingest/events",
    enabled: true,
    autoTrack: true
  });
</script>
```

The demo page is available under `sdk/examples/demo.html` for local testing against the backend ingestion endpoint.

## Milestone 7 — Event Ingestion

The backend now accepts browser SDK event batches at `POST /api/ingest/events`.

- The request body must include a valid website-scoped credential and at least one valid event.
- The server resolves the associated website from the credential instead of trusting browser-supplied website IDs.
- Duplicate `event_id` values are not inserted again; they are counted as duplicates.
- Only safe browser metadata is stored in the `Event.metadata` JSON field.
- CORS is enabled for local development origins and the endpoint uses a lightweight in-memory rate limiter.

### Example ingestion request
```json
{
  "credential": "wix_ing_example",
  "events": [
    {
      "event_id": "event-123",
      "timestamp": "2026-10-03T12:00:00Z",
      "event_type": "page_view",
      "source": "browser_sdk",
      "session_id": "session-abc",
      "page_url": "https://example.com/products",
      "page_path": "/products",
      "referrer": "https://example.com/",
      "user_agent": "Mozilla/5.0",
      "screen_width": 1920,
      "screen_height": 1080,
      "language": "en-US"
    }
  ]
}
```

### Example ingestion response
```json
{
  "success": true,
  "accepted": 1,
  "duplicates": 0,
  "rejected": 0
}
```

## Milestone 9 — Deterministic Detection

The rule-based detection layer remains separate from the ML layer. M9 produces deterministic findings such as `suspicious_path` and `suspicious_user_agent` through configured rule checks against processed events.

## Milestone 10 — ML Anomaly Detection

Milestone 10 adds a separate anomaly signal based on scikit-learn Isolation Forest.

- Model type: `sklearn.ensemble.IsolationForest`
- Training scope: per website only
- Training requirement: minimum configured value (default 20 processed events)
- Feature version: `v1`
- Model version: `v1`
- Output: normalized anomaly score in the range `0.0` to `1.0`
- Safety: raw URLs and sensitive query values are not passed into the model; only numeric feature values derived from the processed event are used
- Persistence: model artifacts are stored under the `data/models/` directory and metadata is written alongside the model file
- Findings: ML anomalies create findings with `agent_name = "ml_anomaly_detector"` and `finding_type = "ml_anomaly"`
- Distinction: anomaly detection identifies unusual behavior patterns. It does not prove that a user or request is malicious.

### Training endpoint
```powershell
$token = (Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/auth/login" -ContentType "application/json" -Body '{"email":"test@example.com","password":"password123"}').access_token

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/websites/1/ml/train" `
  -Headers @{ Authorization = "Bearer $token" }
```

A trained model is optional and does not replace the M9 deterministic rules. M9 findings remain independent until later correlation milestones.

## Milestone 12 — CrewAI Investigation

Milestone 12 adds a bounded investigation layer that consumes the evidence already produced by M7–M11 without replacing those earlier stages. The investigation system only explains and structures evidence; it does not create incidents, calculate risk, or perform automated blocking.

### Scope boundaries
- Allowed: evidence analysis, behavior analysis, timeline synthesis, fact vs inference separation, investigation persistence, safe API exposure.
- Not allowed: threat intelligence, attack graphing, risk scoring, incident creation, response actions, autonomous blocking, web searches, external reputation lookups.

### Configuration
The investigation layer is disabled by default.

```env
CREWAI_ENABLED=false
LLM_PROVIDER=
LLM_MODEL=
LLM_API_KEY=
LLM_BASE_URL=
LLM_TEMPERATURE=0
LLM_MAX_TOKENS=2000
INVESTIGATION_MAX_EVENTS=100
INVESTIGATION_MAX_FINDINGS=50
INVESTIGATION_MAX_CORRELATIONS=50
```

When `CREWAI_ENABLED` is disabled or no LLM provider configuration is present, the system falls back to a deterministic local investigation result instead of crashing or requiring a real LLM call.

### API
```powershell
$token = (Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/auth/login" -ContentType "application/json" -Body '{"email":"test@example.com","password":"password123"}').access_token

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/websites/1/investigations" `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json" `
  -Body '{"correlation_id":1}'
```

The endpoint returns a structured result with `summary`, `facts`, `inferences`, `uncertainties`, and `confidence`. Facts are restricted to event/finding/correlation-backed evidence; inferences are clearly labeled as agent interpretations and never presented as confirmed facts.

### Investigation lifecycle
- `pending`
- `running`
- `completed`
- `failed`

The database keeps the investigation record even when the engine is unavailable or the structured output is rejected, and it stores only the sanitized evidence that is relevant to the website and correlation under review.
