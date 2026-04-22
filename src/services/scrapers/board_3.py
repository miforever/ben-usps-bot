import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.config import get_settings
from src.services.scrapers.base import BaseLoadScraper

logger = logging.getLogger(__name__)


class Board3Scraper(BaseLoadScraper):
    """Scraper for Board 3 API (MKU Logistics dispatcher)."""

    BOARD_NAME = "Board 3"
    API_URL = "http://172.86.97.3:7000/api/Dispatcher/LoadBids"
    LOGIN_URL = "http://172.86.97.3:7000/api/Account/Login"
    AUTH_REQUIRED = True

    HEADERS = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    def __init__(self, cities_list: List[str]):
        super().__init__(cities_list)
        settings = get_settings()
        self.username = settings.BOARD3_USERNAME
        self.password = settings.BOARD3_PASSWORD

    def _format_time(self, time_str: str) -> str:
        """Board 3 only ever returns MM/DD/YYYY HH:MM; keep the narrow parser."""
        if not time_str:
            return "Not specified"
        try:
            dt = datetime.strptime(time_str, "%m/%d/%Y %H:%M")
            return dt.strftime("%m/%d/%Y %I:%M %p")
        except ValueError:
            return time_str

    def _format_stop(self, stop: Dict) -> Optional[str]:
        short = stop.get("shortFormat", "")
        if not short:
            return None
        for city_name in self.cities_list:
            if city_name in short.upper():
                parts = short.split(",")
                parts[0] = city_name
                return ",".join(parts)
        return short

    def _fetch_raw(self) -> List[Dict]:
        response = self.session.get(self.API_URL, timeout=self.REQUEST_TIMEOUT)

        if response.status_code == 401:
            self.token = None
            if not self._login():
                return []
            response = self.session.get(self.API_URL, timeout=self.REQUEST_TIMEOUT)

        if response.status_code != 200:
            logger.error(f"{self.BOARD_NAME}: request failed ({response.status_code})")
            return []

        payload = response.json()
        if not payload.get("success"):
            # Token may be expired even on 200
            self.token = None
            if not self._login():
                logger.error(f"{self.BOARD_NAME}: re-auth failed — {payload.get('error')}")
                return []
            response = self.session.get(self.API_URL, timeout=self.REQUEST_TIMEOUT)
            payload = response.json()
            if not payload.get("success"):
                logger.error(f"{self.BOARD_NAME}: API error — {payload.get('error')}")
                return []

        return payload.get("data") or []

    def _build_entry(self, job: Dict) -> Optional[Dict[str, Any]]:
        load_id = job.get("loadId")
        if not load_id:
            return None

        stops = job.get("stops", [])
        formatted_stops = [s for s in (self._format_stop(st) for st in stops) if s]
        route_locations = [stop.get("shortFormat", "") for stop in stops if stop.get("shortFormat")]

        return {
            "order_id": str(load_id),
            "distance": f"{job.get('totalDistance', 0):,.1f} miles",
            "pickup_time": self._format_time(job.get("loadStartDate", "")),
            "delivery_time": self._format_time(job.get("loadEndDate", "")),
            "stops": formatted_stops or ["No stops information"],
            "state_code": job.get("originLocationState", ""),
            "route": self._create_route_link(route_locations),
        }
