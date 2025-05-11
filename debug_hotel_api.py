import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("models/gemini-1.5-flash-latest")

# Get API token
AFFILIATE_TOKEN = os.getenv('HOTEL_API')
if not AFFILIATE_TOKEN:
    raise ValueError("HOTEL_API environment variable is not set!")

def convert_to_usd(price, from_currency):
    """Convert price to USD using a simple conversion rate"""
    # Simple conversion rates (you might want to use a real currency API in production)
    conversion_rates = {
        'EUR': 1.08,  # 1 EUR = 1.08 USD
        'GBP': 1.27,  # 1 GBP = 1.27 USD
        'USD': 1.0,   # 1 USD = 1 USD
    }
    
    if from_currency in conversion_rates:
        return round(price * conversion_rates[from_currency], 2)
    return price  # Return original price if currency not found

def get_hotel_prices_with_links(city_name, check_in, check_out, token=AFFILIATE_TOKEN):
    """Get hotel prices with booking links"""
    try:
        # Normalize dates
        check_in_date = normalize_date_for_hotel(check_in)
        check_out_date = normalize_date_for_hotel(check_out)
        
        # Ensure dates are within a reasonable range (not too far in the future)
        check_in_dt = datetime.strptime(check_in_date, '%Y-%m-%d')
        check_out_dt = datetime.strptime(check_out_date, '%Y-%m-%d')
        today = datetime.now()
        
        # If dates are more than 1 year in the future, adjust them
        if check_in_dt > today + timedelta(days=365):
            check_in_date = (today + timedelta(days=30)).strftime('%Y-%m-%d')
            check_out_date = (today + timedelta(days=33)).strftime('%Y-%m-%d')
        
        print(f"\nSearching hotels in {city_name}")
        print(f"Check-in: {check_in_date}")
        print(f"Check-out: {check_out_date}")
        
        # Search for location
        location_data = search_location(city_name, token)
        if not location_data or not location_data.get('results', {}).get('locations'):
            print(f"No location found for {city_name}")
            return []
            
        location_id = location_data['results']['locations'][0]['id']
        print(f"Found location ID: {location_id}")
        
        # Get hotel prices
        url = 'https://engine.hotellook.com/api/v2/cache.json'
        params = {
            'locationId': location_id,
            'checkIn': check_in_date,
            'checkOut': check_out_date,
            'adults': 2,
            'limit': 5,
            'token': token
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        hotels = response.json()
        
        if not hotels:
            print("No hotels found for the given dates")
            return []
            
        # Format hotel information
        formatted_hotels = []
        for idx, hotel in enumerate(hotels, start=1):
            name = hotel.get('hotelName', 'N/A')
            stars = hotel.get('stars', 'N/A')
            price = hotel.get('priceFrom', 'N/A')
            original_currency = hotel.get('currency', 'EUR')  # Default to EUR if not specified
            
            # Convert price to USD
            if price != 'N/A':
                price_usd = convert_to_usd(price, original_currency)
                price_display = f"${price_usd} USD"
                if original_currency != 'USD':
                    price_display += f" (originally {price} {original_currency})"
            else:
                price_display = "Price not available"
            
            link = f"https://www.hotellook.com/hotels/{hotel['hotelId']}"
            
            hotel_info = (
                f"{idx}. {name}\n"
                f"   ⭐ {stars} stars\n"
                f"   💰 {price_display}\n"
                f"   🔗 Book here: {link}"
            )
            formatted_hotels.append(hotel_info)
            
        return formatted_hotels
        
    except Exception as e:
        print(f"Error getting hotel prices: {str(e)}")
        return []

def search_location(query, token=AFFILIATE_TOKEN):
    """Search for a location and return its ID"""
    url = 'https://engine.hotellook.com/api/v2/lookup.json'
    params = {
        'query': query,
        'lang': 'en',
        'lookFor': 'both',
        'limit': 1,
        'token': token
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error searching location: {str(e)}")
        return None

def normalize_date_for_hotel(date_str):
    """Normalize date to YYYY-MM-DD format"""
    try:
        # If already in YYYY-MM-DD format, validate and return
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
        except ValueError:
            pass
            
        prompt = (
            "Convert this date to YYYY-MM-DD format. "
            "If the year is not specified, use the current year. "
            "If the date is ambiguous or invalid, return 'invalid'. "
            "Return ONLY the date in YYYY-MM-DD format, nothing else. "
            f"Date to normalize: {date_str}"
        )
        response = model.generate_content(prompt)
        normalized_date = response.text.strip()
        
        # Validate the date format
        try:
            datetime.strptime(normalized_date, '%Y-%m-%d')
            return normalized_date
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}")
            
    except Exception as e:
        print(f"Error normalizing date '{date_str}': {e}")
        raise ValueError(f"Invalid date format: {date_str}")

if __name__ == "__main__":
    # Test the API
    city = "Paris"
    check_in = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    check_out = (datetime.now() + timedelta(days=33)).strftime('%Y-%m-%d')
    
    hotels = get_hotel_prices_with_links(city, check_in, check_out)
    if hotels:
        print("\nFound hotels:")
        for hotel in hotels:
            print("\n" + hotel)
    else:
        print("\nNo hotels found")
