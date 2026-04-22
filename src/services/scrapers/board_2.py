import logging
from typing import Any, Dict, List, Optional

from src.services.scrapers.base import BaseLoadScraper

logger = logging.getLogger(__name__)


class Board2Scraper(BaseLoadScraper):
    """Scraper for Board 2 (swanautomation webhook — no auth)."""

    BOARD_NAME = "Board 2"
    API_URL = "https://demo.swanautomation.store/webhook/7c584a73-0a69-45f4-8bca-c3066e5bec3a"
    AUTH_REQUIRED = False

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    PICKUP_TIME_FIELDS = [
        "pickup_start_datetime",
        "pickup_end_datetime",
        "pick_up_datetime",
    ]
    DELIVERY_TIME_FIELDS = [
        "delivery_start_datetime",
        "delivery_end_datetime",
        "delivery_datetime",
    ]

    def _stop_is_valid(self, stop: Dict) -> bool:
        return bool(stop.get("city") and stop.get("state"))

    def _has_meaningful_data(self, job: Dict) -> bool:
        stops = job.get("stops", []) or []
        if not stops:
            return False
        valid_stops = [s for s in stops if self._stop_is_valid(s)]
        if not valid_stops:
            return False

        has_miles = bool(job.get("total_miles"))
        has_pickup = any(job.get(f) for f in self.PICKUP_TIME_FIELDS)
        has_delivery = any(job.get(f) for f in self.DELIVERY_TIME_FIELDS)
        has_appointments = any(s.get("appointment_start_time") for s in valid_stops)

        return any([has_miles, has_pickup, has_delivery, has_appointments])

    def _format_stop_location(self, stop: Dict) -> Optional[str]:
        city = stop.get("city", "").upper()
        state = stop.get("state", "").upper()
        zipcode = stop.get("zipcode", "")

        if not city or not state:
            return None

        for city_name in self.cities_list:
            if city_name in city or city_name in f"{city} {state}".upper():
                city = city_name
                break

        return f"{city}, {state} {zipcode}"

    def _format_stops(self, stops: List[Dict]) -> List[str]:
        if not stops:
            return ["No stops information"]

        valid = [s for s in (self._format_stop_location(stop) for stop in stops) if s]
        return valid if valid else ["No valid stops"]

    def _extract_state_code(self, stops: List[Dict]) -> str:
        if not stops:
            return ""
        return stops[0].get("state", "").upper()

    def _stops_to_locations(self, stops: List[Dict]) -> List[str]:
        locations = []
        for stop in stops:
            city = stop.get("city", "")
            state = stop.get("state", "")
            zipcode = stop.get("zipcode", "")
            if city and state:
                locations.append(f"{city}, {state} {zipcode}")
        return locations

    def _fetch_raw(self) -> List[Dict]:
        response = self.session.post(self.API_URL, json={}, timeout=self.REQUEST_TIMEOUT)
        if response.status_code != 200:
            logger.error(f"{self.BOARD_NAME}: API request failed ({response.status_code})")
            return []

        payload = response.json()
        if not isinstance(payload, list):
            logger.error(f"{self.BOARD_NAME}: unexpected response format {type(payload)}")
            return []
        return payload

    def _build_entry(self, job: Dict) -> Optional[Dict[str, Any]]:
        load_id = job.get("load_id")
        if not load_id or not self._has_meaningful_data(job):
            return None

        stops = job.get("stops", [])

        return {
            "order_id": str(load_id),
            "distance": f"{job.get('total_miles', 0):,.1f} miles",
            "pickup_time": self._extract_pickup_time(job),
            "delivery_time": self._extract_delivery_time(job),
            "stops": self._format_stops(stops),
            "state_code": self._extract_state_code(stops),
            "route": self._create_route_link(self._stops_to_locations(stops)),
        }
