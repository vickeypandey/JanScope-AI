# Build verification

Verified on 25 August 2026 with Python 3.12.13.

## Completed checks

- Full dependency installation: passed
- SQLite initialization: passed
- Curated scheme seed: 8 records
- Chroma persistent index: 17 generated chunks before test-specific ingestion
- Python syntax compilation: passed
- JSON validation for scheme data and Postman collection: passed
- Ruff import/error lint checks: passed
- Automated tests: **15 passed**
- Backend live health check: HTTP 200
- Streamlit live health check: HTTP 200
- Live Hinglish chat smoke request: passed
- Workflow trace observed: receive → classify → profile → retrieval → eligibility → grounded answer
- PDF/TXT/Markdown ingestion path: implemented; Markdown multipart API covered by test
- Golden regression dataset: 25 cases executed

## Expected warning

The test environment emitted one upstream Starlette deprecation warning about its current TestClient HTTP transport. It does not fail a test or affect the application endpoints. Recheck it when upgrading FastAPI/Starlette.

## Not verified with a secret

Gemini mode was not called because no user API key was used or requested. The provider integration imports successfully through the installed official Google GenAI SDK, while all no-key paths were fully tested. After adding your own key locally, test one chat request and keep demo mode available as the fallback.
