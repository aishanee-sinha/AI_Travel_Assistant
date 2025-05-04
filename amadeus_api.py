from dotenv import load_dotenv
import os
from amadeus import Client, ResponseError
import google.generativeai as genai
from datetime import datetime
import re
load_dotenv()

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("models/gemini-1.5-flash-latest")

amadeus = Client(
    client_id=os.getenv("AMADEUS_API_KEY"),
    client_secret=os.getenv("AMADEUS_API_SECRET")
)

def normalize_date_for_flights(date_str):
    """Normalize date string to YYYY-MM-DD format for Amadeus API"""
    try:
        # If already in YYYY-MM-DD format, return as is
        if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return date_str
            
        # Try parsing with different formats
        date_formats = [
            '%Y-%m-%d', '%d-%m-%Y', '%m-%d-%Y',
            '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y',
            '%Y.%m.%d', '%d.%m.%Y', '%m.%d.%Y'
        ]
        
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
                
        # If all parsing fails, try Gemini
        prompt = (
            "Convert this date to YYYY-MM-DD format. "
            "If the year is not specified, use the current year. "
            "Return ONLY the date in YYYY-MM-DD format, nothing else. "
            f"Date: {date_str}"
        )
        response = model.generate_content(prompt)
        normalized_date = response.text.strip()
        
        # Validate the normalized date
        if re.match(r'^\d{4}-\d{2}-\d{2}$', normalized_date):
            return normalized_date
            
        raise ValueError("Invalid date format")
        
    except Exception as e:
        print(f"❌ Error normalizing date '{date_str}': {e}")
        raise ValueError(f"Invalid date format: {date_str}")

def get_iata_code_with_gemini(city_name):
    try:
        prompt = (
            "Given a city name, return ONLY the IATA code of its main international airport. "
            "If the city has multiple airports, choose the main international one. "
            "Return ONLY the 3-letter code, nothing else. "
            f"City: {city_name}"
        )
        response = model.generate_content(prompt)
        iata_code = response.text.strip().upper()
        
        # Validate the IATA code format
        if len(iata_code) == 3 and iata_code.isalpha():
            return iata_code
        else:
            print(f"⚠️ Invalid IATA code format from Gemini for '{city_name}', using fallback")
            return city_name.replace(" ", "")[:3].upper()
    except Exception as e:
        print(f"❌ Error getting IATA code from Gemini: {e}")
        return city_name.replace(" ", "")[:3].upper()

def resolve_city_to_code(city_name):
    try:
        # Clean the city name
        city_name = city_name.strip().title()
        
        # First try Gemini for IATA code
        iata_code = get_iata_code_with_gemini(city_name)
        
        # Verify the code with Amadeus
        try:
            response = amadeus.reference_data.locations.get(
                keyword=iata_code,
                subType='CITY,AIRPORT'
            )
            if response.data and len(response.data) > 0:
                return iata_code
        except ResponseError:
            pass
        
        # If verification fails, try Amadeus search as fallback
        response = amadeus.reference_data.locations.get(
            keyword=city_name,
            subType='CITY,AIRPORT'
        )
        
        if response.data and len(response.data) > 0:
            for location in response.data:
                if location.get("subType") == "CITY":
                    return location["iataCode"]
            return response.data[0]["iataCode"]
        
        print(f"⚠️ No IATA code found for '{city_name}', using fallback")
        return iata_code  # Use the Gemini-generated code as fallback
        
    except ResponseError as error:
        print(f"❌ City lookup error: {error}")
        return get_iata_code_with_gemini(city_name)  # Fallback to Gemini

def get_flight_prices_with_links(origin, destination, date):
    try:
        # Validate inputs
        if not origin or not destination or not date:
            return ["❌ Missing required information for flight search"]
            
        # Normalize the date to YYYY-MM-DD format
        try:
            normalized_date = normalize_date_for_flights(date)
        except ValueError as e:
            return [f"❌ Invalid date format: {date}. Please use YYYY-MM-DD format."]
            
        # Get IATA codes using Gemini
        origin_code = resolve_city_to_code(origin)
        destination_code = resolve_city_to_code(destination)
        
        print(f"🔍 Searching flights: {origin_code} → {destination_code} on {normalized_date}")
        
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin_code,
            destinationLocationCode=destination_code,
            departureDate=normalized_date,
            adults=1,
            max=3,
            currencyCode="USD"
        )
        
        if not response.data:
            return [f"❌ No flights found from {origin_code} to {destination_code} on {normalized_date}"]
            
        results = response.data
        formatted = []

        for i, offer in enumerate(results[:3]):
            segments = offer["itineraries"][0]["segments"]
            first = segments[0]["departure"]
            last = segments[-1]["arrival"]
            price = offer["price"]["total"]
            airline = offer["validatingAirlineCodes"][0]
            duration = offer["itineraries"][0]["duration"].replace("PT", "").lower()

            link = f"https://www.google.com/flights?hl=en#flt={origin_code}.{destination_code}.{normalized_date};c:USD;e:1;sd:1;t:f"

            formatted.append(
                f"{i+1}. {airline} – ${price}\n"
                f"   🕐 Duration: {duration}\n"
                f"   🛫 Departs: {first['at']} from {first['iataCode']}\n"
                f"   🛬 Arrives: {last['at']} at {last['iataCode']}\n"
                f"   🔗 [Book here]({link})"
            )

        return [f"✈️ Flight Options ({origin_code} → {destination_code} on {normalized_date}):\n\n"] + formatted

    except ResponseError as error:
        error_msg = str(error)
        if "400" in error_msg:
            return [f"❌ Invalid request: Please check if the cities and date are valid"]
        elif "401" in error_msg:
            return [f"❌ Authentication error: Please check API credentials"]
        elif "404" in error_msg:
            return [f"❌ No flights found for the specified route"]
        else:
            return [f"❌ Flight API error: {error_msg}"]




def get_hotel_prices(city_code, check_in, check_out):
    try:
        response = amadeus.shopping.hotel_offers_by_city.get(
            cityCode=city_code,
            checkInDate=check_in,
            checkOutDate=check_out,
            adults=1,
            radius=10,
            radiusUnit='KM'
        )
        results = response.data
        formatted = []
        for h in results[:3]:
            hotel_name = h['hotel']['name']
            price = h['offers'][0]['price']['total']
            currency = h['offers'][0]['price']['currency']
            formatted.append(f"{hotel_name} - {price} {currency}")
        return formatted
    except ResponseError as error:
        return [f"Hotel API error: {error}"]

