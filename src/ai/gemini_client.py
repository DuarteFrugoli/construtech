"""
AI model initialization and configuration for house plan generation.
"""
import os
import logging
from typing import Optional, Tuple
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_use_ai: bool = False
_model: Optional[genai.GenerativeModel] = None
_initialized: bool = False


def get_model() -> Tuple[bool, Optional[genai.GenerativeModel]]:
    """
    Return the Gemini model singleton, initializing it on first call.

    Returns:
        Tuple of (use_ai: bool, model: Optional[GenerativeModel])
    """
    global _use_ai, _model, _initialized
    if _initialized:
        return _use_ai, _model

    try:
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            logger.warning("No Gemini API key found. Using rule-based generation.")
            _initialized = True
            return False, None

        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel('models/gemini-1.5-flash')
        test_response = _model.generate_content("Hello")
        if test_response:
            logger.info("Gemini model initialized successfully.")
            _use_ai = True
        else:
            raise RuntimeError("Empty test response from Gemini model")

    except Exception as e:
        logger.warning(f"Failed to initialize Gemini API: {e}. Using rule-based generation.")
        _model = None
        _use_ai = False

    _initialized = True
    return _use_ai, _model
 