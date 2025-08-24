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

   Update `services/ai_orchestration_service/.env` with real values for `LLM_PROVIDER`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, and `LOCAL_LLM_URL`.

2. Start the containers:

   ```bash
   docker-compose up --build
   ```
