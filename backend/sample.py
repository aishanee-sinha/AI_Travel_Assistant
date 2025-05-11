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
    "interests": "",
    "duration": ""
}

# Set up Gemini model
model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
chat = model.start_chat()

def normalize_date(date_str):
    """Use Gemini to normalize any date format into YYYY-MM-DD"""
    try:
        prompt = (
            "Convert this date to YYYY-MM-DD format. "
            "If the year is not specified, use the current year. "
            "If the date is ambiguous or invalid, return 'invalid'. "
            "Return ONLY the date in YYYY-MM-DD format, nothing else. "
            f"Date to normalize: {date_str}"
        )
        response = chat.send_message(prompt)
        normalized_date = response.text.strip()
        # Validate the date format using datetime
        try:
            datetime.strptime(normalized_date, '%Y-%m-%d')
            return normalized_date
        except ValueError:
            return "invalid"
    except Exception as e:
        print(f"Error normalizing date: {str(e)}")
        return "invalid"

def initialize_chat():
    instruction = (
        "You are a smart travel assistant. Help users plan trips with itineraries, "
        "suggest hotels and flights, and answer travel-related questions. "
        "Be friendly, detailed, and always respond helpfully."
        "Your goal is to fill trip_context = {"
        "origin: [city name]"
        "destination: [city name]"
        "departure_date: [date in YYYY-MM-DD format]"
        "return_date: [date in YYYY-MM-DD format]"
        "budget: [amount]"
        "accommodation: [preference]"
        "interests: [interests]"
        "duration: [number only]"
        "}"
        "Keep the conversation going until the user is satisfied with the trip context."
    )
    chat.send_message(instruction)

def generate_itinerary(destination, duration, interests=""):
    prompt = (
        f"Create a detailed {duration}-day itinerary for {destination}. "
        f"Break it down day by day, starting each day with 'Day X:' (e.g., 'Day 1:'). "
        f"List morning, afternoon, and evening activities for each day. "
        f"Consider these interests: {interests}. "
        "Include major attractions, local experiences, and dining recommendations."
    )
    response = chat.send_message(prompt)
    return response.text

def generate_itinerary_html(destination, duration, interests=""):
    prompt = (
        f"Create a detailed {duration}-day itinerary for {destination}. "
        f"Break it down day by day. For each day, start with an emoji and a bolded title, e.g., '<span>📅 <strong>Day 1: City Name</strong></span>'. "
        f"For each day, use nested bullet points for morning, afternoon, and evening activities, using <ul> and <li> tags. "
        f"Use <strong> for subheadings like 'Morning', 'Lunch', etc. "
        f"Format the entire itinerary as HTML. Do NOT use Markdown. "
        f"Return only the HTML, no explanations. "
        f"Consider these interests: {interests}. "
        "Include major attractions, local experiences, and dining recommendations."
    )
    response = chat.send_message(prompt)
    return response.text

def strip_code_blocks(text):
    return re.sub(r"^```html|^```|```$", "", text.strip(), flags=re.MULTILINE).strip()

def generate_flights_html(origin, destination, date):
    flights = get_flight_prices_with_links(origin, destination, date)
    html = '<span>✈️ <strong>Flight Options</strong></span><ul>'
    for flight in flights:
        html += "<li>" + "<br>".join(flight.split('\n')) + "</li>"
    html += "</ul>"
    return html

def generate_hotels_html(destination, checkin, checkout):
    hotels = get_hotel_prices_with_links(destination, checkin, checkout)
    html = '<span>🏨 <strong>Hotel Options</strong></span><ul>'
    for hotel in hotels:
        html += "<li>" + "<br>".join(hotel.split('\n')) + "</li>"
    html += "</ul>"
    return html

def generate_tips_html(destination):
    prompt = (
        f"Give travel tips for {destination}. "
        "Start with an emoji and a bolded title, e.g., '<span>🚕 <strong>Transportation & Tips</strong></span>'. "
        "List tips as bullet points, using <ul> and <li> tags. "
        "Use <strong> for key words (e.g., 'MetroCard', 'Packing'). "
        "Format the entire response as HTML. Do NOT use Markdown. "
        "Return only the HTML, no explanations."
    )
    response = chat.send_message(prompt)
    return response.text

def extract_trip_context(user_input):
    # Initialize context with current values
    context = trip_context.copy()
    # First, use Gemini to extract and normalize the date
    date_prompt = (
        "Given the current date and the user's message, determine the exact date they want to travel. "
        "If they mention a relative date (like 'next Monday'), calculate the actual date. "
        "If they mention a date without a year, use the current year. "
        "Return ONLY the date in YYYY-MM-DD format, nothing else. "
        f"Current date: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"User message: {user_input}"
    )
    try:
        date_response = chat.send_message(date_prompt)
        departure_date = date_response.text.strip()
        # Validate the date
        try:
            # Check if the date is in the future
            parsed_date = datetime.strptime(departure_date, '%Y-%m-%d')
            if parsed_date < datetime.now():
                # If the date is in the past, try next year
                parsed_date = parsed_date.replace(year=parsed_date.year + 1)
                departure_date = parsed_date.strftime('%Y-%m-%d')
            context["departure_date"] = departure_date
        except ValueError:
            print(f"Invalid date format from Gemini: {departure_date}")
        # Now extract other trip information
        extraction_prompt = (
            "Extract the following information from the user's message. "
            "If a field is not mentioned, leave it blank. "
            "Return the result in this format:\n"
            "destination: [city name]\n"
            "duration: [number only]\n"
            "origin: [city name]\n"
            "budget: [amount]\n"
            "accommodation: [preference]\n"
            "interests: [interests]\n\n"
            f"User message: {user_input}"
        )
        extraction_response = chat.send_message(extraction_prompt)
        extracted = extraction_response.text.strip()
        print("Gemini extraction response:", extracted)  # DEBUG LOGGING
        # Parse the extracted information
        for line in extracted.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                if key in context and value:
                    if key == 'duration':
                        # Use Gemini to extract just the number
                        duration_prompt = (
                            "Extract just the number from this duration. "
                            "Return ONLY the number, nothing else. "
                            f"Duration: {value}"
                        )
                        duration_response = chat.send_message(duration_prompt)
                        duration = duration_response.text.strip()
                        if duration.isdigit():
                            context[key] = duration
                            # Calculate return date if we have departure date
                            if context["departure_date"]:
                                context["return_date"] = calculate_return_date(context["departure_date"], context["duration"])
                    else:
                        context[key] = value
    except Exception as e:
        print(f"Error in extraction: {str(e)}")
    return context

def calculate_return_date(departure_date, duration):
    try:
        dep_date = datetime.strptime(departure_date, "%Y-%m-%d")
        ret_date = dep_date + timedelta(days=int(duration))
        return ret_date.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Error calculating return date: {str(e)}")
        return ""

def chat_with_gemini(user_input):
    try:
        extracted_context = extract_trip_context(user_input)
        for key in trip_context:
            if extracted_context[key]:
                trip_context[key] = extracted_context[key]
        print("\U0001F4E6 Current Trip Context:", trip_context)

        # If destination and duration are present but no departure_date, prompt for dates
        if trip_context["destination"] and trip_context["duration"] and not trip_context["departure_date"]:
            return (
                f"Great! I see you want to plan a {trip_context['duration']}-day trip to {trip_context['destination']}. "
                "Could you please provide your travel start date (e.g., 2024-07-01)?"
            )

        # Case 1: Only destination and duration provided
        if trip_context["destination"] and trip_context["duration"] and not trip_context["departure_date"] and not trip_context["origin"]:
            itinerary_html = strip_code_blocks(generate_itinerary_html(trip_context["destination"], trip_context["duration"], trip_context["interests"]))
            tips_html = strip_code_blocks(generate_tips_html(trip_context["destination"]))
            return f"{itinerary_html}\n\n{tips_html}"

        # Case 2: Destination, duration, and start date provided
        if trip_context["destination"] and trip_context["duration"] and trip_context["departure_date"] and not trip_context["origin"]:
            hotels_html = generate_hotels_html(
                trip_context["destination"],
                trip_context["departure_date"],
                trip_context["return_date"],
            )
            itinerary_html = strip_code_blocks(generate_itinerary_html(trip_context["destination"], trip_context["duration"], trip_context["interests"]))
            tips_html = strip_code_blocks(generate_tips_html(trip_context["destination"]))
            return f"{itinerary_html}\n\n{hotels_html}\n\n{tips_html}"

        # Case 3: All information provided
        if all([trip_context["origin"], trip_context["destination"], trip_context["departure_date"], trip_context["duration"]]):
            flights_html = generate_flights_html(
                trip_context["origin"],
                trip_context["destination"],
                trip_context["departure_date"]
            )
            hotels_html = generate_hotels_html(
                trip_context["destination"],
                trip_context["departure_date"],
                trip_context["return_date"],
            )
            itinerary_html = strip_code_blocks(generate_itinerary_html(trip_context["destination"], trip_context["duration"], trip_context["interests"]))
            tips_html = strip_code_blocks(generate_tips_html(trip_context["destination"]))
            return f"{flights_html}\n\n{hotels_html}\n\n{itinerary_html}\n\n{tips_html}"

        # Default case: Not enough information
        return "I need more information to help you plan your trip. Please provide at least the destination and duration of your trip."
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}. Please try again with your travel details." 