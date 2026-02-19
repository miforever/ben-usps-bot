# Ben USPS Bot

This project is a Telegram bot that automatically scrapes shipping load information from a web source and posts it to a specified Telegram channel. It's built with Python using the `aiogram` library for Telegram integration, `requests` and `beautifulsoup4` for web scraping, and `pydantic` for robust configuration management.

## Features

- **Automated Load Scraping**: The bot periodically scrapes a web source for new shipping loads.
- **Telegram Channel Integration**: New loads are formatted and posted to a designated Telegram channel.
- **Admin Controls**: A suite of admin commands allows for managing the bot's operation, including starting/stopping posting, checking status, and clearing the order history.
- **City-Based Filtering**: The bot can be configured to filter loads based on a customizable list of cities.
- **Error Handling and Notifications**: The bot includes error logging and can be configured to send notifications to an admin when issues arise.
- **Persistent Order Tracking**: The bot maintains a history of posted loads to prevent duplicates.
- **Multiple Scraper Support**: The project is structured to support multiple scraper implementations, allowing for easy extension to new data sources.

## Project Structure

```
.
├── .gitignore
├── env.example
├── requirements.txt
├── data/
├── scripts/
│   └── clear_orders.py
├── src/
│   ├── config.py
│   ├── main.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── filters.py
│   │   └── admin/
│   │       ├── __init__.py
│   │       └── commands.py
│   ├── middlewares/
│   │   └── services.py
│   └── services/
│       ├── city_manager.py
│       ├── error_notifier.py
│       ├── order_manager.py
│       └── scrapers/
│           ├── board_1.py
│           └── board_2.py
└── venv/
```

## Getting Started

### Prerequisites

- Python 3.8+
- A Telegram Bot Token
- A Telegram Channel ID
- Admin User IDs

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd ben-usps-bot
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the environment variables:**

    Create a `.env` file in the root directory by copying the `env.example` file:
    ```bash
    cp env.example .env
    ```

    Edit the `.env` file with your specific settings:
    ```env
    BOT_TOKEN="your_telegram_bot_token"
    TELEGRAM_CHANNEL_ID="@your_channel_or_id"
    DB_PATH="data/orders.db"
    MAX_LOADS=1000
    CITIES_FILE="data/cities.txt"
    ADMIN_IDS="123456789,987654321"
    ERROR_NOTIFICATION_ENABLED=True
    ERROR_NOTIFICATION_DELAY=60
    ```

### Running the Bot

To start the bot, run the `main.py` script:

```bash
python src/main.py
```

## Admin Commands

The following commands are available to admin users in a private chat with the bot:

- `/startpost`: Resume posting loads to the channel.
- `/stoppost`: Pause posting loads.
- `/status`: Check the current posting status.
- `/clearorders`: Clear all stored order IDs from the database.
- `/addcity <CITY>`: Add a city to the filter list.
- `/removecity <CITY>`: Remove a city from the filter list.
- `/listcities`: Show all tracked cities.
- `/help`: Show the help message with all available commands.

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.
