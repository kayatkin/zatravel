import logging
logger = logging.getLogger(__name__)
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime

@dataclass
class FlightSegment:
    departure_airport: str
    arrival_airport: str
    departure_time: str  # ISO формат для JSON
    arrival_time: str    # ISO формат для JSON
    airline: str
    flight_number: str
    duration: str

    @classmethod
    def from_amadeus_segment(cls, segment_data):
        try:
            dep_time = segment_data['departure']['at']
            arr_time = segment_data['arrival']['at']

            # Преобразуем время в ISO строку — безопасно для JSON
            dep_iso = dep_time.replace('Z', '+00:00') if 'Z' in dep_time else dep_time
            arr_iso = arr_time.replace('Z', '+00:00') if 'Z' in arr_time else arr_time

            return cls(
                departure_airport=segment_data['departure']['iataCode'],
                arrival_airport=segment_data['arrival']['iataCode'],
                departure_time=dep_iso,
                arrival_time=arr_iso,
                airline=segment_data['carrierCode'],
                flight_number=segment_data['number'],
                duration=segment_data.get('duration', '')
            )
        except Exception as e:
            raise ValueError(f"Failed to parse segment: {e}")

@dataclass
class FlightOffer:
    price: float
    currency: str
    segments: List[FlightSegment]

    @classmethod
    def from_amadeus_data(cls, data):
        """Преобразование данных из Amadeus API в объект"""
        segments = []
        for itinerary in data.get('itineraries', []):
            for segment in itinerary.get('segments', []):
                try:
                    seg = FlightSegment.from_amadeus_segment(segment)
                    segments.append(seg)
                except Exception as e:
                    logger.warning(f"Skipping invalid segment: {e}")
                    continue  # пропускаем битый сегмент

        return cls(
            price=float(data['price']['total']),
            currency=data['price']['currency'],
            segments=segments
        )

    def to_dict(self):
        """Преобразует объект в словарь для JSON-сериализации"""
        return {
            'price': self.price,
            'currency': self.currency,
            'segments': [asdict(segment) for segment in self.segments]
        }