from clients.train_client import TrainClient
from utils.currency_converter import currency_converter
from deep_translator import GoogleTranslator

class TrainService:
    def __init__(self):
        self.train_client = TrainClient()

    def get_train_info(self, start, end, currency_code):
        """
        Retrieves summarized travel information between two stations.

        This method computes both the shortest distance route and the fastest route,
        then returns a combined overview including distances, travel times, and
        an estimated ticket price.

        Args:
            start (str): Name of the departure station.
            end (str): Name of the destination station.
            currency_code (str): Currency code for pricing (e.g., "EUR").

        Returns:
            dict | None:
                - dict: A dictionary containing:
                    - "distance": tuple of distances (shortest, fastest)
                    - "time": tuple of travel times (shortest, fastest)
                    - "price": list of estimated ticket price (shortest, fastest)
                    - "speed": tuple of estimated train speed (shortest, fastest)
                - None: If no valid route exists between the stations.
        """
        start, end = self.format_station(start, end)
        best_distance = self.train_client.shortest_distance(start, end)
        best_time = self.train_client.shortest_time(start, end)
        if best_distance is None or best_time is None:
            return None
        distance1, time1 = best_distance
        distance2, time2 = best_time
        info = {
            "distance": (round(distance1, 2), round(distance2, 2)),
            "time": (round(time1, 2), round(time2, 2)),
            "price": [round(self.train_client.price * distance1, 2), round(self.train_client.price * distance2, 2)],
            "speed": (round(distance1/time1, 2), round(distance2/time2, 2))
        }
        if currency_code != "RON":
            p1 = currency_converter(info["price"][0], "RON", currency_code)
            p2 = currency_converter(info["price"][1], "RON", currency_code)
            if p1 is not None and p2 is not None:
                info["price"] = [p1,p2]
            elif currency_code == "EUR":
                info["price"] = [info["price"][0]/5,info["price"][1]/5]
            info ["price"] = [round(info["price"][0], 2), round(info["price"][1], 2)]
        return info

    def format_station(self, start, end):
        """
        Normalizes and maps input station names to valid station names from the train dataset.

        Args:
            start (str): Name of the departure station.
            end (str): Name of the destination station.

        Returns:
            tuple[str, str]:
                A tuple containing the matched station names as found in the dataset.
        """
        ro_start = GoogleTranslator(source='en', target='ro').translate(start)
        ro_end = GoogleTranslator(source='en', target='ro').translate(end)
        sorted_stations = sorted(list(self.train_client.stations))

        for station in sorted_stations:
            if ro_start in station:
                ro_start = station
            if ro_end in station:
                ro_end = station

        return ro_start, ro_end
