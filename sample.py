from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import re
from amadeus import Client, ResponseError
from amadeus_api import get_flight_prices_with_links, resolve_city_to_code
from hotel_api import get_hotel_prices_with_links
import google.generativeai as genai
from dateutil import parser

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Trip context memory
trip_context = {
    "origin": "",
    "destination": "",
    "departure_date": "",
    "return_date": "",
    "budget": "",
    "accommodation": "",
    "interests": ""
}

# Set up Gemini model
#model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
model = genai.GenerativeModel("models/gemini-1.5-flash-latest")

chat = model.start_chat()

def normalize_date(date_str):
    try:
        return parser.parse(date_str).strftime('%Y-%m-%d')
    except:
        return date_str  # fallback if parsing fails

def initialize_chat():
    instruction = (
        "You are a smart travel assistant. Help users plan trips with itineraries, "
        "suggest hotels and flights, and answer travel-related questions. "
        "Be friendly, detailed, and always respond helpfully."
    )
    chat.send_message(instruction)

def chat_with_gemini(user_input):
    try:
        # Step 1: Extract or update fields from user input
        extraction_prompt = (
            "Update only the fields below based on the user's message. If something is not mentioned, leave it blank.\n"
            "Return the result in this format:\n"
            "origin: ...\ndestination: ...\ndeparture_date: ...\nreturn_date: ...\n"
            "budget: ...\naccommodation: ...\ninterests: ...\n\n"
            f"User message: {user_input}"
        )
        extraction_response = chat.send_message(extraction_prompt)
        extracted = extraction_response.text.strip()

        # Step 2: Update trip context based on Gemini extraction
        for key in trip_context:
            match = re.search(fr"{key}:\s*(.+)", extracted, re.IGNORECASE)
            if match and match.group(1).strip():
                trip_context[key] = match.group(1).strip()

        print("\U0001F4E6 Current Trip Context:", trip_context)

        # Step 3: If sufficient info, resolve city names to IATA codes and fetch flights, hotels
        if all([trip_context["destination"], trip_context["departure_date"], trip_context["return_date"]]):
            # origin_code = resolve_city_to_code(trip_context["origin"])
            # destination_code = resolve_city_to_code(trip_context["destination"])
            departure_date = normalize_date(trip_context["departure_date"])
            return_date = normalize_date(trip_context["return_date"])

            # print(f"\U0001F3AF Resolved codes: {trip_context['origin']} → {origin_code}, {trip_context['destination']} → {destination_code}")
            # print(f"\U0001F4C5 Normalized departure date: {departure_date}")

            # flights = get_flight_prices_with_links(
            #     origin_code, destination_code, departure_date
            # )

            hotels = get_hotel_prices_with_links(
                trip_context["destination"],
                departure_date,
                return_date,
            )
            # Step 4: Generate a Gemini response with flight and hotel options
            prompt = (
                f"\nHere are hotel options in {trip_context['destination']}:\n\n" +
                "\n".join(hotels) +
                f"\n\nTraveler preferences: budget {trip_context['budget']}, "
                f"interests: {trip_context['interests']}, preferred accommodation: {trip_context['accommodation']}.\n\n"
                "Please list and compare these options, and include the booking link for each one."
            )
            # If we have origin, destination, and date but no hotel info
        elif all([trip_context["origin"], trip_context["destination"], trip_context["departure_date"]]):
            # If we have origin, destination, and date but no hotel info
            origin_code = resolve_city_to_code(trip_context["origin"])
            destination_code = resolve_city_to_code(trip_context["destination"])
            departure_date = normalize_date(trip_context["departure_date"])
            print(f"\U0001F3AF Resolved codes: {trip_context['origin']} → {origin_code}, {trip_context['destination']} → {destination_code}")
            print(f"\U0001F4C5 Normalized departure date: {departure_date}")
            flights = get_flight_prices_with_links(
                origin_code, destination_code, departure_date
            )

            # Step 4: Generate a Gemini response with real flights
            prompt = (
                f"Here are real flight options from {trip_context['origin']} to {trip_context['destination']} "
                f"on {trip_context['departure_date']}:\n\n" +
                "\n".join(flights) +
                f"\n\nTraveler preferences: budget {trip_context['budget']}, "
                f"interests: {trip_context['interests']}, preferred accommodation: {trip_context['accommodation']}.\n\n"
                "Please list and compare these flight options, and include the booking link for each one."
            )
        else:
            # Not enough data yet — ask Gemini to help clarify
            prompt = f"The user said: {user_input}\nPlease help clarify missing travel info like origin, destination, or date."

        response = chat.send_message(prompt)
        return response.text

    except Exception as e:
        # return f"❌ Error: {e}"
        return f"The user said: {user_input}\nPlease help clarify missing travel info like origin, destination, or date."

def main():
    print("\U0001F972 Travel Itinerary Chatbot with Memory\nType 'exit' to end the conversation.\n")
    initialize_chat()

    while True:
        user_input = input("\U0001F9D1 You: ")
        if user_input.lower() in ['exit', 'quit']:
            print("\U0001F44B Goodbye!")
            break

        reply = chat_with_gemini(user_input)
        print(f"\U0001F916 Gemini: {reply}\n")

if __name__ == "__main__":
    main()