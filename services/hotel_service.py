from geopy.geocoders import Nominatim

class HotelService:
    def __init__(self, client):
        self.client = client
        self.geolocator = Nominatim(user_agent="my_app")

    def get_hotel_info(self, check_in, check_out, address, price_range=None,  ratings=None, adults=1):
        """
        This method attempts to convert the given address into geographic coordinates
        using a geocoding service. If successful, it searches for hotels using the
        geographic location; otherwise, it falls back to searching by city name.

        Args:
            check_in (str): Check-in date in YYYY-MM-DD format.
            check_out (str): Check-out date in YYYY-MM-DD format.
            address (str): Location of the hotel (city, address, or place name).
            price_range (str | None): Desired price range for hotels (optional).
            ratings (list[int] | int | None): Desired hotel star ratings (optional).
            adults (int): Number of adult guests. Default is 1.

        Returns:
            dict | None:
                - dict: A dictionary containing:
                    - "name_list": List of hotel names
                    - "price_list": List of hotel prices
                    - "contact_list": List of contact phone numbers (0 if unavailable)
                    - "price": Average price of the found hotels
                    - "hotels_found": Total number of hotels found
                - None: If no results are found or the API request fails.
        """
        new_address = self.geolocator.geocode(address, timeout=10)
        if new_address is not None:
            try:
                info = self.client.get_hotels(check_in=check_in, check_out=check_out, geocode=(new_address.latitude, new_address.longitude), price_range=price_range, ratings=ratings, adults=adults)
            except KeyError:
                info = self.client.get_hotels(check_in=check_in, check_out=check_out, city_name=address,
                                              price_range=price_range, ratings=ratings, adults=adults)
        else:
            info = self.client.get_hotels(check_in=check_in, check_out=check_out, city_name=address, price_range=price_range, ratings=ratings, adults=adults)
        if info is None:
            return None

        return self.format_result(info)

    @staticmethod
    def format_result(info):
        """
        Formats raw hotel data into a structured and user-friendly format.
        """
        information = {
            "name_list": [],
            "price_list": [],
            "contact_list": [],
            "price": 0.0,
            "hotels_found": 0
        }
        for hotel in info:
            information["name_list"].append(hotel[0])
            information["price_list"].append(float(hotel[1]))
            information["contact_list"].append(hotel[2] if len(hotel) > 2 else None)
        if not information["price_list"]:
            return None
        information["price"] = round(sum(information["price_list"])/len(information["price_list"]),2)
        information["hotels_found"] = len(information["price_list"])
        return information
