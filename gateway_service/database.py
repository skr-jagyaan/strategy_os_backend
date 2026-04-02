import logging
from google.cloud import firestore
from google.api_core.exceptions import GoogleAPIError
from datetime import datetime, timezone

logger = logging.getLogger("gateway.database")

# Initialize Firestore client (relies on GCP default credentials)
try:
    db = firestore.Client()
    users_ref = db.collection("Users")
except Exception as e:
    logger.critical(f"Failed to initialize Firestore client: {e}")
    raise

def add_new_user(name: str, phone: str, industry: str) -> bool:
    """Creates a new user record in Firestore."""
    try:
        doc_ref = users_ref.document(phone)
        doc_ref.set({
            "name": name,
            "phone_number": phone,
            "industry": industry,
            "status": "active",
            "current_day": 1,
            "total_queries": 0,
            "join_date": datetime.now(timezone.utc)
        })
        logger.info(f"Successfully added new user: {phone}")
        return True
    except GoogleAPIError as e:
        logger.error(f"Firestore API error when adding user {phone}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error adding user {phone}: {e}")
        return False

def get_user(phone: str) -> dict:
    """Fetches a specific user to validate they exist."""
    try:
        doc = users_ref.document(phone).get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        logger.error(f"Error fetching user {phone}: {e}")
        return None

def get_active_users() -> list:
    """Returns a list of all active users for the daily cron job."""
    try:
        # Query for users who are active and haven't finished the 90 days
        query = users_ref.where(filter=firestore.FieldFilter("status", "==", "active"))\
                         .where(filter=firestore.FieldFilter("current_day", "<=", 90))
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error(f"Error fetching active users: {e}")
        return []

def increment_user_day_and_query(phone: str, is_query: bool = False) -> bool:
    """Increments the current_day or total_queries counter."""
    try:
        doc_ref = users_ref.document(phone)
        updates = {}
        if is_query:
            updates["total_queries"] = firestore.Increment(1)
        else:
            updates["current_day"] = firestore.Increment(1)
            
        doc_ref.update(updates)
        return True
    except Exception as e:
        logger.error(f"Error updating stats for user {phone}: {e}")
        return False
