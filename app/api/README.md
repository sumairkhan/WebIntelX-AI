# API Notes

## Ingestion endpoint

The browser SDK sends event batches to `POST /api/ingest/events`.

Request shape:

```json
{
  "credential": "wix_ing_example",
  "events": [
    {
      "event_id": "uuid",
      "timestamp": "2026-10-03T12:00:00Z",
      "event_type": "page_view",
      "source": "browser_sdk",
      "session_id": "session-123",
      "page_url": "https://example.com/products",
      "page_path": "/products",
      "referrer": "",
      "user_agent": "Mozilla/5.0",
      "screen_width": 1920,
      "screen_height": 1080,
      "language": "en-US"
    }
  ]
}
```

The server verifies the credential, resolves the associated website server-side, validates the event shape, and stores only safe browser metadata in the `metadata` JSON field.

## Security notes

- The raw credential is never logged or returned in responses.
- The request body is the only allowed place for the ingestion credential.
- The website is resolved from the credential, never from untrusted client input.
- Sensitive browser data such as passwords, cookies, authorization values, and form submissions are rejected or ignored.

## CORS

The portal CORS allowlist is controlled by `CORS_ALLOWED_ORIGINS`. Local defaults cover the Next.js portal and Streamlit. Set the exact deployed portal origin in the backend environment for production; do not use `*`.

The browser SDK posts only to `POST /api/ingest/events`. Its preflight origin and each browser ingestion request must match the exact HTTP(S) origin registered for the website associated with that credential, including the port when present. For example, `http://localhost:5500` and `http://localhost:5501` are distinct origins. Deactivating a website revokes its active ingestion keys and disables this origin allowance.

Authenticated `GET /api/websites/{website_id}/telemetry` reports connection status only when the website is active, it has an active credential, and recent telemetry was ingested with that currently active credential. Historical events from a rotated key do not verify the new connection.

The existing SDK is served at `/sdk/webintelx.js`. Frontend values `NEXT_PUBLIC_WEBINTELX_SDK_URL` and `NEXT_PUBLIC_INGESTION_ENDPOINT` may override the local defaults. These URLs are public configuration; ingestion credentials remain limited-scope browser values and must never be replaced with backend secrets.

## LLM provider

CrewAI uses the server-side `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_TEMPERATURE`, and `LLM_MAX_TOKENS` settings. For Groq, set those values in the backend environment only. Keep `.env` out of source control; `LLM_API_KEY` is never returned by health, auth, or frontend APIs.

## Rate limiting

A lightweight in-memory rate limiter protects the endpoint for local MVP usage. It is not a distributed production-grade protection mechanism.
