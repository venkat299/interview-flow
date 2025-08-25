# Smart Screener AI

## 1. Project Objective

The goal of this project is to develop an AI-powered technical screening platform that automates initial interviews. The system provides a dynamic, chat-based experience for candidates, asking intelligent, context-aware follow-up questions based on the job description and the candidate's live answers. This aims to provide a deeper, more accurate signal of a candidate's abilities than traditional coding tests.

## 2. Technical Approach

The platform is built on a modern, scalable backend using a **microservices architecture**.

* **Language & Framework**: The entire backend is built with **Python** and **FastAPI**, chosen for its high performance and asynchronous capabilities.
* **AI Engine**: The core intelligence is provided by an **`AI Orchestration Service`** that uses a large language model (LLM) to generate questions on the fly. It engineers prompts based on the job description and conversation history to ensure questions are relevant and insightful.
* **Real-Time Interaction**: An **`Interview Session Service`** manages the candidate experience. It uses **WebSockets** to create a real-time, low-latency chat interface.
* **Development & Deployment**: The services are containerized using **Docker** and orchestrated for local development with **Docker Compose**, ensuring a consistent and reproducible environment.

## 3. Local Development

Run the services with Docker Compose:

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

2. Start the containers:

   ```bash
   docker-compose up --build
   ```

### Direct service calls

By default the Interview Session Service reaches the AI Orchestration Service over
HTTP. To call the orchestration logic directly without making HTTP requests, set
`AI_ORCHESTRATION_USE_DIRECT=true` in `services/interview_session_service/.env`.

This allows the services to invoke each other's methods in-process. If the
orchestration package is not available, the session service logs a warning and
falls back to HTTP.


## 4. Test Frontend & End-to-End Testing

Once the backend services are running, you can drive a sample interview using the lightweight test frontend located in `test_frontend/`.

1. Start the services if they are not already running:

   ```bash
   docker-compose up --build
   ```

2. In a new terminal, serve the static files:

   ```bash
   python -m http.server --directory test_frontend 3000
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your browser. The page connects to the WebSocket service and lets you exchange messages with the AI interviewer.

