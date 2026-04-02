import os
import logging
from vertexai.generative_models import GenerativeModel, Part
import vertexai
from anthropic import AnthropicVertex

from prompts import prompts

logger = logging.getLogger("worker.ai")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
LOCATION = os.getenv("GCP_LOCATION", "us-central1")

# Initialize Vertex AI for Gemini (Router)
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Initialize Anthropic Vertex SDK for Claude (Specialist)
# Note: Ensure the Claude API is enabled in your GCP Vertex Model Garden
claude_client = AnthropicVertex(project_id=PROJECT_ID, region=LOCATION)

def classify_intent(user_text: str) -> str:
    """Uses Gemini Flash (Fast & Cheap) to classify the intent."""
    try:
        # Using Gemini Flash for routing speed
        model = GenerativeModel("gemini-1.5-flash-preview-0514") 
        prompt = f"{prompts.ROUTER_PROMPT}\n\nUser Message: {user_text}"
        
        response = model.generate_content(prompt)
        intent = response.text.strip().upper()
        
        valid_intents = ["COMPETITOR", "CUSTOMER", "STRESS_TEST"]
        if intent in valid_intents:
            return intent
        return "CHITCHAT"
    except Exception as e:
        logger.error(f"Router AI failed: {e}")
        return "CHITCHAT" # Default safe fallback

def generate_strategy(intent: str, user_text: str) -> str:
    """Uses Claude Sonnet (Deep Reasoning) to generate the Roger Martin advice."""
    
    # 1. Map intent to the correct Roger Martin Persona
    if intent == "COMPETITOR":
        system_instruction = prompts.COMPETITOR_XRAY
    elif intent == "CUSTOMER":
        system_instruction = prompts.B2B_ETHNOGRAPHER
    elif intent == "STRESS_TEST":
        system_instruction = prompts.WMBT_STRESS_TEST
    else:
        return "Good morning! Ready for today's strategy? Send me a competitor update, a customer email, or a new business idea to stress-test."

    # 2. Call Claude 3.5/4.6 Sonnet via GCP Vertex AI
    try:
        message = claude_client.messages.create(
            model="claude-3-5-sonnet@20240620", 
            max_tokens=300,
            temperature=0.4, # Low temperature for strict, analytical tone
            system=system_instruction,
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
