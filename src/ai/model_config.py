"""
AI model initialization and configuration for house plan generation.
"""
import os
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def initialize_model(gemini_api_key: Optional[str] = None) -> tuple[bool, Optional[genai.GenerativeModel]]:
    """
    Initialize the Gemini AI model
    
    Args:
        gemini_api_key: Google Gemini API key. If None, will try to get from environment
    
    Returns:
        Tuple of (success: bool, model: Optional[GenerativeModel])
    """
    try:
        api_key = gemini_api_key or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
        else:
            print("Warning: No Google API key provided. Using rule-based generation instead.")
            return False, None
        
        # List available models
        print("Available models:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
        
        # Initialize the model
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        # Test the model with a simple prompt
        test_response = model.generate_content("Hello")
        if test_response:
            print("Successfully initialized Gemini model")
            return True, model
        else:
            raise Exception("Failed to initialize Gemini model")
            
    except Exception as e:
        print(f"Warning: Failed to initialize Gemini API: {e}")
        print("Using rule-based generation instead.")
        return False, None 