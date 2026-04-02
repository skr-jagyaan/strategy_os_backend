# worker_service/main.py
import base64
import json
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import agent_manager as ai
import whatsapp_client as whatsapp
import curriculum

# Configure production-grade logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("worker.main")

app = FastAPI(title="StrategyOS Worker")

# --- PYDANTIC SCHEMAS ---
class PubSubMessage(BaseModel):
    data: str  # Pub/Sub sends the payload as a base64 encoded string

class PubSubPushPayload(BaseModel):
    message: PubSubMessage

# --- ENDPOINTS ---
@app.post("/pubsub/push")
async def handle_pubsub_task(payload: PubSubPushPayload):
    """Triggered internally by GCP Pub/Sub when Service A drops a task in the queue."""
    try:
        # 1. Decode the base64 payload from Pub/Sub
        decoded_data = base64.b64decode(payload.message.data).decode('utf-8')
        task = json.loads(decoded_data)
        
        phone = task.get("phone")
        message_type = task.get("message_type")
        text = task.get("text", "")
        current_day = task.get("current_day", 0)

        if not phone:
            logger.error("Received task without a phone number. Ignoring.")
            return {"status": "ignored", "reason": "missing_phone"}

        logger.info(f"Processing task for {phone}. Type: {message_type}, Day: {current_day}")
        final_reply = ""

        # 2. Routing Logic
        if message_type == "DAILY_STORY":
            # 9:00 AM Cron push (Forced story or Phase 2 Menu)
            final_reply = curriculum.get_daily_cron_message(current_day)
            logger.info(f"Generated Day {current_day} morning push for {phone}")
            
        elif message_type == "INCOMING_CHAT":
            # Active chat: Classify intent with Gemini Router
            intent = ai.classify_intent(text)
            logger.info(f"Router classified {phone}'s message as: {intent}")
            
            # Intercept Menu Commands (Zero API cost for Claude)
            if intent == "MENU_STORY":
                final_reply = curriculum.get_user_requested_content(current_day, "STORY")
            elif intent == "MENU_SPAR":
                final_reply = curriculum.get_user_requested_content(current_day, "SPAR")
                
            # Otherwise, send to Claude for real strategic advice or sparring evaluation
            else:
                final_reply = ai.generate_strategy(intent, text, current_day)
                
        else:
            logger.warning(f"Unknown task type: {message_type}")
            return {"status": "ignored", "reason": "unknown_message_type"}

        # 3. Send final result back via WhatsApp
        if final_reply:
            success = await whatsapp.send_whatsapp_message(phone, final_reply)
            if not success:
                logger.error(f"Failed to send WhatsApp message to {phone}")
                # Raise 500 so Pub/Sub knows the WhatsApp API failed and retries sending later
                raise HTTPException(status_code=500, detail="WhatsApp API Error")
        
        return {"status": "success"}

    except Exception as e:
        logger.error(f"Worker crashed while processing Pub/Sub message: {e}")
        # Return 500 so Pub/Sub knows the generation failed and retries the message
        raise HTTPException(status_code=500, detail="Worker Error")

@app.get("/")
async def health_check():
    """Simple health check for Cloud Run container monitoring."""
    return {"status": "healthy", "service": "StrategyOS AI Worker"}
