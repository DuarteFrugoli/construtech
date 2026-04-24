"""
AI model initialization and configuration for house plan generation.
"""
import os
import logging
from typing import Optional, Tuple
from google import genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-2.5-flash"

_use_ai: bool = False
_client: Optional[genai.Client] = None
_initialized: bool = False


def get_model() -> Tuple[bool, Optional[genai.Client]]:
    """
    Return the Gemini client singleton, initializing it on first call.

    Returns:
        Tuple of (use_ai: bool, client: Optional[genai.Client])
    """
    global _use_ai, _client, _initialized
    if _initialized:
        return _use_ai, _client

    try:
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.warning("No Gemini API key found. Using rule-based generation.")
            _initialized = True
            return False, None

        _client = genai.Client(api_key=api_key)
        logger.info(f"Gemini client initialized (model: {MODEL_NAME}).")
        _use_ai = True

    except Exception as e:
        logger.warning(f"Failed to initialize Gemini API: {e}. Using rule-based generation.")
        _client = None
        _use_ai = False

    _initialized = True
    return _use_ai, _client
 