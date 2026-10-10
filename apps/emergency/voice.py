"""
Generate a short voice message for the emergency call.
Uses Ollama to compose, then any TTS provider to synthesize.
Fallback: just return the text and use default TTS.
"""
import logging

logger = logging.getLogger(__name__)


def compose_message(alert):
    """Return a short spoken message (~15 seconds)."""
    from ai_engine.llm import generate_text

    user = alert.user
    prompt = f"""Write a calm but urgent phone message (max 30 words) to be
spoken aloud to {user.get_full_name() or user.username}'s emergency contact.

Context:
- Student: {user.get_full_name() or user.username}
- Roll no: {user.username}
- Department: {user.department}
- Hostel: Block {user.hostel_block}, Room {user.room_number}
- Reason for alert: {alert.reason or alert.get_trigger_type_display()}

Output only the message text, no preamble. Start with "This is an emergency alert from BPUT Campus Platform.\""""

    response = generate_text(prompt, temperature=0.3, max_tokens=100)
    if response.success and response.text:
        return response.text.strip()

    # Deterministic fallback
    return (
        f"This is an emergency alert from BPUT Campus Platform. "
        f"Student {user.get_full_name() or user.username}, Roll number {user.username}, "
        f"from {user.department} department, Hostel Block {user.hostel_block} Room {user.room_number}, "
        f"requires immediate assistance. Reason: {alert.reason or alert.get_trigger_type_display()}. "
        f"Please respond immediately."
    )


def synthesize_voice(text):
    """
    Convert text to speech audio file.
    Returns a file path or None if unavailable.
    Uses pyttsx3 (offline) if available, else falls back to None.
    """
    try:
        import pyttsx3
        import tempfile
        import os

        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        tmp.close()
        engine.save_to_file(text, tmp.name)
        engine.runAndWait()
        return tmp.name
    except Exception as e:
        logger.warning(f'TTS failed: {e}')
        return None