from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import requests
import os
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

# Create FastAPI app instance
app = FastAPI(
    title="Hotpepper API Wrapper",
    description="A simple API wrapper for the Hotpepper Gourmet API",
    version="1.0.0"
)

# Get API key from environment variable (more secure) or set it directly
# You can set this environment variable with: export HOTPEPPER_API_KEY="your_api_key"
API_KEY = os.environ.get("HOTPEPPER_API_KEY")  # Replace with your actual API key if not using env var

# Base URL for Hotpepper API
BASE_URL = "http://webservice.recruit.co.jp/hotpepper"

# Define Pydantic models for data validation and documentation
class Restaurant(BaseModel):
    id: str
    name: str
    address: str
    access: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    genre: Optional[dict] = None
    budget: Optional[dict] = None
    open: Optional[str] = None
    close: Optional[str] = None
    urls: dict
    photo: Optional[dict] = None

class RestaurantResponse(BaseModel):
    results_available: int
    results_returned: int
    results_start: int
    restaurants: List[Restaurant]

# Routes
@app.get("/")
async def root():
    """
    Welcome endpoint that provides information about the API.
    """
    return {
        "message": "Welcome to the Hotpepper API wrapper!",
        "available_endpoints": [
            "/api/health-check",
            "/api/restaurants/search",
            "/api/restaurants/location"
        ]
    }

@app.get("/api/health-check")
async def health_check():
    """
    Check if the API is functioning and if the API key is valid.
    """
    try:
        # Test the API key with a simple request to large_area endpoint
        url = f"{BASE_URL}/large_area/v1/"
        params = {
            "key": API_KEY,
            "format": "json"
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if "results" in data and "large_area" in data["results"]:
                return {
                    "status": "ok",
                    "message": "API key is valid",
                    "areas_available": len(data["results"]["large_area"])
                }
        
        return {
            "status": "error",
            "message": "Invalid API key or API error",
            "details": response.text
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to connect to Hotpepper API",
            "details": str(e)
        }

@app.get("/api/restaurants/search", response_model=RestaurantResponse)
async def search_restaurants(
    keyword: Optional[str] = None,
    area: Optional[str] = None,
    genre: Optional[str] = None,
    budget: Optional[str] = None,
    count: int = Query(10, ge=1, le=100),
    start: int = 1
):
    """
    Search for restaurants based on various criteria.
    
    - **keyword**: Search keyword (e.g., restaurant name, cuisine type)
    - **area**: Large area code (e.g., 'Z011' for Tokyo)
    - **genre**: Genre code
    - **budget**: Budget code
    - **count**: Number of results to return (max 100)
    - **start**: Starting position of the results
    """
    try:
        # Prepare the API request
        url = f"{BASE_URL}/gourmet/v1/"
        
        params = {
            "key": API_KEY,
            "format": "json",
            "count": count,
            "start": start
        }
        
        # Add optional parameters if provided
        if keyword:
            params["keyword"] = keyword
        if area:
            params["large_area"] = area
        if genre:
            params["genre"] = genre
        if budget:
            params["budget"] = budget
            
        # Send the request to Hotpepper API
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Error from Hotpepper API")
            
        data = response.json()
        
        # Format the response according to our model
        result = {
            "results_available": data["results"]["results_available"],
            "results_returned": data["results"]["results_returned"],
            "results_start": data["results"]["results_start"],
            "restaurants": data["results"]["shop"]  # 'shop' is the key for restaurants in the API response
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/restaurants/location", response_model=RestaurantResponse)
async def search_restaurants_by_location(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    range: int = Query(3, ge=1, le=5, description="Search radius (1: 300m, 2: 500m, 3: 1000m, 4: 2000m, 5: 3000m)"),
    keyword: Optional[str] = None,
    genre: Optional[str] = None,
    count: int = Query(10, ge=1, le=100),
    start: int = 1
):
    """
    Search for restaurants near a specific location.
    
    - **lat**: Latitude of the location
    - **lng**: Longitude of the location
    - **range**: Search radius (1-5, where 1=300m and 5=3000m)
    - **keyword**: Search keyword (e.g., cuisine type)
    - **genre**: Genre code
    - **count**: Number of results to return (max 100)
    - **start**: Starting position of the results
    """
    try:
        # Prepare the API request
        url = f"{BASE_URL}/gourmet/v1/"
        
        params = {
            "key": API_KEY,
            "format": "json",
            "lat": lat,
            "lng": lng,
            "range": range,
            "count": count,
            "start": start
        }
        
        # Add optional parameters if provided
        if keyword:
            params["keyword"] = keyword
        if genre:
            params["genre"] = genre
            
        # Send the request to Hotpepper API
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Error from Hotpepper API")
            
        data = response.json()
        
        # Format the response according to our model
        result = {
            "results_available": data["results"]["results_available"],
            "results_returned": data["results"]["results_returned"],
            "results_start": data["results"]["results_start"],
            "restaurants": data["results"]["shop"]  # 'shop' is the key for restaurants in the API response
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Run the application with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)