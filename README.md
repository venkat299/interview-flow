# Smart Screener AI

## 1. Project Objective

The goal of this project is to develop an AI-powered technical screening platform that automates initial interviews. The system provides a dynamic, chat-based experience for candidates, asking intelligent, context-aware follow-up questions based on the job description and the candidate's live answers. This aims to provide a deeper, more accurate signal of a candidate's abilities than traditional coding tests.

## 2. Technical Approach

The platform is built on a modern, scalable backend using a **microservices architecture**.

* **Language & Framework**: The entire backend is built with **Python** and **FastAPI**, chosen for its high performance and asynchronous capabilities.
* **AI Engine**: The core intelligence is provided by an **`AI Orchestration Service`** that uses a large language model (LLM) to generate questions on the fly. It engineers prompts based on the job description and conversation history to ensure questions are relevant and insightful.
* **Real-Time Interaction**: The **AI Orchestration Service** also manages the candidate experience. It exposes **WebSocket** endpoints to run live interviews and persists transcripts in SQLite.
* **Persistence**: When an interview ends, the service persists the full conversation transcript (as JSON) together with the session metadata and final rubric in a local SQLite DB (`services/ai_orchestration_service/session_service/interview_sessions.db`).
* **Development & Deployment**: The services are containerized using **Docker** and orchestrated for local development with **Docker Compose**, ensuring a consistent and reproducible environment.

## 3. Local Development

Run the service with Docker Compose:

1. Copy the example environment file and provide your own credentials:

   ```bash
   cp services/ai_orchestration_service/.env.example services/ai_orchestration_service/.env
   ```

   Update `services/ai_orchestration_service/.env` with real values for `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `GEMINI_API_KEY`, and `LOCAL_LLM_URL`.

   When using an LLM running on your host machine (e.g., LM Studio), set
   `LLM_PROVIDER=local` and point `LOCAL_LLM_URL` to the host using
   `host.docker.internal`. For example:

   ```bash
   LOCAL_LLM_URL=http://host.docker.internal:1234/v1/chat/completions
   ```

2. Start the container:

   ```bash
docker-compose up --build
   ```

### Direct service calls

The WebSocket session management is now embedded in the orchestration service
and calls orchestration functions in‑process for lower latency.


## 4. Test Frontend & End-to-End Testing

Once the backend service is running, you can drive a sample interview using the lightweight test frontend located in `test_frontend/`.

1. Start the services if they are not already running:

   ```bash
   docker-compose up --build
   ```

2. In a new terminal, serve the static files:

   ```bash
   python -m http.server --directory test_frontend 3000
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your browser. The page connects to the service and lets you exchange messages with the AI interviewer.


## 5. WebSocket & Session Retrieval

The Orchestration Service exposes WebSocket and read endpoints:

- WebSocket: `ws://localhost:8003/api/v1/ws/{session_id}`
- `GET http://localhost:8003/api/v1/sessions` — list sessions with start/end times.
- `GET http://localhost:8003/api/v1/sessions/{session_id}` — fetch a session with parsed `blueprint`, `rubric`, `transcript`, and the per-turn `turns` log.

Adjust the base URL/port to match your deployment.
