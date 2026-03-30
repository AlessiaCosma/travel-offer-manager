import requests

class OsrmClient:
    def __init__(self):
        self.url = "http://router.project-osrm.org/route/v1/driving"
        self.fuel_price = {
            "gasoline": 8.50,
            "diesel": 10.15,
            "LPG": 4.01,
        }
        self.car_consumption = { # l/100km
            "gasoline": 7,
            "diesel": 5,
            "LPG": 8.2,
        }

    def get_distance_time(self, departure_city,  destination_city):
        """
        Retrieves the driving distance and estimated travel time between two locations
        using the OSRM routing API.

        Args:
            departure_city (tuple[float, float]): Coordinates of the departure location (latitude, longitude).
            destination_city (tuple[float, float]): Coordinates of the destination location (latitude, longitude).

        Returns:
            tuple[float, float] | None:
                - tuple: (distance_in_km, travel_time_in_hours)
                - None: If the API request fails or no route is found.
        """
        lat1, lon1 = departure_city
        lat2, lon2 = destination_city

        response = requests.get(f"{self.url}/{lon1},{lat1};{lon2},{lat2}?overview=false", timeout=10)
        if response.status_code != 200:
            return None
        routes = response.json()["routes"]
        if not routes:
            return None
        distance = routes[0]["distance"]
        distance = round(float(distance) / 1000 , 2) # m->km
        time = routes[0]["duration"]
        time = round(float(time) / 3600, 2) # s->h

        return distance, time

    def get_car_info(self, departure_city, destination_city, car_type=None):
        """
        Calculates travel details for a car trip between two locations.

        This method retrieves the distance and travel time using the OSRM API,
        then estimates the fuel cost based on the selected car type.

        Args:
            departure_city (tuple[float, float]): Coordinates of the departure location (latitude, longitude).
            destination_city (tuple[float, float]): Coordinates of the destination location (latitude, longitude).
            car_type (str | None): Type of fuel used by the car ("gasoline", "diesel", "LPG").
                Defaults to "diesel" if not specified or invalid.

        Returns:
            dict | None:
                - dict: A dictionary containing:
                    - "distance": Distance in kilometers
                    - "time": Travel time in hours
                    - "price": Estimated fuel cost for the trip
                - None: If the route could not be calculated.
        """
        if car_type not in ["gasoline", "diesel", "LPG"]:
            car_type = "diesel"
        result = self.get_distance_time(departure_city, destination_city)
        if result is None:
            return None
        distance, time = result
        fuel_price = self.fuel_price[car_type]
        car_consumption = self.car_consumption[car_type]
        final_price = ((distance / 100) * car_consumption) * fuel_price
        info = {
            "distance": distance,
            "time": time,
            "price": final_price,
        }
        return info
