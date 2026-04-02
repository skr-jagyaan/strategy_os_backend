# worker_service/agent_manager.py
import os
import logging
import vertexai
from vertexai.generative_models import GenerativeModel
from anthropic import AnthropicVertex

from prompts import prompts

logger = logging.getLogger("worker.ai")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")

# Initialize Vertex AI for Gemini (Router)
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Initialize Anthropic Vertex SDK for Claude (Specialist)
claude_client = AnthropicVertex(project_id=PROJECT_ID, region=LOCATION)

def classify_intent(user_text: str) -> str:
    """Uses Gemini Flash (Fast & Cheap) to classify the intent."""
    try:
        model = GenerativeModel("gemini-1.5-flash-002") # Use latest fast model available on your GCP
        prompt = f"{prompts.ROUTER_PROMPT}\n\nUser Message: {user_text}"
        
        response = model.generate_content(prompt)
        intent = response.text.strip().upper()
        
        valid_intents = ["MENU_STORY", "MENU_SPAR", "COMPETITOR", "CUSTOMER", "STRESS_TEST", "CHITCHAT"]
        if intent in valid_intents:
            return intent
        return "CHITCHAT"
    except Exception as e:
        logger.error(f"Router AI failed: {e}")
        return "CHITCHAT"

def generate_strategy(intent: str, user_text: str, current_day: int) -> str:
    """Uses Claude Sonnet (Deep Reasoning) to generate the Roger Martin advice."""
    
    # 1. Map intent to the correct Roger Martin Persona
    if intent == "COMPETITOR":
        base_instruction = prompts.COMPETITOR_XRAY
    elif intent == "CUSTOMER":
        base_instruction = prompts.B2B_ETHNOGRAPHER
    elif intent == "STRESS_TEST":
        base_instruction = prompts.WMBT_STRESS_TEST
    else:
        return "Good morning! Ready for today's strategy? Send me a competitor update, a customer email, or a new business idea to stress-test."

    # 2. Inject Context (Allows AI to grade Phase 2 Sparring answers dynamically)
    context_injection = (
        f"\n\nContext: The user is currently on Day {current_day} of their strategy training. "
        "If their message sounds like an answer to a hypothetical sparring scenario, "
        "critique their business instinct ruthlessly using Roger Martin principles. "
        "Tell them why their move is right or wrong, and what the correct strategic move is."
    )
    final_system_instruction = base_instruction + context_injection

    # 3. Call Claude via GCP Vertex AI
    try:
        message = claude_client.messages.create(
            model="claude-3-5-sonnet@20240620", # Use latest Claude model enabled in Vertex Model Garden
            max_tokens=300,
            temperature=0.4,
            system=final_system_instruction,
            messages=[
                {
                    "role": "user",
                    "content": user_text,
                }
            ],
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Specialist AI failed: {e}")
        return "I am currently analyzing massive market datasets. Please give me a moment and try again."
