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

def get_alternative_flights(origin, destination, date):
    """Get alternative flight options when direct flights aren't available"""
    try:
        # Get nearby airports for origin and destination
        origin_code = resolve_city_to_code(origin)
        dest_code = resolve_city_to_code(destination)
        
        # Common major hub airports
        major_hubs = {
            'US': ['JFK', 'LAX', 'ORD', 'ATL', 'DFW'],
            'EU': ['LHR', 'CDG', 'FRA', 'AMS', 'MAD'],
            'ASIA': ['HKG', 'SIN', 'NRT', 'ICN', 'BKK'],
            'MIDDLE_EAST': ['DXB', 'AUH', 'DOH']
        }
        
        # Get region for origin and destination
        origin_region = get_region(origin_code)
        dest_region = get_region(dest_code)
        
        # Get nearby airports
        nearby_origin = get_nearby_airports(origin_code)
        nearby_dest = get_nearby_airports(dest_code)
        
        alternative_options = []
        
        # 1. Try nearby airports for origin
        for nearby in nearby_origin:
            flights = get_flight_prices_with_links(nearby, dest_code, date)
            if flights:
                alternative_options.append({
                    'type': 'nearby_origin',
                    'airport': nearby,
                    'flights': flights
                })
        
        # 2. Try nearby airports for destination
        for nearby in nearby_dest:
            flights = get_flight_prices_with_links(origin_code, nearby, date)
            if flights:
                alternative_options.append({
                    'type': 'nearby_dest',
                    'airport': nearby,
                    'flights': flights
                })
        
        # 3. Try major hub connections
        relevant_hubs = []
        if origin_region in major_hubs:
            relevant_hubs.extend(major_hubs[origin_region])
        if dest_region in major_hubs:
            relevant_hubs.extend(major_hubs[dest_region])
        
        for hub in relevant_hubs:
            # Check if we can fly to the hub
            to_hub = get_flight_prices_with_links(origin_code, hub, date)
            if to_hub:
                # Check if we can fly from hub to destination
                from_hub = get_flight_prices_with_links(hub, dest_code, date)
                if from_hub:
                    alternative_options.append({
                        'type': 'hub_connection',
                        'hub': hub,
                        'to_hub': to_hub,
                        'from_hub': from_hub
                    })
        
        return alternative_options
    except Exception as e:
        print(f"Error getting alternative flights: {str(e)}")
        return []

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
        if alt['type'] == 'nearby_origin':
            response += f"✈️ Flights from nearby airport {alt['airport']}:\n"
            for flight in alt['flights']:
                response += f"  • {flight}\n"
            response += "\n"
            
        elif alt['type'] == 'nearby_dest':
            response += f"✈️ Flights to nearby airport {alt['airport']}:\n"
            for flight in alt['flights']:
                response += f"  • {flight}\n"
            response += "\n"
            
        elif alt['type'] == 'hub_connection':
            response += f"✈️ Multi-city option via {alt['hub']}:\n"
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

def create_rag_context(flight_data, hotel_data, weather_data, destination, duration, interests):
    """Create a context for RAG-based itinerary generation"""
    context = {
        "destination": destination,
        "duration": duration,
        "interests": interests,
        "flight_info": {
            "arrival_time": None,
            "departure_time": None,
            "airline": None
        },
        "hotel_info": {
            "location": None,
            "price_range": None,
            "amenities": []
        },
        "weather_info": {
            "temperature": None,
            "conditions": None,
            "forecast": []
        }
    }
    
    # Extract flight information
    if flight_data:
        try:
            # Get the first flight option
            first_flight = flight_data[0]
            flight_parts = first_flight.split('\n')
            for part in flight_parts:
                if '→' in part:
                    times = part.split('→')[1].strip()
                    context["flight_info"]["arrival_time"] = times.split('-')[0].strip()
                if '$' in part:
                    context["flight_info"]["airline"] = part.split('-')[0].strip()
        except Exception as e:
            print(f"Error parsing flight data: {str(e)}")
    
    # Extract hotel information
    if hotel_data:
        try:
            # Get the first hotel option
            first_hotel = hotel_data[0]
            hotel_parts = first_hotel.split('\n')
            for part in hotel_parts:
                if '$' in part:
                    context["hotel_info"]["price_range"] = part.split('$')[1].split()[0]
                if 'stars' in part.lower():
                    context["hotel_info"]["amenities"].append(part.strip())
        except Exception as e:
            print(f"Error parsing hotel data: {str(e)}")
    
    # Extract weather information
    if weather_data:
        try:
            weather_parts = weather_data.split('\n')
            for part in weather_parts:
                if '°C' in part or '°F' in part:
                    context["weather_info"]["temperature"] = part.strip()
                if any(condition in part.lower() for condition in ['sunny', 'rainy', 'cloudy', 'clear']):
                    context["weather_info"]["conditions"] = part.strip()
                if 'forecast' in part.lower():
                    context["weather_info"]["forecast"].append(part.strip())
        except Exception as e:
            print(f"Error parsing weather data: {str(e)}")
    
    return context

def generate_rag_itinerary(context):
    """Generate a personalized itinerary using RAG context"""
    prompt = (
        f"Create a detailed {context['duration']}-day itinerary for {context['destination']} "
        f"considering the following real-time information:\n\n"
        f"Flight Information:\n"
        f"- Arrival Time: {context['flight_info']['arrival_time']}\n"
        f"- Airline: {context['flight_info']['airline']}\n\n"
        f"Hotel Information:\n"
        f"- Price Range: {context['hotel_info']['price_range']}\n"
        f"- Amenities: {', '.join(context['hotel_info']['amenities'])}\n\n"
        f"Weather Information:\n"
        f"- Current Conditions: {context['weather_info']['conditions']}\n"
        f"- Temperature: {context['weather_info']['temperature']}\n"
        f"- Forecast: {', '.join(context['weather_info']['forecast'])}\n\n"
        f"User Interests: {context['interests']}\n\n"
        "Please create a day-by-day itinerary that:\n"
        "1. Accounts for arrival/departure times\n"
        "2. Suggests activities suitable for the weather conditions\n"
        "3. Recommends attractions near the hotel location\n"
        "4. Includes indoor alternatives for bad weather\n"
        "5. Considers the user's interests\n"
        "6. Provides realistic timing for each activity\n"
        "7. Includes transportation options between locations\n"
        "8. Suggests restaurants and dining options\n\n"
        "Format the response with clear day sections, morning/afternoon/evening activities, "
        "and include practical tips for each day."
    )
    
    try:
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating RAG itinerary: {str(e)}")
        return None

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
        if trip_context["destination"] and trip_context["duration"]:
            # Generate initial itinerary
            itinerary = generate_itinerary_html(
                trip_context["destination"],
                trip_context["duration"],
                trip_context.get("interests", "")
            )
            
            response_text = "Here's a general itinerary for your trip:\n\n"
            response_text += itinerary + "\n\n"
            
            # If we don't have dates and origin, ask for them
            if not trip_context["departure_date"] or not trip_context["origin"]:
                response_text += "Would you like to see flight and hotel options? Please provide your travel dates and origin city."
                return response_text
            
            # Stage 2: If we have dates but no origin
            if trip_context["departure_date"] and not trip_context["origin"]:
                # Calculate return date if we have duration
                if not trip_context["return_date"]:
                    trip_context["return_date"] = calculate_return_date(
                        trip_context["departure_date"],
                        trip_context["duration"]
                    )
                
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
                    
                    response_text = "Here's what I found for your trip:\n\n"
                    response_text += "🌤️ Weather Forecast:\n\n"
                    response_text += departure_weather + "\n"
                    response_text += return_weather + "\n\n"
                    
                    if hotels:
                        response_text += "🏨 Hotel Options:\n\n"
                        for hotel in hotels:
                            response_text += hotel + "\n"
                    else:
                        response_text += "❌ No hotels found for your dates.\n"
                    
                    response_text += "\nTo see flight options, please provide your origin city."
                    return response_text
                    
                except Exception as e:
                    print(f"Error fetching data: {str(e)}")
                    response_text += "❌ Unable to fetch some data at the moment.\n"
                    response_text += "To see flight options, please provide your origin city."
                    return response_text
            
            # Stage 3: If we have all required information
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
                    
                    # Create RAG context
                    rag_context = create_rag_context(
                        flights,
                        hotels,
                        departure_weather,
                        trip_context["destination"],
                        trip_context["duration"],
                        trip_context.get("interests", "")
                    )
                    
                    # Generate RAG-based itinerary
                    rag_itinerary = generate_rag_itinerary(rag_context)
                    
                    response_text = "Here's your complete travel plan:\n\n"
                    
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
                        # Try to get alternative flight options
                        alternative_options = get_alternative_flights(
                            trip_context["origin"],
                            trip_context["destination"],
                            trip_context["departure_date"]
                        )
                        
                        if alternative_options:
                            response_text += format_alternative_options(alternative_options)
                        else:
                            response_text += "❌ No direct flights found for your dates.\n"
                            response_text += "Would you like to:\n"
                            response_text += "1. Try different dates\n"
                            response_text += "2. Look for other transportation options\n"
                            response_text += "3. Consider a different destination\n"
                    
                    # Add hotel options
                    if hotels:
                        response_text += "🏨 Hotel Options:\n\n"
                        for hotel in hotels:
                            response_text += hotel + "\n"
                        response_text += "\n"
                    else:
                        response_text += "❌ No hotels found for your dates.\n\n"
                    
                    # Add RAG-based itinerary
                    if rag_itinerary:
                        response_text += "📅 Your Personalized Itinerary:\n\n"
                        response_text += rag_itinerary + "\n\n"
                    else:
                        # Fallback to basic itinerary if RAG fails
                        basic_itinerary = generate_itinerary_html(
                            trip_context["destination"],
                            trip_context["duration"],
                            trip_context.get("interests", "")
                        )
                        response_text += "�� Your Itinerary:\n\n"
                        response_text += basic_itinerary + "\n\n"
                    
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
        
        return "I need more information to help plan your trip. Please provide your destination and duration of stay."
        
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