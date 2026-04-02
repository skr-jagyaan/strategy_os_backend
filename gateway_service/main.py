import logging
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional

import database as db
import pubsub_publisher as pubsub

# Configure production logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gateway.main")

app = FastAPI(title="StrategyOS Gateway")

# --- PYDANTIC SCHEMAS (For payload validation) ---
class GraphyWebhookPayload(BaseModel):
    name: str = Field(..., description="Client's full name")
    phone: str = Field(..., description="Client's WhatsApp number with country code")
    industry: str = Field(default="General Manufacturing")
    payment_status: str = Field(...)

class WhatsAppWebhookPayload(BaseModel):
    phone: str = Field(..., description="Sender's phone number")
    text: str = Field(..., description="The message content")
    message_type: Optional[str] = "text"

# --- ENDPOINTS ---

@app.post("/webhook/graphy")
async def handle_graphy_onboarding(payload: GraphyWebhookPayload):
    """Catches Razorpay/Graphy success payments."""
    logger.info(f"Received Graphy webhook for: {payload.phone}")
    
    if payload.payment_status.lower() != "success":
        logger.warning(f"Payment not successful for {payload.phone}, aborting onboarding.")
        return {"status": "ignored", "reason": "payment_not_success"}

    try:
        # 1. Save to Database
        success = db.add_new_user(payload.name, payload.phone, payload.industry)
        if not success:
            raise HTTPException(status_code=500, detail="Database write failed")

        # 2. Drop "Day 1 Welcome" task into Pub/Sub for Service B to execute
        pubsub.publish_task(
            phone=payload.phone,
            message_type="DAILY_STORY",
            current_day=1
        )
        
        return {"status": "success", "message": "User onboarded and queued for Welcome Message."}
    except Exception as e:
        logger.error(f"Onboarding flow failed: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/webhook/whatsapp")
async def handle_whatsapp_message(payload: WhatsAppWebhookPayload):
    """Catches incoming WhatsApp messages from Wati/Interakt."""
    try:
        # 1. Validate User Exists (Security check)
        user = db.get_user(payload.phone)
        if not user or user.get("status") != "active":
            logger.warning(f"Unauthorized or inactive user attempted contact: {payload.phone}")
            # Still return 200 so WhatsApp doesn't retry, but ignore the payload
            return {"status": "ignored", "reason": "unauthorized_user"}

        # 2. Push to Queue immediately
        published = pubsub.publish_task(
            phone=payload.phone, 
            message_type="INCOMING_CHAT", 
            text=payload.text
        )
        
        if not published:
            raise HTTPException(status_code=500, detail="Failed to queue task")

        # 3. Log query for rate limiting/analytics
        db.increment_user_day_and_query(payload.phone, is_query=True)

        # 4. Instantly return 200 OK to prevent Webhook timeouts
        return {"status": "success", "message": "Task queued for AI processing"}
    except Exception as e:
        logger.error(f"WhatsApp webhook flow failed: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/cron/daily-habit")
@app.get("/cron/daily-habit") # Allow GET for easier testing
async def trigger_daily_habit(request: Request):
    """Triggered by GCP Cloud Scheduler every day at 9:00 AM IST."""
    logger.info("Daily habit cron triggered.")
    try:
        # 1. Fetch all active users
        users = db.get_active_users()
        logger.info(f"Found {len(users)} active users to process.")

        success_count = 0
        for user in users:
            phone = user.get("phone_number")
            current_day = user.get("current_day", 1)

            # 2. Push Daily Story task to the queue
            published = pubsub.publish_task(
                phone=phone,
                message_type="DAILY_STORY",
                current_day=current_day
            )

            # 3. Increment their day for tomorrow
            if published:
                db.increment_user_day_and_query(phone, is_query=False)
                success_count += 1

        return {"status": "success", "users_processed": success_count}
    except Exception as e:
        logger.error(f"Daily cron flow failed: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Health check for Cloud Run instances
@app.get("/")
async def health_check():
    return {"status": "healthy", "service": "StrategyOS Gateway"}
