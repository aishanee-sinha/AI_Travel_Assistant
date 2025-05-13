from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import re
from amadeus import Client, ResponseError
from amadeus_api import get_flight_prices_with_links, resolve_city_to_code
from hotel_api import get_hotel_prices_with_links
from weather_api import get_weather_climatology
import google.generativeai as genai
from dateutil import parser
import json

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Trip context memory
trip_context = {
    "origin": "",
    "destination": "",
    "departure_date": "",
    "return_date": "",
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
            "If the year is not specified, use 2025. "
            "If the date is ambiguous or invalid, return 'invalid'. "
            "For seasons like 'summer', use the start of that season in 2025. "
            "Handle abbreviated months (e.g., 'aug' for August, 'jan' for January). "
            "Handle various date formats like '28 aug', 'aug 28', '28th august', etc. "
            "Return ONLY the date in YYYY-MM-DD format, nothing else. "
            f"Date to normalize: {date_str}"
        )
        response = chat.send_message(prompt)
        normalized_date = response.text.strip()
        print(f"Gemini normalized '{date_str}' to '{normalized_date}'")
        return normalized_date
    except Exception as e:
        print(f"Error in normalize_date: {str(e)}")
        return "invalid"

def initialize_chat():
    instruction = (
        "You are a friendly and knowledgeable travel planning assistant. Your goal is to help users plan their trips "
        "through natural conversation. Follow these guidelines:\n"
        "1. Engage in natural, conversational dialogue\n"
        "2. Ask relevant questions one at a time\n"
        "3. Show empathy and understanding of user preferences\n"
        "4. Provide personalized recommendations based on user interests\n"
        "5. When you have enough information, suggest specific activities and attractions\n"
        "6. Always maintain context of the conversation\n"
        "7. Be proactive in suggesting options but let the user make decisions\n"
        "8. When discussing flights and hotels, mention that you'll provide real-time options\n"
        "Your goal is to gather trip_context = {"
        "origin: [city name]"
        "destination: [city name]"
        "departure_date: [date in YYYY-MM-DD format]"
        "return_date: [date in YYYY-MM-DD format]"
        "interests: [interests]"
        "duration: [number only]"
        "}"
    )
    chat.send_message(instruction)
    return "Hi! I'm your travel planning assistant. I'd love to help you plan your perfect trip. Where would you like to go?"

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
        f"Break it down day by day. For each day, start with an emoji and a bolded title, e.g., 'Day 1: City Name'. "
        f"For each day, use bullet points for morning, afternoon, and evening activities. "
        f"Use clear section headers for each part of the day. "
        f"Format the entire itinerary as plain text with clear sections and bullet points. "
        f"Do NOT use HTML tags. "
        f"Return only the formatted text, no explanations. "
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
        html += "<li>" + f"<br>".join(flight.split('\n')) + "</li>"
    html += "</ul>"
    return html

def generate_hotels_html(destination, checkin, checkout):
    hotels = get_hotel_prices_with_links(destination, checkin, checkout)
    print(hotels)
    html = '<span>🏨 <strong>Hotel Options</strong></span><ul>'
    for hotel in hotels:
        html += "<li>" + "<br>".join(hotel.split('\n')) + "</li>"
    html += "</ul>"
    return html

def generate_tips_html(destination):
    prompt = (
        f"Give travel tips for {destination}. "
        "Start with an emoji and a bolded title for each section. "
        "List tips as bullet points. "
        "Use clear section headers for different types of tips. "
        "Format the entire response as plain text with clear sections and bullet points. "
        "Do NOT use HTML tags. "
        "Return only the formatted text, no explanations."
    )
    response = chat.send_message(prompt)
    return response.text

def is_greeting(text):
    """Check if the input is a greeting"""
    greeting_prompt = (
        "Determine if this is a greeting or introduction (like 'hello', 'hi', 'hey', etc.). "
        "Return 'yes' if it is, 'no' if it's not. "
        f"Text to check: {text}"
    )
    try:
        response = chat.send_message(greeting_prompt)
        return "yes" in response.text.lower()
    except Exception as e:
        print(f"Error checking greeting: {str(e)}")
        return False

def is_valid_city(text):
    """Check if the input could be a valid city name"""
    city_prompt = (
        "Determine if this could be a valid city name. "
        "Return 'yes' if it could be a city name, 'no' if it's definitely not. "
        "Consider common city names, but also allow for less common ones. "
        "Return 'no' for greetings, numbers, or clearly non-city words. "
        f"Text to check: {text}"
    )
    try:
        response = chat.send_message(city_prompt)
        return "yes" in response.text.lower()
    except Exception as e:
        print(f"Error checking city: {str(e)}")
        return False

def extract_trip_context(user_input):
    # Initialize context with current values
    context = trip_context.copy()
    
    # Check if this is a greeting
    if is_greeting(user_input):
        print("Detected greeting, not updating context")
        return context
    
    # Check if this might be a date
    if any(month in user_input.lower() for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
        print(f"Detected potential date input: {user_input}")
        normalized_date = normalize_date(user_input)
        if normalized_date != "invalid":
            # If we already have a departure date, this must be the return date
            if context["departure_date"]:
                context["return_date"] = normalized_date
                print(f"Updated return_date to {normalized_date}")
            else:
                context["departure_date"] = normalized_date
                print(f"Updated departure_date to {normalized_date}")
            return context
    
    # Use Gemini to extract information from user input
    extraction_prompt = (
        "Extract travel planning information from the user's message. "
        "Return a JSON object with the following fields if found: "
        "origin, destination, departure_date, return_date, budget, accommodation, interests, duration. "
        "Only include fields that are explicitly mentioned or can be reasonably inferred. "
        "For dates, understand natural language expressions like 'next week', 'in 2 months', 'end of summer', etc. "
        "Also handle various date formats like '28 aug', 'aug 28', '28th august', etc. "
        "Convert all dates to YYYY-MM-DD format. "
        "For budget, extract the numerical value. "
        "For duration, extract only the number. "
        "If a field is not mentioned, do not include it in the response. "
        "Format the response as a valid JSON object without any markdown formatting. "
        "If the message is just 'correct' or similar acknowledgment, return an empty JSON object. "
        "IMPORTANT: If the message is a single word or short phrase that could be a city name, and we already have a destination but no origin, treat it as the origin city. "
        f"User message: {user_input}"
    )
    
    try:
        response = chat.send_message(extraction_prompt)
        extracted_data = response.text.strip()
        print(f"Extracted data: {extracted_data}")
        
        # Remove any markdown formatting
        extracted_data = extracted_data.replace('```json', '').replace('```', '').strip()
        
        # Parse the JSON response
        try:
            data = json.loads(extracted_data)
            print(f"Parsed JSON data: {data}")
            
            # If the input is a single word or short phrase, check if it could be a city
            if not data and len(user_input.split()) <= 2:
                if is_valid_city(user_input):
                    # If we have a destination but no origin, treat this as origin
                    if context["destination"] and not context["origin"]:
                        data = {"origin": user_input.strip()}
                        print(f"Treated '{user_input}' as origin city")
                    # If we have no destination, treat this as destination
                    elif not context["destination"]:
                        data = {"destination": user_input.strip()}
                        print(f"Treated '{user_input}' as destination city")
                    else:
                        print(f"'{user_input}' could be a city but context is unclear")
            
            # Update context with extracted values
            for key in context:
                if key in data and data[key]:
                    if key == 'duration':
                        # Ensure duration is a string number
                        if str(data[key]).isdigit():
                            context[key] = str(data[key])
                            print(f"Updated {key} to {data[key]}")
                    elif key in ['departure_date', 'return_date']:
                        # Normalize dates
                        normalized_date = normalize_date(data[key])
                        if normalized_date != "invalid":
                            context[key] = normalized_date
                            print(f"Updated {key} to {normalized_date}")
                    else:
                        context[key] = str(data[key])
                        print(f"Updated {key} to {data[key]}")
            
            # If we have a departure date and duration, calculate return date
            if context["departure_date"] and context["duration"] and not context["return_date"]:
                context["return_date"] = calculate_return_date(context["departure_date"], context["duration"])
                print(f"Calculated return date: {context['return_date']}")
                
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {extracted_data}")
            print(f"JSON Error: {str(e)}")
            # If we can't parse the JSON and input could be a city
            if len(user_input.split()) <= 2 and is_valid_city(user_input):
                # If we have a destination but no origin, treat this as origin
                if context["destination"] and not context["origin"]:
                    context["origin"] = user_input.strip()
                    print(f"Treated '{user_input}' as origin city")
                # If we have no destination, treat this as destination
                elif not context["destination"]:
                    context["destination"] = user_input.strip()
                    print(f"Treated '{user_input}' as destination city")
            return context
            
        return context
    except Exception as e:
        print(f"Error extracting context: {str(e)}")
        # If there's an error and input could be a city
        if len(user_input.split()) <= 2 and is_valid_city(user_input):
            # If we have a destination but no origin, treat this as origin
            if context["destination"] and not context["origin"]:
                context["origin"] = user_input.strip()
                print(f"Treated '{user_input}' as origin city")
            # If we have no destination, treat this as destination
            elif not context["destination"]:
                context["destination"] = user_input.strip()
                print(f"Treated '{user_input}' as destination city")
        return context

def calculate_return_date(departure_date, duration):
    try:
        dep_date = datetime.strptime(departure_date, "%Y-%m-%d")
        ret_date = dep_date + timedelta(days=int(duration))
        return ret_date.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Error calculating return date: {str(e)}")
        return ""

def handle_follow_up(user_input):
    """Handle follow-up questions and modifications to the travel plan"""
    try:
        # Check if user wants to modify any part of the plan
        modification_prompt = (
            "Determine if the user wants to modify any part of their travel plan. "
            "Return 'yes' if they want to change something, 'no' if they're satisfied. "
            f"User message: {user_input}"
        )
        response = chat.send_message(modification_prompt)
        
        if "yes" in response.text.lower():
            # Ask what they want to modify
            return "What would you like to change in your travel plan? You can modify the destination, dates, duration, interests, or any other details."
        
        # If they're satisfied, ask if they want to book anything
        return "Great! Would you like me to help you book any of the flights or hotels I suggested?"
        
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}. Please try again."

def reset_trip_context():
    """Reset all trip context values to empty strings"""
    global trip_context
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
    print("Trip context has been reset")
    return "I've cleared the previous trip details. Let's plan a new trip! Where would you like to go?"

def is_reset_request(text):
    """Check if the user wants to reset/start a new trip"""
    reset_phrases = [
        "new trip",
        "start over",
        "reset",
        "clear",
        "plan another trip",
        "different trip",
        "let's plan something else"
    ]
    return any(phrase in text.lower() for phrase in reset_phrases)

def parse_user_intent(user_input):
    """Use Gemini to parse user intent and extract relevant information"""
    prompt = (
        "You are a travel planning assistant. Analyze this user message and return a JSON object with the following structure. "
        "IMPORTANT: Return ONLY the JSON object, no other text or explanation.\n"
        "{\n"
        "  'intent': 'greeting' | 'reset' | 'provide_info' | 'question' | 'continue',\n"
        "  'is_greeting': boolean,\n"
        "  'is_reset': boolean,\n"
        "  'extracted_info': {\n"
        "    'origin': string | null,\n"
        "    'destination': string | null,\n"
        "    'departure_date': string | null,\n"
        "    'return_date': string | null,\n"
        "    'duration': string | null,\n"
        "    'budget': string | null,\n"
        "    'interests': string | null,\n"
        "    'accommodation': string | null\n"
        "  },\n"
        "  'missing_info': string[],\n"
        "  'next_question': string\n"
        "}\n\n"
        "Rules:\n"
        "1. For dates, convert to YYYY-MM-DD format\n"
        "2. For intent detection:\n"
        "   - 'greeting': hello, hi, hey, etc.\n"
        "   - 'reset': new trip, start over, reset, clear, etc.\n"
        "   - 'provide_info': when user provides any trip details\n"
        "   - 'question': when user asks about the trip\n"
        "   - 'continue': when user wants to proceed with planning\n"
        "3. For missing_info, list only the required fields that are still missing\n"
        "4. For next_question, provide a natural follow-up question\n"
        "5. Maintain context from previous messages\n\n"
        f"Current trip context: {json.dumps(trip_context, indent=2)}\n\n"
        f"User message: {user_input}\n\n"
        "Return ONLY the JSON object, no other text."
    )
    
    try:
        response = chat.send_message(prompt)
        response_text = response.text.strip()
        
        # Clean up the response to ensure it's valid JSON
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        
        # If the response starts with a newline or whitespace, remove it
        response_text = response_text.lstrip()
        
        # If the response is empty or not valid JSON, return default response
        if not response_text:
            raise ValueError("Empty response from Gemini")
            
        parsed_data = json.loads(response_text)
        print(f"Parsed user intent: {parsed_data}")
        
        # Validate the parsed data has all required fields
        required_fields = ['intent', 'is_greeting', 'is_reset', 'extracted_info', 'missing_info', 'next_question']
        if not all(field in parsed_data for field in required_fields):
            raise ValueError("Missing required fields in parsed data")
            
        # Maintain existing context for fields that aren't being updated
        for key in trip_context:
            if key in parsed_data['extracted_info'] and parsed_data['extracted_info'][key] is None:
                parsed_data['extracted_info'][key] = trip_context[key]
            
        return parsed_data
        
    except Exception as e:
        print(f"Error parsing user intent: {str(e)}")
        # Return a default response based on the input and current context
        if user_input.lower() in ['hello', 'hi', 'hey', 'yo']:
            return {
                "intent": "greeting",
                "is_greeting": True,
                "is_reset": False,
                "extracted_info": {},
                "missing_info": ["destination"],
                "next_question": "Hi! I'm your travel planning assistant. Where would you like to go?"
            }
        elif len(user_input.split()) <= 2:  # Single word or short phrase
            if not trip_context["destination"]:
                return {
                    "intent": "provide_info",
                    "is_greeting": False,
                    "is_reset": False,
                    "extracted_info": {"destination": user_input.strip()},
                    "missing_info": ["origin"],
                    "next_question": f"Great! You want to visit {user_input.strip()}. Which city will you be traveling from?"
                }
            elif not trip_context["origin"]:
                return {
                    "intent": "provide_info",
                    "is_greeting": False,
                    "is_reset": False,
                    "extracted_info": {"origin": user_input.strip()},
                    "missing_info": ["departure_date"],
                    "next_question": "When would you like to start your trip?"
                }
            else:
                return {
                    "intent": "provide_info",
                    "is_greeting": False,
                    "is_reset": False,
                    "extracted_info": {},
                    "missing_info": ["departure_date"],
                    "next_question": "When would you like to start your trip?"
                }
        else:
            return {
                "intent": "provide_info",
                "is_greeting": False,
                "is_reset": False,
                "extracted_info": {},
                "missing_info": ["destination"],
                "next_question": "Where would you like to go?"
            }

def get_special_destination_airports(destination):
    """Get nearby airports for special destinations like national parks"""
    special_destinations = {
        "yellowstone": ["JAC", "BZN", "COD", "WYS"],  # Jackson Hole, Bozeman, Cody, West Yellowstone
        "yosemite": ["FAT", "MMH", "RNO"],  # Fresno, Mammoth Lakes, Reno
        "grand canyon": ["FLG", "GCN", "PHX"],  # Flagstaff, Grand Canyon, Phoenix
        "glacier": ["FCA", "GPI", "BZN"],  # Kalispell, Glacier Park, Bozeman
        "zion": ["CDC", "SGU", "LAS"],  # Cedar City, St. George, Las Vegas
        "rocky mountain": ["DEN", "BJC", "FNL"],  # Denver, Broomfield, Fort Collins
    }
    
    # Convert destination to lowercase and remove common words
    dest = destination.lower().replace("national park", "").replace("np", "").strip()
    return special_destinations.get(dest, [])

def get_alternative_routes(origin, destination, date):
    """Use Gemini to suggest alternative routes and connections"""
    # First, check if this is a special destination like a national park
    special_dest_prompt = (
        "You are a travel routing expert. Analyze this destination and determine if it's a special location "
        "like a national park, remote area, or tourist destination that might not have its own airport.\n"
        f"Destination: {destination}\n\n"
        "Return a JSON object with:\n"
        "{\n"
        "  'is_special_destination': boolean,\n"
        "  'type': 'national_park' | 'remote_area' | 'tourist_destination' | 'regular_city',\n"
        "  'nearby_airports': [list of relevant airport codes],\n"
        "  'explanation': 'brief explanation of why this is a special destination'\n"
        "}\n\n"
        "For example, for 'Yellowstone National Park', return:\n"
        "{\n"
        "  'is_special_destination': true,\n"
        "  'type': 'national_park',\n"
        "  'nearby_airports': ['JAC', 'BZN', 'COD', 'WYS'],\n"
        "  'explanation': 'Yellowstone is a national park with no commercial airport. Nearby airports serve different park entrances.'\n"
        "}\n\n"
        "Return ONLY the JSON object, no other text."
    )
    
    try:
        special_dest_response = chat.send_message(special_dest_prompt)
        special_dest_text = special_dest_response.text.strip()
        special_dest_text = special_dest_text.replace('```json', '').replace('```', '').strip()
        special_dest_info = json.loads(special_dest_text)
        print(f"Special destination analysis: {json.dumps(special_dest_info, indent=2)}")
        
        # Now get route suggestions based on whether it's a special destination
        if special_dest_info['is_special_destination']:
            prompt = (
                "You are a travel routing expert. Suggest alternative flight routes for this journey:\n"
                f"From: {origin}\n"
                f"To: {destination}\n"
                f"Date: {date}\n\n"
                f"This is a {special_dest_info['type']} with the following nearby airports: {special_dest_info['nearby_airports']}\n"
                f"{special_dest_info['explanation']}\n\n"
                "Return a JSON array of route suggestions in this format:\n"
                "[\n"
                "  {\n"
                "    'type': 'nearby_dest',\n"
                "    'origin': 'airport_code',\n"
                "    'destination': 'airport_code',\n"
                "    'reasoning': 'explanation of why this route makes sense',\n"
                "    'ground_transportation': 'details about getting to final destination'\n"
                "  }\n"
                "]\n\n"
                "For each nearby airport, explain:\n"
                "1. Which park entrance it serves\n"
                "2. Ground transportation options and duration\n"
                "3. Scenic value of the route\n"
                "4. Any seasonal considerations\n\n"
                "Return ONLY the JSON array, no other text."
            )
        else:
            prompt = (
                "You are a travel routing expert. Suggest alternative flight routes for this journey:\n"
                f"From: {origin}\n"
                f"To: {destination}\n"
                f"Date: {date}\n\n"
                "Consider:\n"
                "1. Nearby airports for both origin and destination\n"
                "2. Major hub airports that could serve as connections\n"
                "3. Common routing patterns for this type of journey\n\n"
                "Return a JSON array of route suggestions in this format:\n"
                "[\n"
                "  {\n"
                "    'type': 'direct' | 'nearby_origin' | 'nearby_dest' | 'hub_connection',\n"
                "    'origin': 'airport_code',\n"
                "    'destination': 'airport_code',\n"
                "    'hub': 'airport_code' (only for hub_connection),\n"
                "    'reasoning': 'explanation of why this route makes sense'\n"
                "  }\n"
                "]\n\n"
                "Return ONLY the JSON array, no other text."
            )
        
        response = chat.send_message(prompt)
        response_text = response.text.strip()
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        routes = json.loads(response_text)
        print(f"Gemini suggested routes: {json.dumps(routes, indent=2)}")
        return routes
    except Exception as e:
        print(f"Error getting alternative routes: {str(e)}")
        return []

def get_alternative_flights(origin, destination, date):
    """Get alternative flight options when direct flights aren't available"""
    try:
        # Resolve origin and destination to airport codes
        origin_code = resolve_city_to_code(origin)
        dest_code = resolve_city_to_code(destination)
        
        print(f"Resolved codes - Origin: {origin_code}, Destination: {dest_code}")
        
        # Get route suggestions from Gemini
        suggested_routes = get_alternative_routes(origin_code, dest_code, date)
        print(f"Got {len(suggested_routes)} suggested routes from Gemini")
        
        alternative_options = []
        
        for route in suggested_routes:
            print(f"Processing route: {json.dumps(route, indent=2)}")
            
            if route['type'] == 'direct':
                # Try direct flight
                flights = get_flight_prices_with_links(route['origin'], route['destination'], date)
                if flights:
                    alternative_options.append({
                        'type': 'direct',
                        'origin': route['origin'],
                        'destination': route['destination'],
                        'flights': flights,
                        'reasoning': route['reasoning']
                    })
            
            elif route['type'] == 'nearby_origin':
                # Try flights from nearby origin airport
                flights = get_flight_prices_with_links(route['origin'], route['destination'], date)
                if flights:
                    alternative_options.append({
                        'type': 'nearby_origin',
                        'airport': route['origin'],
                        'flights': flights,
                        'reasoning': route['reasoning']
                    })
            
            elif route['type'] == 'nearby_dest':
                # Try flights to nearby destination airport
                flights = get_flight_prices_with_links(route['origin'], route['destination'], date)
                if flights:
                    alternative_options.append({
                        'type': 'nearby_dest',
                        'airport': route['destination'],
                        'flights': flights,
                        'reasoning': route['reasoning'],
                        'ground_transportation': route.get('ground_transportation', '')
                    })
            
            elif route['type'] == 'hub_connection':
                # Try hub connection
                to_hub = get_flight_prices_with_links(route['origin'], route['hub'], date)
                if to_hub:
                    from_hub = get_flight_prices_with_links(route['hub'], route['destination'], date)
                    if from_hub:
                        alternative_options.append({
                            'type': 'hub_connection',
                            'hub': route['hub'],
                            'to_hub': to_hub,
                            'from_hub': from_hub,
                            'reasoning': route['reasoning']
                        })
        
        print(f"Found {len(alternative_options)} alternative options")
        return alternative_options
    except Exception as e:
        print(f"Error getting alternative flights: {str(e)}")
        return []

def get_ground_transportation(airport, destination):
    """Get ground transportation options from airport to destination"""
    # This would typically call an API or database
    # For now, we'll use a simplified version
    transportation = {
        "yellowstone": {
            "JAC": "2.5-hour drive to Yellowstone's South Entrance",
            "BZN": "1.5-hour drive to Yellowstone's North Entrance",
            "COD": "1-hour drive to Yellowstone's East Entrance",
            "WYS": "Direct access to Yellowstone's West Entrance"
        },
        "yosemite": {
            "FAT": "1.5-hour drive to Yosemite's South Entrance",
            "MMH": "Direct access to Yosemite's East Entrance",
            "RNO": "3-hour drive to Yosemite's East Entrance"
        }
    }
    
    # Convert destination to lowercase and remove common words
    dest = destination.lower().replace("national park", "").replace("np", "").strip()
    return transportation.get(dest, {}).get(airport, "Ground transportation available")

def get_region(airport_code):
    """Get the region for an airport code"""
    # This is a simplified version - you might want to use a proper airport database
    us_airports = ['SFO', 'LAX', 'JFK', 'ORD', 'ATL', 'DFW', 'DEN', 'SEA', 'LAS', 'MIA']
    eu_airports = ['LHR', 'CDG', 'FRA', 'AMS', 'MAD', 'FCO', 'MUC', 'ZRH', 'BCN', 'LIS']
    asia_airports = ['HKG', 'SIN', 'NRT', 'ICN', 'BKK', 'PEK', 'PVG', 'DEL', 'BOM', 'KUL']
    middle_east = ['DXB', 'AUH', 'DOH', 'RUH', 'TLV', 'CAI', 'IST']
    
    if airport_code in us_airports:
        return 'US'
    elif airport_code in eu_airports:
        return 'EU'
    elif airport_code in asia_airports:
        return 'ASIA'
    elif airport_code in middle_east:
        return 'MIDDLE_EAST'
    return 'OTHER'

def get_nearby_airports(airport_code):
    """Get nearby airports for a given airport code"""
    # This is a simplified version - you might want to use a proper airport database
    nearby_map = {
        'SFO': ['OAK', 'SJC'],
        'LAX': ['BUR', 'SNA', 'ONT'],
        'JFK': ['LGA', 'EWR'],
        'LHR': ['LGW', 'STN', 'LTN'],
        'CDG': ['ORY', 'BVA'],
        'FRA': ['HHN', 'CGN'],
        'AMS': ['RTM', 'EIN'],
        'HKG': ['MFM', 'CAN'],
        'SIN': ['KUL', 'BKK'],
        'NRT': ['HND', 'CTS']
    }
    return nearby_map.get(airport_code, [])

def format_alternative_options(alternatives):
    """Format alternative flight options into a readable string"""
    if not alternatives:
        return "No alternative flight options found."
    
    response = "Here are some alternative flight options:\n\n"
    
    for alt in alternatives:
        if alt['type'] == 'direct':
            response += f"✈️ Direct Flight Option:\n"
            response += f"  {alt['reasoning']}\n"
            for flight in alt['flights']:
                response += f"  • {flight}\n"
            response += "\n"
            
        elif alt['type'] == 'nearby_origin':
            response += f"✈️ Flights from nearby airport {alt['airport']}:\n"
            response += f"  {alt['reasoning']}\n"
            for flight in alt['flights']:
                response += f"  • {flight}\n"
            response += "\n"
            
        elif alt['type'] == 'nearby_dest':
            response += f"✈️ Flights to nearby airport {alt['airport']}:\n"
            response += f"  {alt['reasoning']}\n"
            for flight in alt['flights']:
                response += f"  • {flight}\n"
            if alt.get('ground_transportation'):
                response += f"  🚗 Ground Transportation: {alt['ground_transportation']}\n"
            response += "\n"
            
        elif alt['type'] == 'hub_connection':
            response += f"✈️ Multi-city option via {alt['hub']}:\n"
            response += f"  {alt['reasoning']}\n"
            response += "  First leg:\n"
            for flight in alt['to_hub']:
                response += f"    • {flight}\n"
            response += "  Second leg:\n"
            for flight in alt['from_hub']:
                response += f"    • {flight}\n"
            response += "\n"
    
    response += "Would you like to:\n"
    response += "1. Book any of these alternative flights\n"
    response += "2. Try different dates\n"
    response += "3. Look for other transportation options\n"
    
    return response

def create_rag_context(flights, hotels, weather, destination, duration, interests):
    """Create a context for RAG-based itinerary generation"""
    context = {
        "destination": destination,
        "duration": duration,
        "interests": interests,
        "flights": flights,
        "hotels": hotels,
        "weather": weather,
        "available_activities": get_available_activities(destination),
        "local_events": get_local_events(destination),
        "restaurant_recommendations": get_restaurant_recommendations(destination)
    }
    return context

def get_available_activities(destination):
    """Get available activities and attractions for the destination"""
    # This would typically call an API or database
    # For now, we'll use a simplified version
    activities = {
        "London": [
            "British Museum", "Tower of London", "Buckingham Palace",
            "London Eye", "Westminster Abbey", "Hyde Park"
        ],
        "Paris": [
            "Eiffel Tower", "Louvre Museum", "Notre-Dame",
            "Champs-Élysées", "Montmartre", "Seine River Cruise"
        ],
        # Add more destinations as needed
    }
    return activities.get(destination, [])

def get_local_events(destination):
    """Get local events and festivals for the destination"""
    # This would typically call an API or database
    # For now, we'll use a simplified version
    events = {
        "London": [
            "Changing of the Guard at Buckingham Palace",
            "West End Shows",
            "Portobello Road Market"
        ],
        "Paris": [
            "Eiffel Tower Light Show",
            "Louvre Night Opening",
            "Seine River Festival"
        ],
        # Add more destinations as needed
    }
    return events.get(destination, [])

def get_restaurant_recommendations(destination):
    """Get restaurant recommendations for the destination"""
    # This would typically call an API or database
    # For now, we'll use a simplified version
    restaurants = {
        "London": [
            "The Ivy", "Dishoom", "Sketch",
            "Hawksmoor", "The Wolseley"
        ],
        "Paris": [
            "Le Jules Verne", "L'Ami Louis",
            "Le Comptoir du Relais", "Septime"
        ],
        # Add more destinations as needed
    }
    return restaurants.get(destination, [])

def generate_rag_itinerary(context):
    """Generate a personalized itinerary using RAG"""
    prompt = (
        "Create a detailed travel itinerary based on the following context:\n\n"
        f"Destination: {context['destination']}\n"
        f"Duration: {context['duration']} days\n"
        f"Interests: {context['interests']}\n\n"
        "Flight Information:\n"
        f"{json.dumps(context['flights'], indent=2)}\n\n"
        "Hotel Options:\n"
        f"{json.dumps(context['hotels'], indent=2)}\n\n"
        "Weather Forecast:\n"
        f"{json.dumps(context['weather'], indent=2)}\n\n"
        "Available Activities:\n"
        f"{json.dumps(context['available_activities'], indent=2)}\n\n"
        "Local Events:\n"
        f"{json.dumps(context['local_events'], indent=2)}\n\n"
        "Restaurant Recommendations:\n"
        f"{json.dumps(context['restaurant_recommendations'], indent=2)}\n\n"
        "Please create a day-by-day itinerary that:\n"
        "1. Takes into account the weather forecast for each day\n"
        "2. Considers the user's interests and preferences\n"
        "3. Includes recommended restaurants near the activities\n"
        "4. Suggests indoor activities for rainy days\n"
        "5. Incorporates any special events happening during the stay\n"
        "6. Provides transportation tips between locations\n"
        "7. Includes estimated costs for activities\n"
        "8. Suggests the best times to visit popular attractions\n"
        "Format the response with clear day-by-day sections and include practical tips."
    )
    
    try:
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating RAG itinerary: {str(e)}")
        return "I apologize, but I'm having trouble generating a personalized itinerary at the moment."

def format_rag_response(itinerary, flights, hotels, weather):
    """Format the complete RAG-based response"""
    response = "Here's your personalized travel plan based on your preferences and real-time data:\n\n"
    
    # Add weather information
    response += "🌤️ Weather Forecast:\n"
    response += weather + "\n\n"
    
    # Add flight options
    if flights:
        response += "✈️ Flight Options:\n"
        for flight in flights:
            response += f"• {flight}\n"
        response += "\n"
    else:
        response += "✈️ Direct Flight Options:\n"
        response += f"• ❌ No direct flights found from {trip_context['origin']} to {trip_context['destination']} on {trip_context['departure_date']}\n\n"
        
        # Get alternative flight options
        response += "🔍 Checking alternative routes...\n\n"
        alternative_options = get_alternative_flights(
            trip_context["origin"],
            trip_context["destination"],
            trip_context["departure_date"]
        )
        
        if alternative_options:
            response += format_alternative_options(alternative_options)
        else:
            response += "❌ No alternative flight options found.\n"
            response += "Would you like to:\n"
            response += "1. Try different dates\n"
            response += "2. Look for other transportation options\n"
            response += "3. Consider a different destination\n\n"
    
    # Add hotel options
    if hotels:
        response += "🏨 Hotel Options:\n"
        for hotel in hotels:
            response += f"• {hotel}\n"
        response += "\n"
    else:
        response += "❌ No hotels found for your dates.\n\n"
    
    # Add personalized itinerary
    response += "📅 Your Personalized Itinerary:\n"
    response += "This itinerary is customized based on:\n"
    response += "• Your preferences and interests\n"
    response += "• Real-time weather forecasts\n"
    response += "• Available flights and hotels\n"
    response += "• Local events and activities\n"
    response += "• Restaurant recommendations\n\n"
    response += itinerary
    
    return response

def chat_with_gemini(user_input):
    try:
        # Parse user intent using Gemini
        parsed_intent = parse_user_intent(user_input)
        
        # Handle reset intent
        if parsed_intent["is_reset"]:
            return reset_trip_context()
        
        # Handle greeting intent
        if parsed_intent["is_greeting"]:
            return "Hi! I'm your travel planning assistant. Where would you like to go?"
        
        # Update trip context with extracted information
        if parsed_intent["extracted_info"]:
            for key, value in parsed_intent["extracted_info"].items():
                if value:
                    trip_context[key] = value
                    print(f"Updated trip_context[{key}] to {value}")
        
        print("\U0001F4E6 Current Trip Context:", trip_context)
        
        # Stage 1: Check if we have destination and duration
        if not trip_context["destination"]:
            return "Where would you like to go?"
            
        if not trip_context["duration"]:
            return f"How many days would you like to stay in {trip_context['destination']}?"
            
        # Stage 2: If we have destination and duration, ask for interests
        if not trip_context.get("interests"):
            return (
                f"Great! You want to visit {trip_context['destination']} for {trip_context['duration']} days. "
                "To create a personalized itinerary, please tell me about your interests and preferences. "
                "For example:\n"
                "• What activities do you enjoy? (e.g., museums, outdoor activities, food tours)\n"
                "• Any specific attractions you'd like to visit?\n"
                "• Do you prefer a relaxed or active pace?\n"
                "• Any dietary preferences or restrictions?"
            )
            
        # Stage 3: If we have interests, ask for dates and origin
        if not trip_context["departure_date"]:
            return "When would you like to start your trip? (Please provide a date)"
            
        if not trip_context["origin"]:
            return "Which city will you be traveling from?"
            
        # Stage 4: If we have all required information, generate the complete plan
        if trip_context["departure_date"] and trip_context["origin"]:
            # Calculate return date if we have duration
            if not trip_context["return_date"]:
                trip_context["return_date"] = calculate_return_date(
                    trip_context["departure_date"],
                    trip_context["duration"]
                )
            
            # Get flight options
            flights = get_flight_prices_with_links(
                trip_context["origin"],
                trip_context["destination"],
                trip_context["departure_date"]
            )
            
            # If no direct flights found, get alternative routes
            if not flights:
                print("No direct flights found, checking alternative routes...")
                alternative_options = get_alternative_flights(
                    trip_context["origin"],
                    trip_context["destination"],
                    trip_context["departure_date"]
                )
                
                if alternative_options:
                    print(f"Found {len(alternative_options)} alternative routes")
                    response = format_alternative_options(alternative_options)
                    return response
                else:
                    print("No alternative routes found")
            
            # Get hotel options
            hotels = get_hotel_prices_with_links(
                trip_context["destination"],
                trip_context["departure_date"],
                trip_context["return_date"]
            )
            
            # Get weather information
            try:
                departure_weather = get_weather_climatology(
                    trip_context["destination"],
                    trip_context["departure_date"]
                )
                return_weather = get_weather_climatology(
                    trip_context["destination"],
                    trip_context["return_date"]
                )
                weather_info = f"Departure: {departure_weather}\nReturn: {return_weather}"
                

                # Get weather information
                try:
                    departure_weather = get_weather_climatology(
                        trip_context["destination"],
                        trip_context["departure_date"]
                    )
                    return_weather = get_weather_climatology(
                        trip_context["destination"],
                        trip_context["return_date"]
                    )
                    
                    response_text = "Here's your complete travel plan:\n\n"
                    itinerary = generate_itinerary_html(
                            trip_context["destination"],
                            trip_context["duration"],
                            trip_context["interests"]
                        )
                    response_text = "Here's the itinerary for your trip:\n\n"
                    response_text += itinerary + "\n\n"
                    # Add weather information
                    response_text += "🌤️ Weather Forecast:\n\n"
                    response_text += departure_weather + "\n"
                    response_text += return_weather + "\n\n"
                    
                    # Add flight options
                    if flights:
                        response_text += "✈️ Flight Options:\n\n"
                        for flight in flights:
                            response_text += flight + "\n"
                        response_text += "\n"
                    else:
                        response_text += "❌ No direct flights found for your dates.\n\n"
                    
                    # Add hotel options
                    if hotels:
                        response_text += "🏨 Hotel Options:\n\n"
                        for hotel in hotels:
                            response_text += hotel + "\n"
                        response_text += "\n"
                    else:
                        response_text += "❌ No hotels found for your dates.\n\n"
                    
                    # Stage 4: Ask about interests for revised itinerary
                    if not trip_context.get("interests"):
                        response_text += "Please let me know your interests and preferences and I can customize the itinerary accordingly."
                    else:
                        # Stage 5: Generate revised itinerary with interests
                        revised_itinerary = generate_itinerary_html(
                            trip_context["destination"],
                            trip_context["duration"],
                            trip_context["interests"]
                        )
                        response_text += "Here's your revised itinerary based on your interests:\n\n"
                        response_text += revised_itinerary
                    
                    return response_text
                    
                except Exception as e:
                    print(f"Error fetching data: {str(e)}")
                    response_text += "❌ Unable to fetch some data at the moment.\n"
                    return response_text
        
        # If we don't have destination or duration, ask for them
        if not trip_context["destination"]:
            return "Where would you like to go?"
        if not trip_context["duration"]:
            return f"How many days would you like to stay in {trip_context['destination']}?"

        
        # If we're missing any required information, use Gemini's next question
        return parsed_intent["next_question"]
        
    except Exception as e:
        print(f"Error in chat_with_gemini: {str(e)}")
        return f"Sorry, I encountered an error: {str(e)}. Please try again with your travel details."

def main():
    print("\U0001F972 Travel Itinerary Chatbot with Memory\nType 'exit' to end the conversation.\n")
    initialize_chat()

    while True:
        user_input = input("\U0001F9D1 You: ")
        if user_input.lower() in ['exit', 'quit']:
            print("\U0001F44B Goodbye!")
            break

        # Check if we have a complete plan
        if all(trip_context.values()):
            reply = handle_follow_up(user_input)
        else:
            reply = chat_with_gemini(user_input)
            
        print(f"\U0001F916 Gemini: {reply}\n")

if __name__ == "__main__":
    main() 