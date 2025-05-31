"""
House image generation module using OpenAI's DALL-E.
"""
import requests
import logging
from typing import Dict
from fastapi import HTTPException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HouseImageGenerator:
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key

    def generate_house_image(self, description: str, terrain_data: Dict) -> str:
        print(terrain_data, description)
        """
        Generate a realistic house image using DALL-E based on the client's description
        and terrain characteristics.
        """
        try:
            # Extract terrain information
            slope_percentage = terrain_data["slope"]["average_percentage"]
            height_diff = terrain_data["elevation"]["difference"]
            
            # Create a detailed prompt for DALL-E
            prompt = f"""
            A realistic visualization of a house with these characteristics:
            - {description}
            - Terrain slope: {slope_percentage:.1f}%
            - Height difference: {height_diff:.1f}m
            
            The image should be:
            - Photorealistic
            - Show the terrain slope naturally
            - High quality, detailed, and well-lit
            - Adequated to the terrain {terrain_data['address']}
            - do not exagerate on the house. make it appropriate to countrys condition
            """
            
            # Prepare the request to DALL-E API
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024"
            }
            
            # Make the request to DALL-E API
            response = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            
            # Extract the image URL from the response
            result = response.json()
            if "data" not in result or not result["data"]:
                raise HTTPException(status_code=500, detail="No image generated")
                
            return result["data"][0]["url"]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error generating house image: {str(e)}")
            raise HTTPException(status_code=500, detail="Error generating image with DALL-E")
        except Exception as e:
            logger.error(f"Unexpected error in image generation: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) 