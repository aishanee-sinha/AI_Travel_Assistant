import os
from amadeus import Client, ResponseError
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

amadeus = Client(
    client_id=os.getenv("AMADEUS_API_KEY"),
    client_secret=os.getenv("AMADEUS_API_SECRET")
)

def resolve_city_to_code(city_name):
    try:
        # Search for city or airport code
        response = amadeus.reference_data.locations.get(
            keyword=city_name,
            subType='CITY,AIRPORT'
        )
        if response.data and len(response.data) > 0:
            for location in response.data:
                if location.get("subType") == "CITY":
                    return location["iataCode"]
            return response.data[0]["iataCode"]
        return city_name[:3].upper()
    except ResponseError as error:
        print(f"Amadeus city lookup error: {error}")
        return city_name[:3].upper()

def get_flight_prices_with_links(origin, destination, date):
    try:
        # Normalize date to YYYY-MM-DD
        try:
            datetime.strptime(date, '%Y-%m-%d')
            normalized_date = date
        except ValueError:
            normalized_date = datetime.now().strftime('%Y-%m-%d')
        origin_code = resolve_city_to_code(origin)
        destination_code = resolve_city_to_code(destination)
        print(f"[Amadeus] Requesting flights: {origin_code} -> {destination_code} on {normalized_date}")
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin_code,
            destinationLocationCode=destination_code,
            departureDate=normalized_date,
            adults=1,
            max=3,
            currencyCode="USD"
        )
        print(f"[Amadeus] Raw API response: {response.data}")
        if not response.data:
            print(f"[Amadeus] No flights found for {origin_code} to {destination_code} on {normalized_date}")
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
                f"{i+1}. {airline} – ${price}\n   🕐 Duration: {duration}\n   🛫 Departs: {first['at']} from {first['iataCode']}\n   🛬 Arrives: {last['at']} at {last['iataCode']}\n   🔗 [Book here]({link})"
            )
        return [f"✈️ Flight Options ({origin_code} → {destination_code} on {normalized_date}):\n\n"] + formatted
    except ResponseError as error:
        error_msg = str(error)
        print(f"[Amadeus] ResponseError: {error_msg}")
        if "400" in error_msg:
            return [f"❌ Invalid request: Please check if the cities and date are valid"]
        elif "401" in error_msg:
            return [f"❌ Authentication error: Please check API credentials"]
        elif "404" in error_msg:
            return [f"❌ No flights found for the specified route"]
        else:
            return [f"❌ Flight API error: {error_msg}"]
    except Exception as e:
        print(f"[Amadeus] Exception: {e}")
        return [f"❌ Error: {e}"] 