# Reverse-engineering learning map

Use the repository as a reference implementation. For every topic, first build the tiny exercise yourself, then trace JanScope.

| Topic | Tiny exercise | JanScope files | Modification proving ownership |
|---|---|---|---|
| Python functions/classes | Student class and calculator | Any service class | Add type hints and one tested helper |
| FastAPI | One `/hello` and one POST endpoint | `api/routes.py`, `main.py` | Add a harmless statistics endpoint |
| Pydantic | Validate a student JSON object | `schemas/models.py` | Add a validated optional profile field |
| SQLAlchemy/SQLite | CRUD for one `Student` table | `db/`, `repositories/` | Add and query one new table field |
| NLP extraction | Regex age/state extractor | `profile_service.py` | Add two Hindi aliases and tests |
| Classification | Keyword intent classifier | `intent_service.py` | Add a new intent test case |
| Embeddings | Hash five sentences and compare cosine | `HashingEmbedder` | Change dimensions and measure retrieval |
| Vector database | Store/query five vectors | `retrieval_service.py` | Reindex after adding a document |
| RAG | Retrieve text then template answer | retrieval + workflow | Add abstention for a zero-score query |
| Eligibility engine | Three if-statements with reasons | `eligibility_service.py` | Encode and test one official rule |
| Gemini API | One prompt from a local script | `llm_service.py` | Change model only through `.env` |
| LangChain | Split one long document | `_split_text` | Tune chunk size and test count |
| LangGraph | Three-node conditional graph | `workflow_service.py` | Add one node and workflow trace step |
| Memory | Save messages in SQLite | conversation repository | Add a conversation summary field update |
| Security | Reject one malicious string | `core/safety.py` | Add pattern and corresponding test |
| Testing | Test a pure function | `tests/` | Fix a deliberately failing assertion |
| Streamlit | Input, button and result card | `frontend/streamlit_app.py` | Add one filter or profile component |
| Docker | Containerize a hello API | Docker files | Explain service networking and volume |

## Interview self-check

You are ready to present the project only when you can answer:

1. Why is eligibility deterministic?
2. How does a question become an embedding?
3. Why combine vector and keyword signals?
4. What is stored in LangGraph state?
5. What happens when Gemini is unavailable?
6. How are sources connected to an answer?
7. Why is a 90% match score not a government eligibility probability?
8. How does conversation memory avoid sending unlimited history?
9. Which data should never appear in logs?
10. What must change before government production use?
