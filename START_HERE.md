# Start JanScope AI on Windows

This guide assumes you are new to Python backends. Follow the steps in order.

## What you received

JanScope AI contains two applications:

1. **FastAPI backend** at `http://127.0.0.1:8000`
2. **Streamlit frontend** at `http://127.0.0.1:8501`

The backend stores data in local SQLite, performs deterministic eligibility checks, retrieves scheme documents, runs the LangGraph workflow, and optionally calls Gemini. The frontend calls those APIs and displays the result.

## Install only these things first

1. Python 3.13 or 3.12 from <https://www.python.org/downloads/>
2. VS Code from <https://code.visualstudio.com/>
3. VS Code Python extension
4. Git is recommended but not required to run the ZIP

During Python installation, enable **Add Python to PATH**.

Check it in Command Prompt:

```bat
py -3.13 --version
```

If you have Python 3.12 instead, use `py -3.12 --version`. The setup script automatically selects an installed supported version.

If the `py` launcher is not installed but `python --version` works, that is also supported. The setup script checks `py`, `python`, and `python3` automatically.

## Automatic setup

1. Extract `JanScope-AI.zip`.
2. Open the extracted `JanScope-AI` folder.
3. Double-click `setup.bat`.
4. Wait while it creates `.venv`, installs libraries, initializes SQLite, and builds the vector index.
5. When it reports success, double-click `run_all.bat`.
6. Two terminal windows will open: backend and frontend.
7. Open <http://127.0.0.1:8501>.

The first installation can take several minutes because Chroma, LangChain, LangGraph, Streamlit and their dependencies are downloaded.

## Test without spending money

The default `.env` contains:

```env
AI_ENABLED=false
```

This is **demo mode**. No API key or payment is required. The following still work:

- Complete frontend and backend
- SQLite database
- Profile extraction using rules
- English, common Hindi and Hinglish recognition
- Deterministic eligibility engine
- Hash-vector and keyword retrieval
- ChromaDB storage when installed
- LangGraph workflow
- Conversation history
- Source citations
- Grievance templates
- Automated tests

## Enable Gemini AI mode later

1. Create a key in Google AI Studio: <https://aistudio.google.com/app/apikey>
2. Open `.env` in VS Code.
3. Change only these values:

```env
AI_ENABLED=true
GEMINI_API_KEY=paste_your_key_here
```

4. Save the file.
5. Close and restart the backend terminal.

Never send the key in chat, commit `.env`, show it in screenshots, or write it inside Python code. API free-tier availability and limits can change, so check Google's current terms.

## Test APIs without the frontend

Start `run_backend.bat`, then open:

- Swagger: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/api/v1/health>

In Swagger, open `POST /api/v1/chat`, click **Try it out**, and send:

```json
{
  "message": "Mere pita ji 65 saal ke farmer hain, Bihar se. Kaunsi yojana mil sakti hai?",
  "language": "auto"
}
```

## Run automated tests

Double-click:

```text
run_tests.bat
```

Do this before every important GitHub commit.

## If full setup fails on a weak network

Run `setup-lite.bat`. It installs the essential API and frontend packages. JanScope automatically falls back to its in-memory workflow and retrieval implementations. Later, run `setup.bat` again to install the complete Chroma/LangChain/LangGraph stack.

## Common errors

### `py` is not recognized

Reinstall Python 3.13 or 3.12 and select **Add Python to PATH**, then reopen Command Prompt.

### Port 8000 is already in use

Close an older backend terminal. If necessary, find it in Command Prompt:

```bat
netstat -ano | findstr :8000
```

### Frontend says backend offline

Keep `run_backend.bat` running. Open <http://127.0.0.1:8000/api/v1/health>. If it does not return JSON, read the backend terminal's last error.

### Gemini returns an error

Return to demo mode:

```env
AI_ENABLED=false
```

Restart the backend. Then check the key, selected model, quota, and current Google AI Studio availability separately.

### Chroma does not install

Run `setup-lite.bat`. JanScope will use the built-in memory vector search, so the application remains testable.

## Safe first-day checklist

- [ ] Backend health endpoint returns `healthy`
- [ ] Streamlit home page opens
- [ ] Scheme explorer shows at least eight entries
- [ ] Chat returns schemes and sources
- [ ] Eligibility screen explains matched, failed and missing rules
- [ ] Grievance screen produces a draft with review warning
- [ ] `run_tests.bat` passes

After this, read `PROJECT_FLOW.md` and start tracing one API request.
