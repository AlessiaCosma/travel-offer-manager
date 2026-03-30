from clients.train_client import TrainClient
from deep_translator import GoogleTranslator

class TrainService:
    def __init__(self):
        self.train_client = TrainClient()

    def get_train_info(self, start, end):
        """
        Retrieves summarized travel information between two stations.

        This method computes both the shortest distance route and the fastest route,
        then returns a combined overview including distances, travel times, and
        an estimated ticket price.

        Args:
            start (str): Name of the departure station.
            end (str): Name of the destination station.

        Returns:
            dict | None:
                - dict: A dictionary containing:
                    - "distance": tuple of distances (shortest, fastest)
                    - "time": tuple of travel times (shortest, fastest)
                    - "price": estimated ticket price based on average distance
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
            "price": round(self.train_client.price * ((distance1 + distance2)/2), 2),
        }
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
        for station in self.train_client.stations:
            if ro_start in station:
                ro_start = station
            if ro_end in station:
                ro_end = station
        return ro_start, ro_end
