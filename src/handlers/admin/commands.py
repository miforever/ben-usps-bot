import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.handlers.filters import IsAdminFilter, PrivateChatOnlyFilter
from src.services.city_manager import CityManager
from src.services.order_manager import OrderManager

logger = logging.getLogger(__name__)
router = Router()
router.message.filter(PrivateChatOnlyFilter(), IsAdminFilter())


@router.message(Command("stoppost"))
async def cmd_stoppost(message: Message, app):
    app.posting_enabled = False
    logger.info(f"Posting stopped by admin {message.from_user.id}")
    await message.answer("⏸ Posting paused!")


@router.message(Command("startpost"))
async def cmd_startpost(message: Message, app):
    app.posting_enabled = True
    logger.info(f"Posting started by admin {message.from_user.id}")
    await message.answer("✅ Posting enabled!")


@router.message(Command("status"))
async def cmd_status(message: Message, app):
    status = "🟢 Enabled" if app.posting_enabled else "🔴 Disabled"
    await message.answer(f"📊 Posting Status: {status}")


@router.message(Command("clearorders"))
async def cmd_clearorders(message: Message, order_manager: OrderManager):
    order_manager.clear_all_orders()
    await message.answer("✅ All orders have been cleared from the database.")


@router.message(Command("addcity"))
async def cmd_addcity(message: Message, city_manager: CityManager):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("⚠️ Please provide a city name.\nExample: /addcity Miami")
        return

    city = parts[1].strip()
    if city_manager.add_city(city):
        await message.answer(f"✅ City {city.upper()} has been added to the cities list.")
    else:
        await message.answer(f"⚠️ City {city.upper()} is already in the list.")


@router.message(Command("listcities"))
async def cmd_listcities(message: Message, city_manager: CityManager):
    cities = city_manager.get_all_cities()
    if not cities:
        await message.answer("📄 <b>Cities list is empty.</b>")
        return

    formatted = "\n".join(f"• {city}" for city in cities)
    await message.answer(f"📄 <b>Cities list ({len(cities)}):</b>\n\n{formatted}")


@router.message(Command("removecity"))
async def cmd_removecity(message: Message, city_manager: CityManager):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("⚠️ Please provide a city name.\nExample: /removecity Miami")
        return

    city = parts[1].strip()
    if city_manager.remove_city(city):
        await message.answer(
            f"✅ City <b>{city.upper()}</b> has been removed from the cities list."
        )
    else:
        await message.answer(f"❌ City {city.upper()} not found in the cities list.")


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "<b>🛠 Admin Commands</b>\n\n"
        "<b>/startpost</b> – Resume posting loads to the channel\n"
        "<b>/stoppost</b> – Pause posting loads\n"
        "<b>/status</b> – Check posting status\n"
        "<b>/clearorders</b> – Clear all stored order IDs\n"
        "<b>/addcity CITY</b> – Add a city to the filter list\n"
        "<b>/removecity CITY</b> – Remove a city from the filter list\n"
        "<b>/listcities</b> – Show all tracked cities\n"
    )
    await message.answer(help_text)
