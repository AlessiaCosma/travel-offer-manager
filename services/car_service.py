from clients.osrm_client import OsrmClient
from utils.geocoding import Geocoding
from utils.currency_converter import currency_converter

class CarService:
    def __init__(self):
        self.car_client = OsrmClient()
        self.geocoder = Geocoding()

    def get_car_info(self, start, end, car_type=None, consumption=None, currency_code="EUR"):
        """
        Retrieves travel information for a car trip between two locations.

        This method converts input addresses into geographic coordinates using
        a geocoding service, then calculates the distance, travel time, and
        estimated fuel cost using the OSRM client.

        Args:
            start (str): Starting location (city, address, or place name).
            end (str): Destination location (city, address, or place name).
            car_type (str | None): Type of fuel used by the car ("gasoline", "diesel", "LPG").
                Defaults to "diesel" if not specified or invalid.
            consumption (float | None): The car consumption
            currency_code (str): Currency code for pricing (e.g., "EUR"). Default is "EUR".

        Returns:
            dict | None:
                - dict: A dictionary containing:
                    - "distance": Distance in kilometers
                    - "time": Travel time in hours
                    - "price": Estimated fuel cost
                    - "speed": tuple of estimated speed
                - None: If geocoding fails or route cannot be calculated.
        """
        start_coordinates = self.geocoder.geocode(start)
        end_coordinates = self.geocoder.geocode(end)
        if start_coordinates is not None and end_coordinates is not None:
            info = self.car_client.get_car_info(departure_city=start_coordinates, destination_city=end_coordinates,
                                                car_type=car_type, consumption=consumption)
            if info is None:
                return None
            if currency_code != "RON":
                new_price = currency_converter(info["price"], "RON", currency_code)
                if new_price is not None:
                    info["price"] = new_price
                elif currency_code == "EUR":
                    info["price"] = info["price"]/5
            info["price"] = round(info["price"], 2)
            info["speed"] = round(info["distance"] / info["time"], 2)
            return info
        return None
