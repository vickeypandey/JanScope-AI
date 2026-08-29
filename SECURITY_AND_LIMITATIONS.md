# Security, privacy and limitations

## Implemented controls

- `.env` and local databases are ignored by Git.
- Request models enforce types, lengths and numeric ranges.
- Common prompt-injection attempts are flagged before AI calls.
- Retrieved documents are labelled as evidence, not instructions.
- AI mode uses low temperature and strict source-only instructions.
- Eligibility is calculated by Python rules and remains provisional.
- Gemini failures fall back to deterministic output.
- Logs contain request IDs, route, status and duration—not full citizen messages or API keys.
- Grievances are drafts with placeholders for missing facts and mandatory review warnings.
- CORS defaults to local Streamlit origins.

## Known development-version limitations

- No production authentication or administrator authorization is included.
- The ingestion endpoint is open locally and must be protected before public deployment.
- SQLite is suitable for demonstration, not high concurrent load.
- The curated dataset is small and requires manual freshness review.
- Hashing embeddings are reproducible and lightweight but weaker than modern multilingual neural embeddings.
- Rule extraction covers common examples, not every Indian language or phrasing.
- Prompt-injection detection is defence-in-depth, not a complete security boundary.
- No official portal application or grievance submission occurs.
- There is no legal, accessibility, penetration-testing or government privacy certification.

## Before public deployment

Add authenticated users and administrator roles, rate limiting, HTTPS, secrets management, database migrations, audit logs, encrypted backups, consent and retention controls, monitored official-data updates, malware scanning for uploads, complete evaluation, adversarial testing and professional privacy/security review.
