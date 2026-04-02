import os
import httpx
import logging

logger = logging.getLogger("worker.whatsapp")

# E.g., Wati or Interakt API URL and Token
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", "https://api.your-whatsapp-provider.com/v1/messages")
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN", "your-secret-token")

async def send_whatsapp_message(phone: str, text: str) -> bool:
    """Sends an outbound WhatsApp message via your provider."""
    headers = {
        "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # NOTE: Adjust this payload structure to match your specific provider (Wati/Interakt)
    payload = {
        "phoneNumber": phone,
        "message": text
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
            logger.info(f"Successfully sent WhatsApp message to {phone}")
            return True
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message to {phone}. Error: {e}")
        return False
