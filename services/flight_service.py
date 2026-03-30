class FlightService:
    def __init__(self, client):
        self.client = client

    def get_flight_info(self, original_city, destination_city, departure_date, return_date=None, adult_number=1):
        """
        This method retrieves flight offers using the Amadeus client, then
        processes the results to determine the cheapest and fastest options.

        Args:
            original_city (str): Name of the departure city.
            destination_city (str): Name of the destination city.
            departure_date (str): Departure date in YYYY-MM-DD format.
            return_date (str | None): Return date (optional).
            adult_number (int): Number of adult passengers.

        Returns:
            dict | None:
                - dict: A dictionary containing:
                    - "time": (duration_of_cheapest_flight, shortest_duration)
                    - "price": (lowest_price, price_of_fastest_flight)
                - None: If no flight data is available or an error occurs.
        """
        flight_json = self.client.get_flights(original_city, destination_city, departure_date, return_date, adult_number)
        if not flight_json:
            return None

        durations = [f["itineraries"][0]["duration"] for f in flight_json]
        prices = [f["price"]["total"] for f in flight_json]

        result = self.format_list(durations, prices)
        if result is None:
            return None

        durations, prices = result

        best_price = min(prices)
        best_duration = min(durations)

        info ={         # best price |  best time
            "time": (durations[prices.index(best_price)], best_duration),
            "price": (best_price, prices[durations.index(best_duration)])
        }
        return info
    @staticmethod
    def format_list(duration_list, price_list):
        """
        Converts flight durations and prices into numeric values.

        Args:
            duration_list (list[str]): List of duration strings.
            price_list (list[str]): List of price values as strings.

        Returns:
            tuple[list[int], list[float]] | None:
                - tuple: (durations_in_minutes, prices_as_floats)
                - None: If duration format is invalid.
        """
        new_durations = []
        for i in range(len(duration_list)):
            duration_list[i] = duration_list[i].replace("PT", "")
            duration_list[i] = duration_list[i].replace("M", "")
            time = duration_list[i].split("H")

            hours = int(time[0]) if time[0] else 0
            minutes = int(time[1]) if len(time) > 1 and time[1] else 0
            new_durations.append(hours * 60 + minutes)

        price_list = [float(p) for p in price_list]
        return new_durations, price_list
