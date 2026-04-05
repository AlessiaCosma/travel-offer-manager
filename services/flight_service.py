from utils.currency_converter import currency_converter

class FlightService:
    def __init__(self, client):
        self.client = client

    def get_flight_info(self, original_city, destination_city, departure_date, return_date=None, adult_number=1, currency_code="EUR" , travel_class=None, nonstop=None):
        """
        This method retrieves flight offers using the Amadeus client, then
        processes the results to determine the cheapest and fastest options.

        Args:
            original_city (str): Name of the departure city.
            destination_city (str): Name of the destination city.
            departure_date (str): Departure date in YYYY-MM-DD format.
            return_date (str | None): Return date (optional).
            adult_number (int): Number of adult passengers.
            currency_code (str): Currency code for pricing (e.g., "EUR"). Default is "EUR".
            travel_class (str | None): Desired travel class. Possible values:
                - "ECONOMY"
                - "PREMIUM_ECONOMY"
                - "BUSINESS"
                - "FIRST"
                If None, no class filter is applied.
            nonstop (str | None): If True, returns only direct (non-stop) flights. Possible values: "true" or "false"

        Returns:
            dict | None:
                - dict: A dictionary containing:
                    - "time": (duration_of_cheapest_flight, shortest_duration)
                    - "price": (lowest_price, price_of_fastest_flight)
                - None: If no flight data is available or an error occurs.
        """
        flight_json = self.client.get_flights(original_city=original_city, destination_city=destination_city,
                                              departure_date=departure_date, return_date=return_date,
                                              adult_number=adult_number, currency_code=currency_code, nonstop=nonstop,
                                              travel_class=travel_class)
        if not flight_json:
            return None

        durations = [f["itineraries"][0]["duration"] for f in flight_json]
        price_data = [f["price"] for f in flight_json]

        result = self.format_list(durations, price_data, currency_code)
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
    def format_list(duration_list, price_data, selected_currency):
        """
        Converts flight durations and prices into numeric values.

        Args:
            duration_list (list[str]): List of duration strings.
            price_data (list[dict]): List of dictionaries.
            selected_currency (str): Currency code selected by the user.

        Returns:
            tuple[list[int], list[float]]:
                - tuple: (durations_in_minutes, prices_as_floats)
        """
        new_durations = []
        new_prices = []
        for i in range(len(duration_list)):
            duration_list[i] = duration_list[i].replace("PT", "")
            duration_list[i] = duration_list[i].replace("M", "")
            time = duration_list[i].split("H")

            hours = int(time[0]) if time[0] else 0
            minutes = int(time[1]) if len(time) > 1 and time[1] else 0
            new_durations.append(hours * 60 + minutes)

        for price in price_data:
            current_price = price["total"]
            current_price = float(current_price)
            currency_code = price["currency"]
            if currency_code != selected_currency:
                new_current_price = currency_converter(current_price, currency_code, selected_currency)
                if new_current_price is not None:
                    current_price = new_current_price
            new_prices.append(current_price)
        return new_durations, new_prices
