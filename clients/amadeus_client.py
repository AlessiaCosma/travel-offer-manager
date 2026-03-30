import requests
import os
from dotenv import load_dotenv

class AmadeusClient:
    def __init__(self):
        load_dotenv()
        self.api = os.getenv('AMADEUS_API_KEY')
        self.secret = os.getenv('AMADEUS_SECRET')
        # FLight endpoints
        self.base_url = "https://test.api.amadeus.com"
        self.token_endpoint = f"{self.base_url}/v1/security/oauth2/token"
        self.iata_code_endpoint = f"{self.base_url}/v1/reference-data/locations/cities"
        self.flight_endpoint = f"{self.base_url}/v2/shopping/flight-offers"
        # Hotel endpoints
        self.city_hotel_endpoint = f"{self.base_url}/v1/reference-data/locations/hotels/by-city"
        self.geocode_endpoint = f"{self.base_url}/v1/reference-data/locations/hotels/by-geocode"
        self.hotel_search_endpoint = f"{self.base_url}/v3/shopping/hotel-offers"

        self.token = self.get_new_token()
        if not self.token:
            raise ValueError("Failed to authenticate with Amadeus API")
        self.header = {'Authorization': f'Bearer {self.token}'}



    def get_new_token(self):
        """
        Generates a new access token using the Amadeus API client credentials.

        Returns:
            str | None:
                - str: The access token required for authenticated API calls.
                - None: If the API request fails.

        """
        header = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        body = {
            'grant_type': 'client_credentials',
            'client_id': self.api,
            'client_secret': self.secret,
        }
        response = requests.post(self.token_endpoint, headers=header, data=body)
        if response.status_code != 200:
            return None
        else:
            return response.json()['access_token']

    def get_iata_code(self, city):
        """
        Retrieves the IATA airport code for the specified city.

        Args:
            city (str): Name of the city.
        Returns:
            str | None:
            - str: The IATA code of the first matching airport.
            - None: If the API request fails.
        """
        params = {
            'keyword': city.upper(),
            'include': 'AIRPORTS'
        }
        response = requests.get(url=self.iata_code_endpoint, params=params, headers=self.header)
        if response.status_code != 200:
            return None
        else:
            return response.json()['data'][0]['iataCode']

    def get_flights(self, original_city, destination_city, departure_date, return_date=None, adult_number=1, currency_code="EUR", nonstop=True):
        """
        Searches for available flight offers based on the provided criteria.

        Args:
            original_city (str): Name of the departure city.
            destination_city (str): Name of the destination city.
            departure_date (str): Departure date in YYYY-MM-DD format.
            return_date (str | None): Return date in YYYY-MM-DD format (optional).
            adult_number (int): Number of adult passengers. Default is 1.
            currency_code (str): Currency code for pricing (e.g., "EUR"). Default is "EUR".
            nonstop (bool): Direct flight. Default is True.
        Returns:
            list[dict] | None:
                - list[dict]: A list of flight offers if results are found.
                - None: If the API request fails.
        """
        origin_code = self.get_iata_code(original_city)
        dest_code = self.get_iata_code(destination_city)
        query = {
            "originLocationCode": origin_code,
            "destinationLocationCode": dest_code,
            "departureDate": departure_date,
            "adults": adult_number,
            "nonStop": nonstop,
            "currencyCode": currency_code,
            #"max": "10",
        }
        if return_date is not None:
            query["returnDate"] = return_date
        response = requests.get(url=self.flight_endpoint, headers=self.header, params=query)
        if response.status_code != 200:
            return None
        else:
            return response.json()['data']

    def get_hotel_code_city(self, city, radius=5, ratings=None):
        """
        Retrieves hotel IDs located within a specified radius of a given city.

        Args:
            city (str): Name of the city where hotels should be searched.
            radius (int): Maximum distance in kilometers from the city center. Default is 5.
            ratings (list[str] | int | None): Desired hotel rating(s) in stars (optional).

        Returns:
            list[str] | None:
                - list[str]: A list containing the IDs of hotels found in the specified city area.
                - None: If the API request fails.
        """
        query = {
            "cityCode": self.get_iata_code(city),
            "radius": radius,
        }
        if ratings is not None:
            query["ratings"] = ratings

        response = requests.get(url=self.city_hotel_endpoint, params=query, headers=self.header)
        if response.status_code != 200:
            return None
        else:
            hotel_code = []
            for hotels in response.json()['data']:
                hotel_code.append(hotels['hotelId'])
            return hotel_code

    def get_hotel_code_geocode(self, lat, lng, radius=5, ratings=None):
        """
        Retrieves hotel IDs located near the specified geographic coordinates.

        Args:
            lat (float): Latitude of the location.
            lng (float): Longitude of the location.
            radius (int): Maximum search radius in kilometers. Default is 5.
            ratings (list[str] | int | None): Desired hotel rating(s) in stars (optional).

        Returns:
            list[str] | None:
                - list[str]: A list containing the IDs of hotels found in the specified area.
                - None: If the API request fails.
        """
        query = {
            "latitude": lat,
            "longitude": lng,
            "radius": radius,
        }
        if ratings is not None:
            query["ratings"] = ratings

        response = requests.get(url=self.geocode_endpoint, params=query, headers=self.header)
        if response.status_code != 200:
            return None
        else:
            hotel_code = []
            for hotels in response.json()['data']:
                hotel_code.append(hotels['hotelId'])
            return hotel_code

    def get_hotels(self, check_in, check_out, city_name=None,  geocode=None, price_range=None,  ratings=None, adults=1, currency="EUR"):
        """
        Searches for hotel offers based on city name or geographic coordinates.

        Args:
            check_in (str): Check-in date in YYYY-MM-DD format.
            check_out (str): Check-out date in YYYY-MM-DD format.
            city_name (str | None): Name of the city where hotels should be searched.
            geocode (tuple[float, float] | None): Geographic coordinates in the form (longitude, latitude).
            price_range (str | None): Desired price range for hotels (optional).
            ratings (list[str] | int | None): Desired hotel rating(s) in stars (optional).
            adults (int): Number of adult guests. Default is 1.
            currency (str): Currency code for hotel prices (e.g., "EUR").

        Returns:
            list[tuple] | None:
                - list[tuple]: A list containing hotel information:
                    (hotel_name, price, phone_number?) depending on availability.
                - None: If the API request fails or no valid search parameters are provided.
        """
        if geocode is not None and ratings is not None:
            lat, lng = geocode
            hotel_code = self.get_hotel_code_geocode(lat, lng, ratings=ratings)
        elif geocode is not None:
            lat, lng = geocode
            hotel_code = self.get_hotel_code_geocode(lat, lng)
        elif city_name is not None and ratings is not None:
            hotel_code = self.get_hotel_code_city(city_name, ratings=ratings)
        elif city_name is not None:
            hotel_code = self.get_hotel_code_city(city_name)
        else:
            return None
        hotel_code = hotel_code[:20]
        query = {
            "hotelIds": ",".join(hotel_code), # First 20 hotels from the list
            "adults": adults,
            "checkInDate": check_in,
            "checkOutDate": check_out,
            "currency": currency,
        }

        if price_range is not None:
            query["priceRange"] = price_range

        response = requests.get(url=self.hotel_search_endpoint, params=query, headers=self.header)
        if response.status_code != 200:
            return None
        else:
            hotel_name_price_contact = []
            for hotel in response.json()['data']:
                try:
                    hotel_name_price_contact.append((hotel["hotel"]["name"],float(hotel['offers'][0]["price"]["total"]), hotel["hotel"]["contact"]["phone"]))
                except KeyError: #if there is no phone number
                    hotel_name_price_contact.append((hotel["hotel"]["name"],float(hotel['offers'][0]["price"]["total"])))
            return hotel_name_price_contact
