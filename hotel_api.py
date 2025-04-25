import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# Replace with your actual affiliate token
AFFILIATE_TOKEN = os.getenv('HOTEL_API')

def search_location(query, token=AFFILIATE_TOKEN):
    url = 'https://engine.hotellook.com/api/v2/lookup.json'
    params = {
        'query': query,
        'lang': 'en',
        'lookFor': 'both',
        'limit': 1,
        'token': token
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    # print(f'Location response: {response.json()}')
    return response.json()

def get_hotel_prices(location_id, check_in, check_out, token=AFFILIATE_TOKEN):
    url = 'https://engine.hotellook.com/api/v2/cache.json'
    params = {
        'locationId': location_id,
        'checkIn': check_in,
        'checkOut': check_out,
        'adults': 2,
        'limit': 5,
        'token': token
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def display_hotels(hotels):
    if not hotels:
        print("No hotels found.")
        return
    for idx, hotel in enumerate(hotels, start=1):
        name = hotel.get('hotelName', 'N/A')
        stars = hotel.get('stars', 'N/A')
        price = hotel.get('priceFrom', 'N/A')
        currency = hotel.get('currency', 'USD')
        print(f"{idx}. {name}")
        print(f"   Stars: {stars}")
        print(f"   Price from: {price} {currency}")
        print("-" * 40)

def normalize_date_for_hotel(date_str):
    """
    Normalize date string to YYYY-MM-DD format, assuming 2025 if year is not provided.
    Handles multiple input formats like:
    - MM-DD
    - DD-MM
    - YYYY-MM-DD
    - DD-MM-YYYY
    """
    try:
        # First try parsing as YYYY-MM-DD
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        try:
            # Try DD-MM-YYYY format
            date_obj = datetime.strptime(date_str, '%d-%m-%Y')
        except ValueError:
            try:
                # Try MM-DD format (assume current year)
                date_obj = datetime.strptime(f"{date_str}-2025", '%m-%d-%Y')
            except ValueError:
                # Try DD-MM format (assume current year)
                date_obj = datetime.strptime(f"{date_str}-2025", '%d-%m-%Y')
    
    return date_obj.strftime('%Y-%m-%d')

def get_hotel_prices_with_links(city_name, check_in, check_out, token=AFFILIATE_TOKEN):
    location_data = search_location(city_name, token).get('results')
    if not location_data or not location_data.get('locations'):
        print(f"No location found for {city_name}.")
        return []
    location_id = location_data['locations'][0]['id']
    print(f"Location ID for {city_name}: {location_id}")
    check_in_date = normalize_date_for_hotel(check_in)
    check_out_date = normalize_date_for_hotel(check_out)
    
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
    
    formatted_hotels = []
    for idx, hotel in enumerate(hotels, start=1):
        name = hotel.get('hotelName', 'N/A')
        stars = hotel.get('stars', 'N/A')
        price = hotel.get('priceFrom', 'N/A')
        currency = hotel.get('currency', 'USD')
        link = f"https://www.hotellook.com/hotels/{hotel['hotelId']}"
        formatted_hotels.append(f"{idx}. {name} ({stars} stars) - {price} {currency}\nLink: {link}")
    return formatted_hotels

# Example usage
if __name__ == "__main__":
    city = 'Las Vegas'
    location_data = search_location(city).get('results')
    if location_data.get('locations'):
        location_id = location_data['locations'][0]['id']
        check_in_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        check_out_date = (datetime.now() + timedelta(days=33)).strftime('%Y-%m-%d')
        hotels = get_hotel_prices(location_id, check_in_date, check_out_date)
        display_hotels(hotels)
    else:
        print(f"No location found for {city}.")