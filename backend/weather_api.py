import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("models/gemini-1.5-flash-latest")

def get_weather_climatology(location, date):
    base_url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}/{date}"

    params = {
        "key": os.getenv("WEATHER_API"),
        "include": "days",
        "elements": "datetime,tempmax,tempmin,precip,description",
        "unitGroup": "metric"  # use "us" for Fahrenheit
    }

    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        data = response.json()
        day = data["days"][0]
        weather_info = (
            f"📍 Weather Forecast for {location} on {day['datetime']}:\n"
            f"- Description: {day.get('description', 'N/A')}\n"
            f"- Max Temperature: {day['tempmax']} °C\n"
            f"- Min Temperature: {day['tempmin']} °C\n"
            f"- Precipitation: {day['precip']} mm\n"
        )
        return weather_info
    else:
        error_msg = f"❌ Failed to fetch weather data for {location} on {date}.\nError: {response.text}"
        return error_msg
