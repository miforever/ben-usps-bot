from typing import List

from src.services.scrapers.base import BaseLoadScraper
from src.services.scrapers.board_1 import Board1Scraper
from src.services.scrapers.board_2 import Board2Scraper
from src.services.scrapers.board_3 import Board3Scraper

_REGISTRY = {
    1: Board1Scraper,
    2: Board2Scraper,
    3: Board3Scraper,
}


def get_scraper(active_board: int, cities_list: List[str]) -> BaseLoadScraper:
    """Return the scraper instance matching ACTIVE_BOARD."""
    try:
        cls = _REGISTRY[active_board]
    except KeyError as e:
        raise ValueError(
            f"Unknown ACTIVE_BOARD={active_board}; must be one of {sorted(_REGISTRY)}"
        ) from e
    return cls(cities_list)


__all__ = ["BaseLoadScraper", "get_scraper"]
