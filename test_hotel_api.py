from hotel_api import get_hotel_prices_with_links
from dotenv import load_dotenv
import os
import requests
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Get API token
AFFILIATE_TOKEN = os.getenv('HOTEL_API')

def test_hotel_search():
    # Test parameters
    city = "Paris"
    check_in = "2024-04-01"  # Example date
    check_out = "2024-04-05"  # Example date
    
    print(f"\nSearching for hotels in {city} from {check_in} to {check_out}")
    print("API Key:", AFFILIATE_TOKEN[:5] + "..." if AFFILIATE_TOKEN else "Not found!")
    
    try:
        hotels = get_hotel_prices_with_links(city, check_in, check_out)
        if hotels:
            print("\nFound hotels:")
            for hotel in hotels:
                print("\n" + hotel)
        else:
            print("\nNo hotels found. This could be because:")
            print("1. Invalid API key")
            print("2. No hotels available for these dates")
            print("3. City not found in the database")
    except Exception as e:
        print(f"\nError: {str(e)}")

def test_alternative_dates():
    # Test with dates closer to today
    check_in = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')  # 7 days from now
    check_out = (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d')  # 10 days from now
    
    print(f"\n=== Testing Alternative Dates ===")
    print(f"Check-in: {check_in}")
    print(f"Check-out: {check_out}")
    
    url = 'https://engine.hotellook.com/api/v2/cache.json'
    params = {
        'locationId': 15542,  # Paris location ID
        'checkIn': check_in,
        'checkOut': check_out,
        'adults': 2,
        'limit': 5,
        'token': AFFILIATE_TOKEN
    }
    
    try:
        response = requests.get(url, params=params)
        print("\nResponse Status:", response.status_code)
        print("Response:", response.text[:500])  # Print first 500 chars of response
        
        if response.status_code == 200:
            hotels = response.json()
            if hotels:
                print("\nFound hotels:")
                for hotel in hotels:
                    print(f"\nHotel: {hotel.get('hotelName')}")
                    print(f"Price: {hotel.get('priceFrom')} {hotel.get('currency')}")
            else:
                print("\nNo hotels found in response")
        else:
            print("\nError response:", response.text)
            
    except Exception as e:
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    test_hotel_search()
    test_alternative_dates()