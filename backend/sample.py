from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import re
from amadeus import Client, ResponseError
from amadeus_api import get_flight_prices_with_links, resolve_city_to_code
from hotel_api import get_hotel_prices_with_links
import google.generativeai as genai
from dateutil import parser
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io

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
        # First try direct parsing with dateutil
        try:
            parsed_date = parser.parse(date_str)
            formatted_date = parsed_date.strftime('%Y-%m-%d')
            print(f"Successfully parsed date '{date_str}' to '{formatted_date}' using dateutil")
            return formatted_date
        except Exception as e:
            print(f"Direct parsing failed for '{date_str}': {str(e)}")

        # If direct parsing fails, try using Gemini
        prompt = (
            "Convert this date to YYYY-MM-DD format. "
            "If the year is not specified, use the current year. "
            "If the date is ambiguous or invalid, return 'invalid'. "
            "For seasons like 'summer', use the start of that season in the current year. "
            "Handle abbreviated months (e.g., 'aug' for August, 'jan' for January). "
            "Handle various date formats like '28 aug', 'aug 28', '28th august', etc. "
            "Return ONLY the date in YYYY-MM-DD format, nothing else. "
            f"Date to normalize: {date_str}"
        )
        response = chat.send_message(prompt)
        normalized_date = response.text.strip()
        print(f"Gemini normalized '{date_str}' to '{normalized_date}'")
        
        # Validate the normalized date
        try:
            parsed_date = parser.parse(normalized_date)
            formatted_date = parsed_date.strftime('%Y-%m-%d')
            print(f"Successfully validated normalized date '{normalized_date}' to '{formatted_date}'")
            return formatted_date
        except Exception as e:
            print(f"Error validating normalized date '{normalized_date}': {str(e)}")
            return "invalid"
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
        "budget: [amount]"
        "accommodation: [preference]"
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

def generate_itinerary_pdf(itinerary_text, destination, duration):
    """Generate a PDF file from the itinerary text or any message text"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.HexColor('#2c3e50')
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=20,
        textColor=colors.HexColor('#34495e')
    )
    
    day_style = ParagraphStyle(
        'DayStyle',
        parent=styles['Heading2'],
        fontSize=18,
        spaceAfter=15,
        spaceBefore=20,
        textColor=colors.HexColor('#2980b9')
    )
    
    content_style = ParagraphStyle(
        'ContentStyle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=8,
        leftIndent=20,
        textColor=colors.HexColor('#2c3e50')
    )
    
    activity_style = ParagraphStyle(
        'ActivityStyle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=8,
        leftIndent=20,
        textColor=colors.HexColor('#2c3e50')
    )
    
    story = []

    # Determine if this is an itinerary (contains "Day X:" pattern) or a regular message
    is_itinerary = any(line.strip().startswith("Day") for line in itinerary_text.split('\n'))
    
    # Title
    if is_itinerary:
        story.append(Paragraph(f"Travel Itinerary for {destination}", title_style))
    else:
        story.append(Paragraph(f"Travel Information: {destination}", title_style))
    story.append(Spacer(1, 20))
    
    # Info Summary
    story.append(Paragraph("Summary", subtitle_style))
    summary_data = [
        ["Topic:", destination],
    ]
    
    if is_itinerary:
        summary_data.append(["Duration:", f"{duration} days"])
    
    summary_data.append(["Generated on:", datetime.now().strftime("%Y-%m-%d")])
    
    summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
    summary_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 30))

    # Process text differently based on type
    if is_itinerary:
        # Process itinerary text
        lines = itinerary_text.split('\n')
        current_day = None
        current_activities = []
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('Day'):
                # If we have activities from previous day, add them
                if current_day and current_activities:
                    story.append(Paragraph(current_day, day_style))
                    for activity in current_activities:
                        story.append(Paragraph(f"• {activity}", activity_style))
                    story.append(Spacer(1, 12))
                
                current_day = line
                current_activities = []
                current_section = None
            elif any(section in line.lower() for section in ['morning', 'afternoon', 'evening']):
                if current_section:
                    story.append(Spacer(1, 6))
                current_section = line
                story.append(Paragraph(current_section, subtitle_style))
            else:
                current_activities.append(line)

        # Add the last day's activities
        if current_day and current_activities:
            story.append(Paragraph(current_day, day_style))
            for activity in current_activities:
                story.append(Paragraph(f"• {activity}", activity_style))
    else:
        # Process generic message text
        story.append(Paragraph("Content", subtitle_style))
        
        # Split by paragraphs and add
        paragraphs = itinerary_text.split('\n')
        for paragraph in paragraphs:
            if paragraph.strip():
                # Check if line might be a heading (shorter lines with no punctuation)
                if len(paragraph) < 50 and not any(p in paragraph for p in ['.', ',', ':', ';']):
                    story.append(Paragraph(paragraph, subtitle_style))
                else:
                    story.append(Paragraph(paragraph, content_style))
                story.append(Spacer(1, 8))

    # Add footer
    story.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#7f8c8d'),
        alignment=1  # Center alignment
    )
    story.append(Paragraph("Generated by AI Travel Assistant", footer_style))
    story.append(Paragraph(f"© {datetime.now().year} Travelit.Ai", footer_style))

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

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
        
        # Check if we have all required information
        required_fields = ["origin", "destination", "departure_date"]
        has_all_required = all(trip_context[field] for field in required_fields)
        
        if has_all_required:
            # Check if we have either return date or duration
            if not trip_context["return_date"] and not trip_context["duration"]:
                return "Would you like to specify your return date or trip duration? (e.g., 'return on 28 june' or 'stay for 7 days')"
            
            # Check if we have all optional information
            optional_fields = ["budget", "interests", "accommodation"]
            has_all_optional = all(trip_context[field] for field in optional_fields)
            
            if not has_all_optional:
                # Use Gemini's next question
                return parsed_intent["next_question"]
            else:
                # We have all information, generate the complete plan
                try:
                    # Calculate return date if we have duration but no return date
                    if trip_context["duration"] and not trip_context["return_date"]:
                        trip_context["return_date"] = calculate_return_date(trip_context["departure_date"], trip_context["duration"])
                        print(f"Calculated return date: {trip_context['return_date']}")
                    
                    # Get flight options
                    flights = get_flight_prices_with_links(
                        trip_context["origin"],
                        trip_context["destination"],
                        trip_context["departure_date"]
                    )
                    
                    # Build complete response
                    response_text = "Here's your complete travel plan:\n\n"
                    
                    # Add flights
                    if flights:
                        response_text += "✈️ Flight Options:\n\n"
                        for flight in flights:
                            response_text += flight + "\n"
                        response_text += "\n"
                    else:
                        # No flights found - provide alternative options
                        response_text += "✈️ Flight Options:\n\n"
                        response_text += "❌ No direct flights found from {} to {} on {}.\n\n".format(
                            trip_context["origin"],
                            trip_context["destination"],
                            trip_context["departure_date"]
                        )
                        response_text += "Here are some alternative options:\n\n"
                        response_text += "1. Try nearby airports:\n"
                        response_text += "   - For {}: Consider alternative airports in the region\n".format(trip_context["origin"])
                        response_text += "   - For {}: Check if there are other airports serving the area\n\n".format(trip_context["destination"])
                        response_text += "2. Adjust your dates:\n"
                        response_text += "   - Try dates a few days before or after your planned departure\n"
                        response_text += "   - Consider different seasons for better availability\n\n"
                        response_text += "3. Alternative routes:\n"
                        response_text += "   - Look for connecting flights through major hubs\n"
                        response_text += "   - Consider multi-city options\n\n"
                        response_text += "4. Other transportation options:\n"
                        response_text += "   - Check train services if available\n"
                        response_text += "   - Look into bus services for regional travel\n"
                        response_text += "   - Consider car rental options\n\n"
                        response_text += "Would you like me to:\n"
                        response_text += "1. Search for flights on alternative dates?\n"
                        response_text += "2. Look for flights from/to nearby airports?\n"
                        response_text += "3. Search for connecting flights?\n"
                        response_text += "4. Continue with the rest of the plan?\n\n"
                    
                    # Get hotel options
                    hotels = get_hotel_prices_with_links(
                        trip_context["destination"],
                        trip_context["departure_date"],
                        trip_context["return_date"]
                    )
                    
                    # Add hotels
                    if hotels:
                        response_text += "🏨 Hotel Options:\n\n"
                        for hotel in hotels:
                            response_text += hotel + "\n"
                        response_text += "\n"
                    else:
                        response_text += "🏨 Hotel Options:\n\n"
                        response_text += "❌ No hotels found for your dates. Consider:\n"
                        response_text += "1. Adjusting your travel dates\n"
                        response_text += "2. Looking for accommodations in nearby areas\n"
                        response_text += "3. Checking alternative booking platforms\n\n"
                    
                    # Generate itinerary
                    itinerary = generate_itinerary_html(
                        trip_context["destination"],
                        trip_context["duration"] or "7",  # Default to 7 days if duration not specified
                        trip_context["interests"]
                    )
                    
                    # Generate travel tips
                    tips = generate_tips_html(trip_context["destination"])
                    
                    # Add itinerary
                    response_text += "📅 Your Itinerary:\n\n" + itinerary + "\n\n"
                    
                    # Add travel tips
                    response_text += "💡 Travel Tips:\n\n" + tips
                    
                    # Check if user wants to save as PDF
                    if "yes" in user_input.lower():
                        pdf_buffer = generate_itinerary_pdf(itinerary, trip_context["destination"], trip_context["duration"])
                        return {
                            "type": "pdf",
                            "data": pdf_buffer.getvalue(),
                            "filename": f"itinerary_{trip_context['destination']}_{trip_context['departure_date']}.pdf"
                        }
                    
                except Exception as e:
                    print(f"Error getting real-time data: {str(e)}")
                    response_text = "I apologize, but I'm having trouble fetching real-time flight and hotel options at the moment."
        else:
            # Use Gemini's next question for missing information
            return parsed_intent["next_question"]
        
        return response_text
        
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