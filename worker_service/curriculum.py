# worker_service/curriculum.py
import logging
from google.cloud import firestore

logger = logging.getLogger("worker.curriculum")

# Initialize Firestore client once outside the function scope
try:
    db = firestore.Client()
except Exception as e:
    logger.critical(f"Failed to initialize Firestore in curriculum.py: {e}")
    db = None

def get_daily_cron_message(current_day: int) -> dict:
    """
    Triggered by the 9:00 AM Cron Job. 
    Returns a dictionary containing the text and any WhatsApp buttons to display.
    """
    # Phase 1: Onboarding (Day 1)
    if current_day == 1:
        text = (
            "Namaskaram. Welcome to the StrategyOS Boardroom.\n\n"
            "I am here to act as your Chief Strategy Officer. Every morning, I will send you a 60-second "
            "strategy case study or a sparring scenario to test your instincts.\n\n"
            "The Golden Rule: You don't have to wait for my morning message. The exact moment a client asks "
            "for a discount, or a competitor drops a price, forward their email/chat to me here. I will script your counter-move."
        )
        return {"text": text, "buttons": None}
    
    # Phase 1: Habit Building (Days 2 to 14)
    # Force-feed the story to build the habit. No buttons needed.
    elif 2 <= current_day <= 14:
        story_text = get_user_requested_content(current_day, "STORY")
        return {"text": story_text, "buttons": None}
        
    # Phase 2: The Agency Model (Days 15+)
    # Send the Interactive Menu and let the CEO choose their mental workout.
    else:
        text = (
            f"Morning Sethji. Welcome to Day {current_day} of the Boardroom.\n\n"
            "Choose your mental workout for today:"
        )
        buttons = [
            {"id": "MENU_STORY", "title": "📖 Case Study"},
            {"id": "MENU_SPAR", "title": "🥊 Sparring"}
        ]
        return {"text": text, "buttons": buttons}

def get_user_requested_content(current_day: int, content_type: str) -> str:
    """
    Triggered when the Gemini Router detects a menu button tap.
    Fetches the actual text directly from the GCP Firestore database.
    """
    if not db:
        return "My database connection is temporarily down. What real-world problem are you facing right now?"

    try:
        # Query Firestore: Collection 'ContentLibrary', Document 'Day_X'
        doc_ref = db.collection("ContentLibrary").document(f"Day_{current_day}")
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            if content_type == "STORY":
                return data.get("story_text", "Today's story is still being written in the Boardroom. Check back later!")
            elif content_type == "SPAR":
                return data.get("spar_text", "Today's sparring scenario is still being prepared. Got a real problem instead?")
        else:
            return "You've reached the edge of the current curriculum! Send me a real problem from your factory to stress-test."
            
    except Exception as e:
        logger.error(f"Failed to fetch curriculum from DB for Day {current_day}: {e}")
        return "Let's skip the theory today. What real-world problem are you facing right now?"
