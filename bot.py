import logging
import os
import asyncio
import shutil
from datetime import datetime
import json
import io
import pandas as pd

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    FSInputFile
)
from dotenv import load_dotenv

# Імпорти з парсера
from ali_parse import (
    headers,
    parse_item,
    parse_query,
    get_item_id_from_url,
    get_items_list_from_query,
    parse_items_from_query
)
from data import (
    get_item_info,
    get_shopify_one_item,
    save_json,
    save_csv,
    save_shopify_csv_one_item,
    save_shopify_csv_list_items
)
from hosting import upload_photos

# Завантаження змінних середовища
load_dotenv()

# Спробуємо отримати токен з різних можливих назв змінних
BOT_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN") or 
    os.getenv("TELEGRAM_API_KEY") or 
    os.getenv("BOT_TOKEN")
)

if not BOT_TOKEN:
    raise ValueError(
        "Токен бота не знайдено! "
        "Переконайтеся, що в файлі .env встановлено TELEGRAM_API_KEY"
    )

# Перевіряємо інші необхідні змінні
RAPID_API_KEY = os.getenv("RAPID_API_KEY")
if not RAPID_API_KEY:
    raise ValueError(
        "API ключ не знайдено! "
        "Переконайтеся, що в файлі .env встановлено RAPID_API_KEY"
    )

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Створення папки для результатів
if not os.path.exists("list_items"):
    os.makedirs("list_items")

# Ініціалізація бота та диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Стани FSM
class ParsingStates(StatesGroup):
    choosing_mode = State()
    entering_link = State()
    entering_limit = State()
    parsing = State()

# Створення клавіатур
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 Почати парсинг")],
        [KeyboardButton(text="❓ Допомога")]
    ],
    resize_keyboard=True
)

mode_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Single", callback_data="mode_single"),
            InlineKeyboardButton(text="Query", callback_data="mode_query"),
            InlineKeyboardButton(text="Multiple", callback_data="mode_multiple")
        ],
        [InlineKeyboardButton(text="🔙 Головне меню", callback_data="main_menu")]
    ]
)

limit_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="3", callback_data="limit_3"),
            InlineKeyboardButton(text="5", callback_data="limit_5"),
            InlineKeyboardButton(text="7", callback_data="limit_7")
        ],
        [
            InlineKeyboardButton(text="10", callback_data="limit_10"),
            InlineKeyboardButton(text="20", callback_data="limit_20"),
            InlineKeyboardButton(text="30", callback_data="limit_30")
        ],
        [
            InlineKeyboardButton(text="40", callback_data="limit_40"),
            InlineKeyboardButton(text="50", callback_data="limit_50"),
            InlineKeyboardButton(text="60", callback_data="limit_60")
        ],
        [InlineKeyboardButton(text="🔙 Головне меню", callback_data="main_menu")]
    ]
)

async def update_status_message(message: types.Message, text: str):
    """Оновлює статус повідомлення"""
    try:
        await message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 Головне меню", callback_data="main_menu")]]
            )
        )
    except Exception as e:
        logging.error(f"Помилка оновлення статусу: {e}")

async def start_parsing_process(message: types.Message, state: FSMContext):
    data = await state.get_data()
    mode = data['mode']
    link = data['link']
    limit = data.get('limit', 1)
    
    # Створюємо початкове повідомлення
    status_message = await message.answer("🚀 Починаємо парсинг...")
    logs = []
    
    async def update_status(text: str):
        logs.append(text)
        try:
            await status_message.edit_text("\n".join(logs))
        except Exception as e:
            if "message is not modified" not in str(e):
                logging.error(f"Помилка оновлення статусу: {e}")
    
    try:
        if mode == "single":
            await update_status("⚙️ Парсинг одного товару...")
            item_id = get_item_id_from_url(link)
            if not item_id:
                await status_message.edit_text("❌ Некоректне посилання")
                return
                
            await update_status("⏳ Отримання даних товару...")
            item_data = await parse_item(headers, item_id)
            if not item_data:
                await status_message.edit_text("❌ Не вдалося отримати дані товару")
                return
                
            await update_status("⚙️ Обробка даних...")
            item_dict = get_item_info(item_data)
            
            await update_status("📸 Завантаження фотографій...")
            main_photos_url = upload_photos(item_dict["MainPhotoLinks"], f"{item_id}/MainPhotos")
            
            await update_status("🛍️ Підготовка даних для Shopify...")
            shopify_info = get_shopify_one_item(item_dict, main_photos_url)
            
            # Зберігаємо дані в state
            await state.update_data({
                'json_data': json.dumps(item_dict, ensure_ascii=False, indent=2),
                'csv_data': pd.DataFrame([item_dict]).to_csv(index=False),
                'shopify_data': pd.DataFrame(shopify_info).to_csv(index=False),
                'item_id': item_id
            })

            # Створюємо клавіатуру для завантаження
            download_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📥 Завантажити JSON", callback_data="download_json")],
                [InlineKeyboardButton(text="📥 Завантажити CSV", callback_data="download_csv")],
                [InlineKeyboardButton(text="📥 Завантажити Shopify CSV", callback_data="download_shopify")],
                [InlineKeyboardButton(text="🔄 Новий парсинг", callback_data="new_parsing")]
            ])

            # Оновлюємо повідомлення з клавіатурою
            await status_message.edit_text(
                "✅ Парсинг завершено! Оберіть формат для завантаження:",
                reply_markup=download_keyboard
            )

        elif mode == "query":
            await update_status(f"⚙️ Парсинг товарів за запитом (ліміт: {limit})...")
            query_data = await parse_query(headers, link)
            if not query_data:
                await status_message.edit_text("❌ Помилка при парсингу запиту")
                return
                
            items_list = get_items_list_from_query(query_data)[:limit]
            items_data = []
            shopify_list = []
            
            for idx, item_id in enumerate(items_list, 1):
                await update_status(f"📦 Обробка товару {idx}/{limit}")
                item_data = await parse_item(headers, item_id)
                if item_data:
                    item_dict = get_item_info(item_data)
                    items_data.append(item_dict)
                    main_photos_url = upload_photos(item_dict["MainPhotoLinks"], f"{item_id}/MainPhotos")
                    shopify_info = get_shopify_one_item(item_dict, main_photos_url)
                    shopify_list.append(shopify_info)
                    await update_status(f"✅ Товар {idx} успішно оброблено")
            
            if items_data:
                # Зберігаємо дані в state
                await state.update_data({
                    'json_data': json.dumps(items_data, ensure_ascii=False, indent=2),
                    'csv_data': pd.DataFrame(items_data).to_csv(index=False),
                    'shopify_data': pd.DataFrame(shopify_list).to_csv(index=False),
                    'item_id': 'query_result'
                })

                # Створюємо клавіатуру для завантаження
                download_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📥 Завантажити JSON", callback_data="download_json")],
                    [InlineKeyboardButton(text="📥 Завантажити CSV", callback_data="download_csv")],
                    [InlineKeyboardButton(text="📥 Завантажити Shopify CSV", callback_data="download_shopify")],
                    [InlineKeyboardButton(text="🔄 Новий парсинг", callback_data="new_parsing")]
                ])

                # Оновлюємо повідомлення з клавіатурою
                await status_message.edit_text(
                    "✅ Парсинг завершено! Оберіть формат для завантаження:",
                    reply_markup=download_keyboard
                )

        elif mode == "multiple":
            links_list = [l.strip() for l in link.split(",") if l.strip()]
            if not links_list:
                await status_message.edit_text("❌ Список посилань порожній")
                return
            
            items_data = []
            shopify_list = []
            
            for idx, item_link in enumerate(links_list, 1):
                await update_status(f"📦 Обробка товару {idx}/{len(links_list)}")
                
                item_id = get_item_id_from_url(item_link)
                if not item_id:
                    await update_status(f"⚠️ Пропущено товар {idx}: некоректне посилання")
                    continue
                
                item_data = await parse_item(headers, item_id)
                if not item_data:
                    await update_status(f"⚠️ Пропущено товар {idx}: помилка отримання даних")
                    continue
                
                item_dict = get_item_info(item_data)
                items_data.append(item_dict)
                
                main_photos_url = upload_photos(item_dict["MainPhotoLinks"], f"{item_id}/MainPhotos")
                shopify_info = get_shopify_one_item(item_dict, main_photos_url)
                shopify_list.append(shopify_info)
                
                await update_status(f"✅ Товар {idx} успішно оброблено")
            
            if items_data:
                # Зберігаємо дані в state
                await state.update_data({
                    'json_data': json.dumps(items_data, ensure_ascii=False, indent=2),
                    'csv_data': pd.DataFrame(items_data).to_csv(index=False),
                    'shopify_data': pd.DataFrame(shopify_list).to_csv(index=False),
                    'item_id': 'multiple_result'
                })

                # Створюємо клавіатуру для завантаження
                download_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📥 Завантажити JSON", callback_data="download_json")],
                    [InlineKeyboardButton(text="📥 Завантажити CSV", callback_data="download_csv")],
                    [InlineKeyboardButton(text="📥 Завантажити Shopify CSV", callback_data="download_shopify")],
                    [InlineKeyboardButton(text="🔄 Новий парсинг", callback_data="new_parsing")]
                ])

                # Оновлюємо повідомлення з клавіатурою
                await status_message.edit_text(
                    "✅ Парсинг завершено! Оберіть формат для завантаження:",
                    reply_markup=download_keyboard
                )
            else:
                await status_message.edit_text("❌ Не вдалося обробити жодного товару")

    except Exception as e:
        logging.error(f"Помилка: {e}")
        await status_message.edit_text(f"❌ Помилка при парсингу: {str(e)}")

@dp.callback_query(lambda c: c.data == "new_parsing")
async def new_parsing(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ParsingStates.choosing_mode)
    await callback.message.answer(
        "Оберіть режим парсингу:",
        reply_markup=mode_keyboard
    )

@dp.callback_query(lambda c: c.data.startswith("download_"))
async def process_download(callback: types.CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        file_type = callback.data.split("_")[1]
        item_id = data.get('item_id')

        if file_type == "json":
            file_data = data.get('json_data').encode()
            filename = f"item_{item_id}.json"
            caption = "📄 JSON файл"
        elif file_type == "csv":
            file_data = data.get('csv_data').encode()
            filename = f"item_{item_id}.csv"
            caption = "📄 CSV файл"
        elif file_type == "shopify":
            file_data = data.get('shopify_data').encode()
            filename = f"item_{item_id}_shopify.csv"
            caption = "📄 Shopify CSV файл"
        
        await callback.message.answer_document(
            document=types.BufferedInputFile(file_data, filename=filename),
            caption=caption
        )
        await callback.answer("✅ Файл надіслано")
        
    except Exception as e:
        logging.error(f"Помилка завантаження: {e}")
        await callback.answer("❌ Помилка при завантаженні файлу", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("mode_"))
async def process_mode_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обробник вибору режиму парсингу"""
    mode = callback.data.split('_')[1]
    
    if mode == "back":
        await callback.answer()
        await state.clear()
        await callback.message.answer("Головне меню", reply_markup=main_keyboard)
        return
        
    await callback.answer()
    await state.update_data(mode=mode)
    
    if mode == "query":
        await callback.message.edit_text(
            "Виберіть ліміт товарів:",
            reply_markup=limit_keyboard
        )
        await state.set_state(ParsingStates.entering_limit)
    else:
        await state.set_state(ParsingStates.entering_link)
        message_text = (
            "Введіть посилання на товар:" if mode == "single"
            else "Введіть посилання на товари через кому:"
        )
        await callback.message.edit_text(message_text)

@dp.callback_query(lambda c: c.data.startswith("limit_"))
async def process_limit_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обробник вибору ліміту товарів"""
    limit = int(callback.data.split("_")[1])
    await state.update_data(limit=limit)
    await state.set_state(ParsingStates.entering_link)
    await callback.message.edit_text("Введіть пошуковий запит:")

@dp.callback_query(lambda c: c.data == "main_menu")
async def return_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "Повернення до головного меню.\nВиберіть опцію:",
        reply_markup=main_keyboard
    )
    await callback.answer()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обробник команди /start"""
    await message.answer(
        "👋 Вітаю! Я бот для парсингу AliExpress.\n"
        "Оберіть дію:",
        reply_markup=main_keyboard
    )

@dp.message(lambda m: m.text == "🚀 Почати парсинг")
async def start_parsing_command(message: types.Message, state: FSMContext):
    """Обробник кнопки 'Почати парсинг'"""
    await state.set_state(ParsingStates.choosing_mode)
    await message.answer(
        "Оберіть режим парсингу:",
        reply_markup=mode_keyboard
    )

@dp.message(lambda m: m.text == "❓ Допомога")
async def help_command(message: types.Message):
    """Обробник кнопки 'Допомога'"""
    help_text = (
          
        "🤖 *AliExpress Parser Bot*\n\n"
        
        "🎯 *Режими:*\n"
        "• Single - один товар\n"
        "• Query - пошук товарів\n"
        "• Multiple - список товарів\n\n"
        
        "📱 *Як користуватись:*\n"
        "1.Тисни 'Почати парсинг'\n"
        "2.Обери режим\n"
        "3.Введи дані\n"
        "4.Чекай результат\n"
        "5.Завантаж файли\n\n"
        
        "⚡️ *Ліміти API:*\n"
        "🔄 300 запитів/день\n"
        "• Single - 2 запити\n"
        "• Query - 3+ запити\n"
        "• Multiple - 2 запити/товар\n\n"
        
        "⚠️ *Помилки:*\n"
        "🔴 Не вдалося отримати дані:\n"
        "• Ліміт API вичерпано\n"
        "• Зачекай 24 години\n\n"
        
        "🔴 Помилка запиту:\n"
        "• Перевір пошуковий запит\n"
        "• Можливо ліміт API\n\n"
        
        "🔴 Помилка парсингу:\n"
        "• Перевір посилання\n"
        "• Перевір доступність товару\n\n"
        
        "📦 *Файли:*\n"
        "📗 JSON - всі дані\n"
        "📘 CSV - базові дані\n"
        "📙 Shopify - для імпорту\n\n"
        
        "💡 *Поради:*\n"
        "• Single - для аналізу\n"
        "• Query - для пошуку\n"
        "• Multiple - для списків\n\n"
        
        "❗️ *Важливо:*\n"
        "• Слідкуй за лімітом - не більше 300 запитів/день\n"
        "• Перевіряй посилання\n"
        "• Для відміни жми - 🔙Повернутись до головного меню\n\n"
        
        "✨ *Успішного парсингу* ✨"
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(StateFilter(ParsingStates.entering_link))
async def process_link(message: types.Message, state: FSMContext):
    """Обробник введення посилання/запиту"""
    data = await state.get_data()
    await state.update_data(link=message.text)
    
    # Одразу починаємо парсинг
    await start_parsing_process(message, state)

@dp.message()
async def unknown_command(message: types.Message, state: FSMContext):
    """Обробник невідомих команд"""
    current_state = await state.get_state()
    if not current_state:  # Якщо немає активного стану
        await message.answer(
            "Використовуйте кнопки меню:",
            reply_markup=main_keyboard
        )

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
