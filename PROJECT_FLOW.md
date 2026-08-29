# JanScope request flow in simple language

This file explains what happens after a user asks:

> Mere pita ji 65 saal ke farmer hain, Bihar se. Kaunsi yojana mil sakti hai?

## 1. Streamlit sends JSON

`frontend/streamlit_app.py` sends a request to:

```text
POST /api/v1/chat
```

The JSON contains the message, optional conversation ID, saved profile and language preference.

## 2. FastAPI validates it

`app/api/routes.py` receives the request. Pydantic validates it with `ChatRequest`. Empty or excessively large input is rejected before domain logic runs.

Java comparison:

```text
FastAPI route ≈ Spring Boot @RestController method
Pydantic model ≈ request DTO + validation annotations
Service container ≈ constructor-injected Spring services
SQLAlchemy repository ≈ Spring Data repository/service layer
```

## 3. Conversation memory is loaded

`ConversationRepository` reads the existing conversation from SQLite when a conversation ID is present. It merges only profile fields the user actually supplied. One user's profile is not guessed from another conversation.

## 4. Safety and intent classification run

`WorkflowService` starts a LangGraph state containing the message, profile, language and workflow trace.

The first node:

- checks common prompt-injection patterns;
- classifies the intent as scheme search, eligibility, application guidance, grievance, greeting or unsupported.

## 5. Citizen profile is extracted

`ProfileService` finds explicit attributes such as:

```json
{
  "age": 65,
  "state": "Bihar",
  "occupation": "farmer"
}
```

In demo mode, regex rules and curated aliases are used. In Gemini mode, the model may fill only still-empty fields, and it is instructed not to infer sensitive attributes.

## 6. LangGraph chooses the path

The graph uses a conditional edge:

- normal scheme question → retrieval;
- grievance request → explain required verified facts;
- greeting → greeting response;
- unsupported request → scope response;
- injection attempt → safe stop.

If LangGraph is not installed, `_manual_workflow` runs the same node order. This is why lightweight demo mode still works.

## 7. Hybrid retrieval finds evidence

`RetrievalService` converts the message into a hashing vector and queries Chroma. It also calculates keyword overlap and gives small bonuses for matching scheme names and states.

The final score combines:

```text
vector similarity + keyword overlap + scheme-name/state signals
```

Only the best chunk per scheme is kept so citations are diverse.

## 8. Eligibility rules run in ordinary Python

`EligibilityService` checks the profile against structured fields:

- state;
- minimum/maximum age;
- maximum income;
- occupation;
- gender/category when encoded;
- education when encoded.

It returns matched rules, failed rules and missing information. The LLM does not decide these conditions.

Example:

```json
{
  "status": "not_eligible",
  "matched_rules": ["Income requirement satisfied"],
  "failed_rules": ["Maximum entry age is 40"],
  "missing_information": []
}
```

## 9. Grounded answer is produced

In Gemini mode, only retrieved chunks, profile and deterministic results are placed in the prompt. The model is required to cite `[1]`, `[2]` and abstain when evidence is insufficient.

In demo mode, a deterministic template produces the answer from the same schemes, rule results and sources.

## 10. SQLite stores the exchange

The user message, assistant answer, intent, sources and updated limited profile are saved. API keys and unnecessary personal fields are not logged.

## 11. Streamlit renders all parts

The frontend shows:

- answer;
- extracted profile;
- recommended scheme cards;
- matched/failed/missing eligibility conditions;
- official source links;
- workflow trace;
- provisional-result disclaimer.

## Files to trace first

Read these in order:

1. `frontend/streamlit_app.py` → `page_chat`
2. `app/api/routes.py` → `chat`
3. `app/services/workflow_service.py` → `run`
4. `app/services/profile_service.py`
5. `app/services/retrieval_service.py`
6. `app/services/eligibility_service.py`
7. `app/repositories/conversation_repository.py`
