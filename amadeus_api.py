from dotenv import load_dotenv
import os
from amadeus import Client, ResponseError
load_dotenv()

amadeus = Client(
    client_id=os.getenv("AMADEUS_API_KEY"),
    client_secret=os.getenv("AMADEUS_API_SECRET")
)

def resolve_city_to_code(city_name):
    try:
        response = amadeus.reference_data.locations.get(
            keyword=city_name,
            subType='CITY'
        )
        if response.data and len(response.data) > 0:
            return response.data[0]["iataCode"]
        else:
            print(f"⚠️ No IATA code found for '{city_name}', using fallback")
            return city_name[:3].upper()  # fallback if no match found
    except ResponseError as error:
        print(f"❌ City lookup error: {error}")
        return city_name[:3].upper()  # fallback on error



def get_flight_prices_with_links(origin, destination, date):
    try:
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=date,
            adults=1,
            max=3,
            currencyCode="USD"
        )
        results = response.data
        formatted = []

        for i, offer in enumerate(results[:3]):
            segments = offer["itineraries"][0]["segments"]
            first = segments[0]["departure"]
            last = segments[-1]["arrival"]
            price = offer["price"]["total"]
            airline = offer["validatingAirlineCodes"][0]
            duration = offer["itineraries"][0]["duration"].replace("PT", "").lower()

            link = f"https://www.google.com/flights?hl=en#flt={origin}.{destination}.{date};c:USD;e:1;sd:1;t:f"

            formatted.append(
                f"{i+1}. {airline} – ${price}\n"
                f"   🕐 Duration: {duration}\n"
                f"   🛫 Departs: {first['at']} from {first['iataCode']}\n"
                f"   🛬 Arrives: {last['at']} at {last['iataCode']}\n"
                f"   🔗 [Book here]({link})"
            )

        return [f"✈️ Flight Options ({origin} → {destination} on {date}):\n\n"] + formatted

    except ResponseError as error:
        return [f"Flight API error: {error}"]




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

