# worker_service/whatsapp_client.py
import os
import httpx
import logging

logger = logging.getLogger("worker.whatsapp")

WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", "https://api.your-provider.com/v1/messages")
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN", "your-secret-token")

async def send_whatsapp_message(phone: str, text: str, buttons: list = None) -> bool:
    """Sends an outbound WhatsApp message. Uses Interactive Buttons if provided."""
    headers = {
        "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    if buttons:
        # Send Interactive Button Message
        # Max 3 buttons allowed by WhatsApp
        formatted_buttons = []
        for btn in buttons:
            formatted_buttons.append({
                "type": "reply",
                "reply": {
                    "id": btn["id"], # Hidden ID sent back to your server
                    "title": btn["title"] # Text visible to the user (max 20 chars)
                }
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text},
                "action": {"buttons": formatted_buttons}
            }
        }
    else:
        # Send Standard Text Message
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": text}
        }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
            logger.info(f"Successfully sent message to {phone}")
            return True
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message to {phone}. Error: {e}")
        return False
