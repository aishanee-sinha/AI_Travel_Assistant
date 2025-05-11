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
        "You are a friendly and interactive travel assistant. Your goal is to help users plan their trips "
        "by asking relevant questions and gathering necessary information. Follow these guidelines:\n"
        "1. Start by asking about their destination and travel dates\n"
        "2. Then ask about their interests and preferences\n"
        "3. Ask about their budget and accommodation preferences\n"
        "4. Finally, ask about their origin city for flight options\n"
        "Keep the conversation natural and engaging. Ask one question at a time and acknowledge their responses.\n"
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
    )
    chat.send_message(instruction)
    return "Hi! I'm your travel planning assistant. Where would you like to go?"

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
    
    # Only try to extract date if we don't have one yet
    if not context["departure_date"]:
        date_prompt = (
            "Given the current date and the user's message, determine the exact date they want to travel. "
            "If they mention a relative date (like 'next month'), calculate the actual date. "
            "If they mention a date without a year, use the current year. "
            "If there is no date information, return 'no_date'. "
            "Return ONLY the date in YYYY-MM-DD format or 'no_date', nothing else. "
            f"Current date: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"User message: {user_input}"
        )
        
        try:
            date_response = chat.send_message(date_prompt)
            departure_date = date_response.text.strip()
            
            if departure_date != 'no_date':
                # Validate the date
                try:
                    parsed_date = datetime.strptime(departure_date, '%Y-%m-%d')
                    # Don't allow dates more than 1 year in advance
                    max_date = datetime.now() + timedelta(days=365)
                    if parsed_date > max_date:
                        parsed_date = max_date
                    context["departure_date"] = parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    print(f"Invalid date format from Gemini: {departure_date}")
        except Exception as e:
            print(f"Error extracting date: {str(e)}")
    
    # If we're specifically asking for duration, use a focused prompt
    if not context["duration"] and context["departure_date"]:
        duration_prompt = (
            "Extract the number of days from the user's message. "
            "Return ONLY the number, nothing else. "
            "If no number is found, return 'no_duration'. "
            f"User message: {user_input}"
        )
        try:
            duration_response = chat.send_message(duration_prompt)
            duration = duration_response.text.strip()
            if duration.isdigit():
                context["duration"] = duration
                if context["departure_date"]:
                    context["return_date"] = calculate_return_date(context["departure_date"], context["duration"])
                return context
        except Exception as e:
            print(f"Error extracting duration: {str(e)}")
    
    # If we're specifically asking for origin city, use a focused prompt
    if not context["origin"] and context["destination"]:
        origin_prompt = (
            "The user is providing their starting city. "
            "Extract ONLY the city name from their message. "
            "Remove any words like 'city', 'town', etc. "
            "Return ONLY the city name, nothing else. "
            "If no city is found, return 'no_city'. "
            f"User message: {user_input}"
        )
        try:
            origin_response = chat.send_message(origin_prompt)
            origin = origin_response.text.strip()
            if origin and origin != 'no_city':
                context["origin"] = origin
                return context
        except Exception as e:
            print(f"Error extracting origin: {str(e)}")
    
    # For other information, use the general extraction prompt
    extraction_prompt = (
        "Extract travel information from the user's message. Be specific about:\n"
        "1. Destination: The city or place they want to visit\n"
        "2. Duration: Number of days they want to stay\n"
        "3. Origin: Their starting city\n"
        "4. Budget: Their budget range or preferences\n"
        "5. Accommodation: Their hotel preferences (luxury, budget, etc.)\n"
        "6. Interests: Their interests (culture, food, adventure, etc.)\n\n"
        "Return the result in this format:\n"
        "destination: [city name]\n"
        "duration: [number only]\n"
        "origin: [city name]\n"
        "budget: [amount]\n"
        "accommodation: [preference]\n"
        "interests: [interests]\n\n"
        f"User message: {user_input}"
    )
    
    try:
        extraction_response = chat.send_message(extraction_prompt)
        extracted = extraction_response.text.strip()
        
        # Parse the extracted information
        for line in extracted.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key in context and value:
                    if key == 'duration':
                        if value.isdigit():
                            context[key] = value
                            if context["departure_date"]:
                                context["return_date"] = calculate_return_date(context["departure_date"], context["duration"])
                    elif key == 'origin':
                        context[key] = value
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

def chat_with_gemini(user_input):
    try:
        # Extract trip context from user input while maintaining previous context
        extracted_context = extract_trip_context(user_input)
        
        # Update trip context with extracted values
        for key in trip_context:
            if extracted_context[key]:
                trip_context[key] = extracted_context[key]

        print("\U0001F4E6 Current Trip Context:", trip_context)

        # If this is the first message, start with a friendly greeting
        if not any(trip_context.values()):
            return "Hi! I'm your travel planning assistant. I'd love to help you plan your trip. Where would you like to go?"

        # Define priority order for information gathering
        priority_order = ["destination", "departure_date", "duration", "origin", "interests", "budget", "accommodation"]
        
        # Check what information we have and what we need next
        for info in priority_order:
            if not trip_context[info]:
                # Create a friendly, specific question based on what we need
                if info == "destination":
                    return "Where would you like to go for your trip?"
                elif info == "departure_date":
                    return "When would you like to start your trip? You can say something like 'next month' or give a specific date."
                elif info == "duration":
                    return "How many days would you like to stay?"
                elif info == "origin":
                    return "Which city will you be traveling from?"
                elif info == "interests":
                    return "What are your interests? For example, are you interested in culture, food, shopping, or something else?"
                elif info == "budget":
                    return "What's your budget for this trip? Are you looking for luxury, mid-range, or budget options?"
                elif info == "accommodation":
                    return "What type of accommodation do you prefer? For example, hotels, hostels, or vacation rentals?"

        # If we have all information, provide a complete plan
        if all(trip_context.values()):
            # Get flight options
            origin_code = resolve_city_to_code(trip_context["origin"])
            destination_code = resolve_city_to_code(trip_context["destination"])
            flights = get_flight_prices_with_links(
                origin_code, destination_code, trip_context["departure_date"]
            )
            
            # Get hotel options
            hotels = get_hotel_prices_with_links(
                trip_context["destination"],
                trip_context["departure_date"],
                trip_context["return_date"],
            )
            
            # Generate itinerary
            itinerary = generate_itinerary(trip_context["destination"], trip_context["duration"], trip_context["interests"])
            
            return (
                f"Perfect! I've prepared a complete travel plan for your trip to {trip_context['destination']}:\n\n"
                f"Flight options from {trip_context['origin']} to {trip_context['destination']}:\n\n" + "\n".join(flights) + "\n\n"
                f"Hotel options in {trip_context['destination']}:\n\n" + "\n".join(hotels) + "\n\n"
                f"{trip_context['duration']}-day itinerary:\n\n{itinerary}\n\n"
                "Would you like to make any changes to this plan?"
            )

        # If we have partial information, provide what we can and ask for more
        response = ""
        if trip_context["destination"] and trip_context["duration"]:
            itinerary = generate_itinerary(trip_context["destination"], trip_context["duration"], trip_context["interests"])
            response += f"Great! I've started planning your {trip_context['duration']}-day trip to {trip_context['destination']}.\n\n"
            response += f"Here's a preliminary itinerary:\n\n{itinerary}\n\n"
        
        if trip_context["destination"] and trip_context["departure_date"]:
            hotels = get_hotel_prices_with_links(
                trip_context["destination"],
                trip_context["departure_date"],
                trip_context["return_date"],
            )
            response += f"I've found some hotel options for your stay:\n\n" + "\n".join(hotels) + "\n\n"
        
        # Find the next piece of information we need
        for info in priority_order:
            if not trip_context[info]:
                if info == "departure_date":
                    response += "When would you like to start your trip? You can say something like 'next month' or give a specific date."
                elif info == "duration":
                    response += "How many days would you like to stay?"
                elif info == "origin":
                    response += "Which city will you be traveling from?"
                elif info == "interests":
                    response += "What are your interests? For example, are you interested in culture, food, shopping, or something else?"
                elif info == "budget":
                    response += "What's your budget for this trip? Are you looking for luxury, mid-range, or budget options?"
                elif info == "accommodation":
                    response += "What type of accommodation do you prefer? For example, hotels, hostels, or vacation rentals?"
                break
        
        return response

    except Exception as e:
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