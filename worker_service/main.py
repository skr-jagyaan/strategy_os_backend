import base64
import json
import logging
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel

import agent_manager as ai
import whatsapp_client as whatsapp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("worker.main")

app = FastAPI(title="StrategyOS Worker")

class PubSubMessage(BaseModel):
    data: str # Pub/Sub sends the payload as a base64 encoded string

class PubSubPushPayload(BaseModel):
    message: PubSubMessage

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

        logger.info(f"Processing task for {phone}. Type: {message_type}")

        # 2. Handle the specific task type
        if message_type == "DAILY_STORY":
            # For V1, we send a hardcoded story based on the day. 
            # In V2, you would pull this from a database of stories.
            final_reply = f"Morning! Welcome to Day {current_day} of the Boardroom. Ready to spar?"
        
        elif message_type == "INCOMING_CHAT":
            # Run the Double-LLM Pipeline
            intent = ai.classify_intent(text)
            logger.info(f"Router classified {phone}'s message as: {intent}")
            final_reply = ai.generate_strategy(intent, text)
            
        else:
            logger.warning(f"Unknown task type: {message_type}")
            return {"status": "ignored"}

        # 3. Send the final result back via WhatsApp
        await whatsapp.send_whatsapp_message(phone, final_reply)
        
        return {"status": "success"}

    except Exception as e:
        logger.error(f"Worker crashed while processing Pub/Sub message: {e}")
        # Return 500 so Pub/Sub knows it failed and will retry the message later
        raise HTTPException(status_code=500, detail="Worker Error")

@app.get("/")
async def health_check():
    return {"status": "healthy", "service": "StrategyOS AI Worker"}
