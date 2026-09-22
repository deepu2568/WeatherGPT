import os
import requests

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ==================================================
# LOAD ENVIRONMENT VARIABLES
# ==================================================

load_dotenv()


# ==================================================
# APP
# ==================================================

app = FastAPI(title="WeatherGPT API")


# ==================================================
# CORS
# ==================================================

# Local development origins (Vite dev + preview servers).
# These are always allowed so the existing local workflow
# continues to work unchanged.
default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost",
    "https://localhost",
    "capacitor://localhost",
    "http://localhost:8000",
]

# Additional production origins can be supplied (comma separated)
# through the ALLOWED_ORIGINS environment variable, for example:
#   ALLOWED_ORIGINS=https://weathergpt.pages.dev,https://app.example.com
# No secrets are stored here - it is only a list of public web origins.
extra_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

allow_origins = default_origins + extra_origins

# Also accept any Cloudflare Pages / Workers deployment (including
# preview URLs) and any onrender.com host, without hardcoding a
# specific project name. Everything still requires HTTPS.
allow_origin_regex = (
    r"^https://([a-zA-Z0-9-]+\.)*(pages\.dev|workers\.dev)$"
    r"|^https://[a-zA-Z0-9-]+\.onrender\.com$"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================
# API KEYS
# ==================================================

cloudflare_api_key = os.getenv("CLOUDFLARE_API_KEY")
cloudflare_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
weather_api_key = os.getenv("WEATHER_API_KEY")


# ==================================================
# CHECK REQUIRED KEYS
# ==================================================

if not cloudflare_api_key:
    raise RuntimeError("CLOUDFLARE_API_KEY is missing")

if not cloudflare_account_id:
    raise RuntimeError("CLOUDFLARE_ACCOUNT_ID is missing")

if not weather_api_key:
    print("WARNING: WEATHER_API_KEY is missing", flush=True)


# ==================================================
# CHAT REQUEST MODEL
# ==================================================

class ChatRequest(BaseModel):
    message: str


# ==================================================
# HOME
# ==================================================

@app.get("/")
def home():
    return {
        "message": "WeatherGPT AI backend is running!"
    }


# ==================================================
# AI CHAT - CLOUDFLARE GPT-6 ASTRA
# ==================================================

@app.post("/api/chat")
def chat(request: ChatRequest):

    cloudflare_url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{cloudflare_account_id}/ai/v1/chat/completions"
    )

    payload = {
        "model": "openai/gpt-6-astra",
        "messages": [
            {
                "role": "system",
                "content": """
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
Use supplied weather data whenever it is available.
"""
            },
            {
                "role": "user",
                "content": request.message
            }
        ],
        "max_completion_tokens": 1000
    }

    try:

        response = requests.post(
            cloudflare_url,
            headers={
                "Authorization": f"Bearer {cloudflare_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )

        # ------------------------------------------
        # CLOUDFLARE ERROR
        # ------------------------------------------

        if response.status_code != 200:

            try:
                error_data = response.json()
            except Exception:
                error_data = response.text

            print(
                "CLOUDFLARE AI ERROR:",
                error_data,
                flush=True
            )

            return {
                "error": "Cloudflare AI request failed",
                "status": response.status_code,
                "details": error_data,
            }

        # ------------------------------------------
        # PARSE RESPONSE
        # ------------------------------------------

        data = response.json()

        reply = (
            data
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )

        if not reply:

            return {
                "error": "Cloudflare returned an empty AI response",
                "details": data,
            }

        return {
            "reply": reply
        }

    except requests.exceptions.Timeout:

        return {
            "error": "Cloudflare AI request timed out"
        }

    except requests.exceptions.RequestException as e:

        return {
            "error": "Unable to connect to Cloudflare AI",
            "details": str(e),
        }

    except Exception as e:

        return {
            "error": "AI processing failed",
            "details": str(e),
        }


# ==================================================
# WEATHER
# ==================================================

@app.get("/api/weather")
def get_weather(city: str):

    print(
        "WEATHER DEBUG CITY:",
        city,
        flush=True
    )

    # ------------------------------------------
    # CHECK WEATHER API KEY
    # ------------------------------------------

    if not weather_api_key:

        return {
            "error": "WEATHER_API_KEY is missing"
        }

    # ------------------------------------------
    # WEATHERAPI ENDPOINT
    # ------------------------------------------

    weather_url = (
        "https://api.weatherapi.com/v1/forecast.json"
    )

    try:

        response = requests.get(
            weather_url,
            params={
                "key": weather_api_key,
                "q": city,
                "days": 3,
                "aqi": "no",
                "alerts": "no",
            },
            timeout=15,
        )

        # ------------------------------------------
        # WEATHER API ERROR
        # ------------------------------------------

        if response.status_code != 200:

            try:
                error_data = response.json()
            except Exception:
                error_data = {}

            return {
                "error": "Weather API request failed",
                "status": response.status_code,
                "details": error_data,
            }

        weather_data = response.json()

        # ------------------------------------------
        # LOCATION
        # ------------------------------------------

        location = weather_data["location"]

        # ------------------------------------------
        # CURRENT WEATHER
        # ------------------------------------------

        current = weather_data["current"]

        # ------------------------------------------
        # FORECAST
        # ------------------------------------------

        forecast_days = (
            weather_data["forecast"]["forecastday"]
        )

        # ------------------------------------------
        # HOURLY DATA
        # ------------------------------------------

        hourly = {
            "time": [],
            "temperature_2m": [],
            "precipitation_probability": [],
            "relative_humidity_2m": [],
            "wind_speed_10m": [],
        }

        for day in forecast_days:

            for hour in day["hour"]:

                hourly["time"].append(
                    hour["time"]
                )

                hourly["temperature_2m"].append(
                    hour["temp_c"]
                )

                hourly["precipitation_probability"].append(
                    hour["chance_of_rain"]
                )

                hourly["relative_humidity_2m"].append(
                    hour["humidity"]
                )

                hourly["wind_speed_10m"].append(
                    hour["wind_kph"]
                )

        # ------------------------------------------
        # DAILY DATA
        # ------------------------------------------

        daily = {
            "time": [],
            "temperature_2m_max": [],
            "temperature_2m_min": [],
            "precipitation_probability_max": [],
            "uv_index_max": [],
        }

        for day in forecast_days:

            daily["time"].append(
                day["date"]
            )

            daily["temperature_2m_max"].append(
                day["day"]["maxtemp_c"]
            )

            daily["temperature_2m_min"].append(
                day["day"]["mintemp_c"]
            )

            daily["precipitation_probability_max"].append(
                day["day"]["daily_chance_of_rain"]
            )

            daily["uv_index_max"].append(
                day["day"]["uv"]
            )

        # ------------------------------------------
        # FINAL WEATHER RESPONSE
        # ------------------------------------------

        return {

            "location": {

                "city": location["name"],

                "country": location["country"],

                "latitude": location["lat"],

                "longitude": location["lon"],
            },

            "current": {

                "time": location["localtime"],

                "temperature_2m": current["temp_c"],

                "relative_humidity_2m": current["humidity"],

                "apparent_temperature": current["feelslike_c"],

                "precipitation": current["precip_mm"],

                "weather_code": current["condition"]["code"],

                "wind_speed_10m": current["wind_kph"],

                "uv_index": current["uv"],
            },

            "hourly": hourly,

            "daily": daily,
        }

    # ------------------------------------------
    # WEATHER TIMEOUT
    # ------------------------------------------

    except requests.exceptions.Timeout:

        return {
            "error": "Weather API request timed out"
        }

    # ------------------------------------------
    # WEATHER CONNECTION ERROR
    # ------------------------------------------

    except requests.exceptions.RequestException as e:

        return {
            "error": "Unable to connect to weather service",
            "details": str(e),
        }

    # ------------------------------------------
    # GENERAL ERROR
    # ------------------------------------------

    except Exception as e:

        return {
            "error": "Weather processing failed",
            "details": str(e),
        }