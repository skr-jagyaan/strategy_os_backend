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

def get_daily_cron_message(current_day: int) -> str:
    """
    Triggered by the 9:00 AM Cron Job. 
    Decides whether to push a story directly or push the Menu.
    """
    # Phase 1: Onboarding (Day 1)
    if current_day == 1:
        return (
            "Namaskaram. Welcome to the StrategyOS Boardroom.\n\n"
            "I am here to act as your Chief Strategy Officer. Every morning, I will send you a 60-second "
            "strategy case study or a sparring scenario to test your instincts.\n\n"
            "The Golden Rule: You don't have to wait for my morning message. The exact moment a client asks "
            "for a discount, or a competitor drops a price, forward their email/chat to me here. I will script your counter-move."
        )
    
    # Phase 1: Habit Building (Days 2 to 14)
    # Force-feed the story to build the habit.
    elif 2 <= current_day <= 14:
        return get_user_requested_content(current_day, "STORY")
        
    # Phase 2: The Agency Model (Days 15+)
    # Send the Menu and let the CEO choose their mental workout.
    else:
        return (
            f"Morning Sethji. Welcome to Day {current_day} of the Boardroom.\n\n"
            "Choose your mental workout for today:\n"
            "Reply *'STORY'* for a Roger Martin case study.\n"
            "Reply *'SPAR'* for a hypothetical crisis to test your instincts.\n\n"
            "(Or, as always, drop a real-world problem here and let's stress-test it.)"
        )

def get_user_requested_content(current_day: int, content_type: str) -> str:
    """
    Triggered when the Gemini Router detects 'MENU_STORY' or 'MENU_SPAR'.
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
