import os
import json
import logging
from google.cloud import pubsub_v1
from google.api_core.exceptions import GoogleAPIError

logger = logging.getLogger("gateway.pubsub")

# Environment variables (Set these in Cloud Run console)
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
TOPIC_ID = os.getenv("PUBSUB_TOPIC_ID", "incoming-strategy-tasks")

try:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)
except Exception as e:
    logger.critical(f"Failed to initialize Pub/Sub client: {e}")
    raise

def publish_task(phone: str, message_type: str, text: str = "", current_day: int = 0) -> bool:
    """
    Publishes a task to the queue for Service B.
    message_type can be 'INCOMING_CHAT' or 'DAILY_STORY'
    """
    try:
        payload = {
            "phone": phone,
            "message_type": message_type,
            "text": text,
            "current_day": current_day
        }
        
        # Pub/Sub requires data to be encoded as a bytestring
        data_str = json.dumps(payload)
        data_bytes = data_str.encode("utf-8")
        
        # Publish asynchronously
        future = publisher.publish(topic_path, data=data_bytes)
        message_id = future.result(timeout=10)
        
        logger.info(f"Published task for {phone} to Pub/Sub. Message ID: {message_id}")
        return True
    except GoogleAPIError as e:
        logger.error(f"Pub/Sub API error publishing task for {phone}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error publishing task to Pub/Sub: {e}")
        return False
