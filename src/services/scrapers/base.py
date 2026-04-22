import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import requests

logger = logging.getLogger(__name__)


class BaseLoadScraper(ABC):
    """Shared machinery for board scrapers.

    Subclasses declare `BOARD_NAME`, `API_URL`, and (if auth is needed)
    `LOGIN_URL` + `AUTH_REQUIRED = True`, then implement `_fetch_raw()` and
    `_build_entry()`. Everything else (session setup, time formatting,
    pickup/delivery extraction, route-link, login, meaningful-data check,
    and the `get_new_entries` orchestration) lives here.
    """

    BOARD_NAME: str = "Base"
    API_URL: str = ""
    LOGIN_URL: str = ""
    AUTH_REQUIRED: bool = False
    REQUEST_TIMEOUT: int = 30

    HEADERS: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
    }

    PICKUP_TIME_FIELDS: List[str] = []
    DELIVERY_TIME_FIELDS: List[str] = []

    def __init__(self, cities_list: List[str]):
        self.cities_list = cities_list
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.token: Optional[str] = None
        self.username: Optional[str] = None
        self.password: Optional[str] = None

    # ---------- time formatting ----------

    def _format_time(self, time_str: str) -> str:
        """Format various time formats to MM/DD/YYYY HH:MM AM/PM."""
        if not time_str:
            return "Not specified"

        try:
            if "T" in time_str:
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                return dt.strftime("%m/%d/%Y %I:%M %p")

            if "-" in time_str and ":" in time_str:
                parts = time_str.split(" ")
                if len(parts) == 2:
                    date_part, time_part = parts
                    date_components = date_part.split("-")
                    if len(date_components) == 3:
                        month, day, year = date_components
                        time_obj = datetime.strptime(time_part, "%H:%M").time()
                        dt = datetime(
                            int(year),
                            int(month),
                            int(day),
                            time_obj.hour,
                            time_obj.minute,
                        )
                        return dt.strftime("%m/%d/%Y %I:%M %p")

            if "/" in time_str and ":" in time_str:
                dt = datetime.strptime(time_str, "%m/%d/%Y %H:%M")
                return dt.strftime("%m/%d/%Y %I:%M %p")

            return time_str

        except (ValueError, AttributeError) as e:
            logger.warning(f"{self.BOARD_NAME}: failed to parse time '{time_str}': {e}")
            return time_str

    # ---------- pickup / delivery extraction ----------

    def _extract_time_from_fields(self, job: Dict, fields: List[str]) -> Optional[str]:
        for field in fields:
            if job.get(field):
                return self._format_time(job[field])
        return None

    def _extract_pickup_time(self, job: Dict) -> str:
        direct = self._extract_time_from_fields(job, self.PICKUP_TIME_FIELDS)
        if direct:
            return direct

        for stop in job.get("stops", []):
            if stop.get("stop_type") == "Pickup":
                if stop.get("appointment_start_time"):
                    return self._format_time(stop["appointment_start_time"])
                if stop.get("appointment_end_time"):
                    return self._format_time(stop["appointment_end_time"])

        return "Not specified"

    def _extract_delivery_time(self, job: Dict) -> str:
        direct = self._extract_time_from_fields(job, self.DELIVERY_TIME_FIELDS)
        if direct:
            return direct

        for stop in reversed(job.get("stops", [])):
            if stop.get("stop_type") == "Delivery":
                if stop.get("appointment_start_time"):
                    return self._format_time(stop["appointment_start_time"])
                if stop.get("appointment_end_time"):
                    return self._format_time(stop["appointment_end_time"])

        return "Not specified"

    # ---------- route link ----------

    def _create_route_link(self, locations: List[str]) -> str:
        """Build a Google Maps route URL from pre-formatted location strings."""
        cleaned = [loc for loc in locations if loc]
        if len(cleaned) < 2:
            return ""
        encoded = [quote_plus(loc) for loc in cleaned]
        return "https://www.google.com/maps/dir/" + "/".join(encoded)

    # ---------- meaningful-data check ----------

    def _stop_is_valid(self, stop: Dict) -> bool:
        """Subclasses can tighten this to enforce required stop fields."""
        return True

    def _has_meaningful_data(self, job: Dict) -> bool:
        has_miles = job.get("total_miles") or job.get("totalDistance")
        has_pickup = any(job.get(f) for f in self.PICKUP_TIME_FIELDS)
        has_delivery = any(job.get(f) for f in self.DELIVERY_TIME_FIELDS)

        stops = job.get("stops", []) or []
        valid_stops = [s for s in stops if self._stop_is_valid(s)]
        has_valid_stops = bool(valid_stops)
        has_appointments = any(s.get("appointment_start_time") for s in valid_stops)

        return bool(has_miles or has_pickup or has_delivery or has_valid_stops or has_appointments)

    # ---------- auth ----------

    def _login(self) -> bool:
        """Default login: POST username/password, read token from result.data."""
        if not self.LOGIN_URL or not self.username or not self.password:
            logger.error(f"{self.BOARD_NAME}: login misconfigured")
            return False

        try:
            response = self.session.post(
                self.LOGIN_URL,
                json={"username": self.username, "password": self.password},
                timeout=self.REQUEST_TIMEOUT,
            )
            if response.status_code != 200:
                logger.error(f"{self.BOARD_NAME}: login failed with status {response.status_code}")
                return False

            result = response.json()
            if result.get("success") and result.get("data"):
                self.token = result["data"]
                self.session.headers["Authorization"] = f"Bearer {self.token}"
                logger.info(f"{self.BOARD_NAME}: login successful")
                return True

            logger.error(
                f"{self.BOARD_NAME}: login failed — {result.get('error', 'unknown error')}"
            )
            return False

        except Exception as e:
            logger.error(f"{self.BOARD_NAME}: login error — {e}")
            return False

    def _ensure_authenticated(self) -> bool:
        if not self.AUTH_REQUIRED:
            return True
        if self.token:
            return True
        return self._login()

    # ---------- template method ----------

    @abstractmethod
    def _fetch_raw(self) -> List[Dict]:
        """Board-specific HTTP fetch + response unwrapping. Return list of raw jobs."""

    @abstractmethod
    def _build_entry(self, job: Dict) -> Optional[Dict[str, Any]]:
        """Board-specific entry construction. Return None to skip the job."""

    def get_new_entries(self) -> List[Dict[str, Any]]:
        try:
            if not self._ensure_authenticated():
                logger.error(f"{self.BOARD_NAME}: authentication failed")
                return []

            jobs = self._fetch_raw()
            entries = [entry for entry in (self._build_entry(job) for job in jobs) if entry]
            logger.info(f"{self.BOARD_NAME}: fetched {len(entries)} entries")
            return entries

        except Exception as e:
            logger.error(f"{self.BOARD_NAME}: error fetching entries — {e}", exc_info=True)
            return []
