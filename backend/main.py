import os
import requests

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI


# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

load_dotenv()

app = FastAPI(title="WeatherGPT API")


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost",
        "https://localhost",
        "capacitor://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# OpenAI setup
# --------------------------------------------------

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("OPENAI_API_KEY is missing")

client = OpenAI(api_key=api_key)


# --------------------------------------------------
# Chat request model
# --------------------------------------------------

class ChatRequest(BaseModel):
    message: str


# --------------------------------------------------
# Home endpoint
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "WeatherGPT AI backend is running!"
    }


# --------------------------------------------------
# AI Chat endpoint
# --------------------------------------------------

@app.post("/api/chat")
def chat(request: ChatRequest):

    response = client.responses.create(
        model="gpt-5.6-luna",
        instructions="""
You are WeatherGPT, an AI weather assistant.

Help users understand weather and make plans involving:
- Temperature
- Rain
- Wind
- Humidity
- UV
- Travel
- Outdoor activities
- Clothing
- Weather plans

Be friendly, clear and concise.

Never invent real-time weather information.
Actual weather data will be provided separately.
Use the supplied weather data whenever it is available.
""",
        input=request.message,
    )

    return {
        "reply": response.output_text
    }


# --------------------------------------------------
# Weather endpoint
# --------------------------------------------------

@app.get("/api/weather")
def get_weather(city: str):

    # ----------------------------------------------
    # Geocoding
    # ----------------------------------------------

    geo_url = "https://geocoding-api.open-meteo.com/v1/search"

    geo_response = requests.get(
        geo_url,
        params={
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json",
        },
        timeout=10,
    )

    geo_response.raise_for_status()

    geo_data = geo_response.json()

    if not geo_data.get("results"):
        return {
            "error": "City not found"
        }

    location = geo_data["results"][0]

    latitude = location["latitude"]
    longitude = location["longitude"]

    city_name = location["name"]
    country = location.get("country", "")


    # ----------------------------------------------
    # Weather API
    # ----------------------------------------------

    weather_url = "https://api.open-meteo.com/v1/forecast"

    weather_response = requests.get(
        weather_url,
        params={
            "latitude": latitude,
            "longitude": longitude,

            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "apparent_temperature,"
                "precipitation,"
                "weather_code,"
                "wind_speed_10m"
            ),

            "hourly": (
                "temperature_2m,"
                "precipitation_probability,"
                "relative_humidity_2m,"
                "wind_speed_10m"
            ),

            "daily": (
                "temperature_2m_max,"
                "temperature_2m_min,"
                "precipitation_probability_max,"
                "uv_index_max"
            ),

            "timezone": "auto",
            "forecast_days": 7,
        },
        timeout=10,
    )

    weather_response.raise_for_status()

    weather_data = weather_response.json()


    # ----------------------------------------------
    # Return weather data
    # ----------------------------------------------

    return {
        "location": {
            "city": city_name,
            "country": country,
            "latitude": latitude,
            "longitude": longitude,
        },

        "current": weather_data.get("current"),

        "hourly": weather_data.get("hourly"),

        "daily": weather_data.get("daily"),
    }