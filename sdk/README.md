# WebIntelX JavaScript SDK

The WebIntelX JavaScript SDK provides a lightweight browser-side telemetry foundation for future backend ingestion. The current milestone focuses on configuration validation, session tracking, page-view telemetry, custom event creation, batching, and safe browser behavior.

## Installation

Add the SDK to a website with a script tag:

```html
<script src="./webintelx.js"></script>
<script>
  WebIntelX.init({
    credential: "wix_ing_<generated-value>",
    endpoint: "https://your-webintelx-server/api/ingest/events",
    enabled: true,
    autoTrack: true
  });
</script>
```

> Use a placeholder credential value in examples. Do not expose a real ingestion credential in documentation or source control.

## Features

- validates required configuration before tracking begins
- creates and reuses a browser session identifier
- records page view events automatically when `autoTrack` is enabled
- supports SPA navigation detection with `pushState`, `replaceState`, and `popstate`
- supports custom event tracking through `WebIntelX.track(eventType, data)`
- batches queued events and flushes them with `fetch()`
- exposes safe status metadata without exposing the credential
- avoids capturing sensitive browser data such as passwords, cookies, localStorage contents, or authorization headers

## API

```js
WebIntelX.init({
  credential: "wix_ing_<generated-value>",
  endpoint: "http://127.0.0.1:8000/api/ingest/events",
  enabled: true,
  autoTrack: true
});

WebIntelX.track("button_click", { button: "checkout" });
WebIntelX.flush();
WebIntelX.getSessionId();
WebIntelX.getStatus();
```

## Local Development

The FastAPI backend serves this SDK source at `http://127.0.0.1:8000/sdk/webintelx.js` and accepts telemetry at `http://127.0.0.1:8000/api/ingest/events`. The integration wizard generates these values from the frontend environment configuration. Register the customer site's exact HTTP(S) origin in the portal first; development origins such as `http://localhost:5500` retain their port and use HTTP, while production sites normally use HTTPS. CORS and ingestion both enforce the registered origin against the credential's website.

## Security Notes

- The SDK only contains a limited-scope ingestion identifier.
- It does not include JWTs, database credentials, or backend application secrets.
- It avoids collecting sensitive browser data and never stores credentials in `localStorage` or `sessionStorage`.
