# In services/ai_orchestration_service/app/services/llm_service.py

"""Service for interacting with various LLM providers."""
"""Service for interacting with various LLM providers."""
import logging
from typing import List
import json
import httpx

from core.config import settings
from schemas.interview import ConversationTurn, InterviewContext

# Configure basic logging
logging.basicConfig(level=logging.INFO)

async def generate_next_question(
    context: InterviewContext, history: List[ConversationTurn]
) -> str:
    """Generate the next interview question using the configured LLM."""

    system_prompt = (
        "You are an AI technical interviewer. "
        f"The job description is: {context.job_description}. "
        "Ask the candidate the next question based on the conversation so far."
    )

    provider = "local" # settings.llm_provider.lower()

    if provider == "local":
        messages = [{"role": "system", "content": system_prompt}]
        for turn in history:
            role = "user" if turn.role == "candidate" else "assistant"
            messages.append({"role": role, "content": turn.message})

        payload = {
            "model": "google/gemma-3-1b",
            "messages": messages,
            "stream": False
        }
        
        # --- Logging the Raw Request Details ---
        url =  "https://248e110186a5.ngrok-free.app/v1/chat/completions"# settings.local_llm_url
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        body = json.dumps(payload, indent=2)

        logging.info("--- Preparing to send request ---")
        logging.info(f"METHOD: POST")
        logging.info(f"URL: {url}")
        logging.info(f"HEADERS:\n{json.dumps(headers, indent=2)}")
        logging.info(f"BODY:\n{body}")
        logging.info("---------------------------------")
        # ----------------------------------------
        
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
                # Using the manually prepared headers and content
                response = await client.post(url, headers=headers, content=body)
                response.raise_for_status()
                data = response.json()
            
            return data["choices"][0]["message"]["content"].strip()
        except httpx.ConnectError as e:
            logging.error(f"CONNECTION FAILED: Could not connect to {url}. Please ensure the server is running, accessible from Docker, and not blocked by a firewall.")
            raise e # Re-raise the exception after logging
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            raise e


    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
