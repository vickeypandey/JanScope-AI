# Folder explanation

```text
JanScope-AI/
├── app/                  FastAPI backend
│   ├── api/              HTTP routes only
│   ├── core/             Settings, logging, safety
│   ├── db/               SQLAlchemy engine, tables, seed loader
│   ├── repositories/     Database queries and mapping
│   ├── schemas/          Pydantic request/response DTOs
│   ├── services/         Profile, retrieval, rules, AI, graph, grievance
│   └── main.py           FastAPI startup and middleware
├── frontend/             Complete Streamlit UI
├── data/                 Curated JSON; runtime DB/vector files are ignored
├── sample_documents/     Human-readable scheme summaries
├── scripts/              Database/index initialization commands
├── tests/                Unit and end-to-end API tests
├── postman/              Importable API request collection
├── .streamlit/           UI theme configuration
├── .env.example          Safe configuration template
├── requirements.txt      Complete Python dependencies
├── setup.bat             Windows automatic installation
├── run_all.bat           Starts backend and frontend
└── docker-compose.yml    Containerized full application
```

## Backend package responsibility

| File | Responsibility |
|---|---|
| `app/main.py` | Application startup, CORS, logging middleware, routes |
| `core/config.py` | Reads `.env` into typed settings |
| `core/safety.py` | Input cleaning and prompt-injection flags |
| `db/models.py` | SQLite table definitions |
| `db/seed.py` | Loads `data/schemes.json` idempotently |
| `repositories/scheme_repository.py` | Scheme and document database operations |
| `repositories/conversation_repository.py` | Local conversation persistence |
| `services/profile_service.py` | Explicit profile extraction |
| `services/intent_service.py` | Request classification |
| `services/retrieval_service.py` | Chunking, embeddings, Chroma and ranking |
| `services/eligibility_service.py` | Deterministic rule evaluation |
| `services/llm_service.py` | Isolated Gemini provider integration |
| `services/workflow_service.py` | LangGraph nodes, routing and grounded response |
| `services/grievance_service.py` | English/Hindi reviewable grievance drafts |
| `services/container.py` | Creates and connects service objects |
| `api/routes.py` | Converts HTTP requests into service calls |

## Where to make common changes

| Goal | Edit |
|---|---|
| Add a sample scheme | `data/schemes.json` then run `scripts/ingest_documents.py` |
| Add profile attribute | schema, DB profile JSON usage, profile and eligibility services |
| Change ranking | `RetrievalService.search` |
| Add graph route | `WorkflowService._invoke_graph` and route function |
| Change frontend design | `frontend/streamlit_app.py` CSS and page function |
| Change AI provider | implement behind `LLMService` |
| Change database | `DATABASE_URL` and verify SQLAlchemy compatibility |
