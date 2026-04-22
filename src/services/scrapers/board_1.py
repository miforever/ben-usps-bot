import logging
import re
from typing import Any, Dict, List, Optional

from src.config import get_settings
from src.services.scrapers.base import BaseLoadScraper

logger = logging.getLogger(__name__)


class Board1Scraper(BaseLoadScraper):
    """Scraper for Board 1 API (a2zexpress dispatcher)."""

    BOARD_NAME = "Board 1"
    API_URL = "http://172.86.97.3:7000/api/Dispatcher/LoadBids"
    LOGIN_URL = "http://172.86.97.3:7000/api/Account/Login"
    AUTH_REQUIRED = True

    PICKUP_TIME_FIELDS = [
        "loadStartDate",
        "pickup_start_datetime",
        "pickup_end_datetime",
        "pick_up_datetime",
    ]
    DELIVERY_TIME_FIELDS = [
        "loadEndDate",
        "delivery_start_datetime",
        "delivery_end_datetime",
        "delivery_datetime",
    ]

    _ADDRESS_REGEX = re.compile(r"([A-Za-z\.\s]+?),\s*([A-Z]{2}).*?(\d{5})$")

    def __init__(self, cities_list: List[str]):
        super().__init__(cities_list)
        settings = get_settings()
        self.username = settings.BOARD1_USERNAME
        self.password = settings.BOARD1_PASSWORD

    def _extract_city_state_zip(self, address: str) -> Optional[str]:
        match = self._ADDRESS_REGEX.search(address)
        if not match:
            return None

        city, state, zipcode = match.groups()
        city = city.strip().upper()

        for city_name in self.cities_list:
            if city_name in address.upper():
                city = city_name
                break

        return f"{city}, {state} {zipcode}"

    def _format_stops(self, stops: List[Dict]) -> List[str]:
        if not stops:
            return ["No stops information"]

        formatted: List[str] = []
        for stop in stops:
            if "shortFormat" in stop:
                location = stop["shortFormat"]
                for city_name in self.cities_list:
                    if city_name in stop.get("address", "").upper():
                        parts = location.split(",")
                        parts[0] = city_name
                        location = ",".join(parts)
                        break
                formatted.append(location)
            elif "address" in stop:
                formatted.append(self._extract_city_state_zip(stop["address"]) or "Unknown")
            else:
                formatted.append("Unknown")

        return formatted

    def _extract_state_code(self, stops: List[Dict]) -> str:
        if not stops:
            return ""

        first = stops[0]
        if "shortFormat" in first:
            parts = first["shortFormat"].split(",")
            if len(parts) >= 2:
                return parts[1].strip().split()[0]
        if "state" in first:
            return first["state"]
        return ""

    def _fetch_raw(self) -> List[Dict]:
        response = self.session.get(self.API_URL, timeout=self.REQUEST_TIMEOUT)

        if response.status_code == 401:
            logger.warning(f"{self.BOARD_NAME}: token expired, re-authenticating")
            self.token = None
            if not self._login():
                return []
            response = self.session.get(self.API_URL, timeout=self.REQUEST_TIMEOUT)

        if response.status_code != 200:
            logger.error(f"{self.BOARD_NAME}: API request failed ({response.status_code})")
            return []

        payload = response.json()

        if isinstance(payload, dict):
            if not payload.get("success"):
                logger.error(f"{self.BOARD_NAME}: API error — {payload.get('error')}")
                return []
            data = payload.get("data", [])
        elif isinstance(payload, list):
            data = payload
        else:
            logger.error(f"{self.BOARD_NAME}: unexpected response type {type(payload)}")
            return []

        if not isinstance(data, list):
            logger.error(f"{self.BOARD_NAME}: data is not a list ({type(data)})")
            return []

        return data

    def _build_entry(self, job: Dict) -> Optional[Dict[str, Any]]:
        load_id = job.get("load_id") or job.get("loadId")
        if not load_id or not self._has_meaningful_data(job):
            return None

        stops = job.get("stops", [])
        distance = job.get("total_miles") or job.get("totalDistance", 0)
        stop_addresses = [stop.get("address", "") for stop in stops if stop.get("address")]

        return {
            "order_id": str(load_id),
            "distance": f"{distance:,.1f} miles",
            "pickup_time": self._extract_pickup_time(job),
            "delivery_time": self._extract_delivery_time(job),
            "stops": self._format_stops(stops),
            "state_code": self._extract_state_code(stops),
            "route": self._create_route_link(stop_addresses),
        }
