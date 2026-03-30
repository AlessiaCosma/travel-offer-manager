from clients.amadeus_client import AmadeusClient
from services.flight_service import FlightService
from services.hotel_service import HotelService
from services.car_service import CarService
from services.train_service import TrainService

amadeus_client = AmadeusClient() # pentru flight_service si hotel_service

# flight
# Optionale: return_date, adult_number
flight_service = FlightService(amadeus_client)
print(flight_service.get_flight_info(original_city="Bucharest", destination_city="Paris", departure_date="2026-05-05", return_date=None, adult_number=1))

# hotel
# Optionale: price_range, ratings, adults
hotel_service = HotelService(amadeus_client)
print(hotel_service.get_hotel_info(check_in="2026-05-05", check_out="2026-05-07", address="Paris", price_range=None,  ratings=None, adults=1))

# car
# Optionale: car_type
car_service = CarService()
print(car_service.get_car_info(start="Bucharest", end="Paris", car_type=None))

# train
train_service = TrainService()
print(train_service.get_train_info(start="Bucharest", end="Alba Iulia"))

