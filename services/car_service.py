from clients.osrm_client import OsrmClient
from geopy.geocoders import Nominatim

class CarService:
    def __init__(self):
        self.car_client = OsrmClient()
        self.geolocator = Nominatim(user_agent="my_app")

    def get_car_info(self, start, end, car_type=None):
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

        Returns:
            dict | None:
                - dict: A dictionary containing:
                    - "distance": Distance in kilometers
                    - "time": Travel time in hours
                    - "price": Estimated fuel cost
                - None: If geocoding fails or route cannot be calculated.
        """
        start_location = self.geolocator.geocode(start, timeout=10)
        end_location = self.geolocator.geocode(end, timeout=10)
        if start_location is not None and end_location is not None:
            start_coordinates = (start_location.latitude, start_location.longitude)
            end_coordinates = (end_location.latitude, end_location.longitude)
            return self.car_client.get_car_info(start_coordinates, end_coordinates, car_type)
        return None
