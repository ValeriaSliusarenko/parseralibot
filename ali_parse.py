import json
import os
from datetime import datetime
import logging
import asyncio
import random
import time

import aiohttp
import requests
from data import (
    get_item_info,
    get_shopify_one_item,
    get_items_list_from_query,
    save_json,
    save_csv,
    save_shopify_csv_one_item,
    save_shopify_csv_list_items,
)
from hosting import upload_photos
from dotenv import load_dotenv

# Завантаження змінних середовища
load_dotenv()

headers = {
    "x-rapidapi-key": os.getenv('RAPID_API_KEY'),
    "x-rapidapi-host": "aliexpress-datahub.p.rapidapi.com",
}

# Додаємо затримку між запитами
async def delay_request():
    await asyncio.sleep(random.uniform(2, 4))

async def make_request(url: str, params: dict) -> dict:
    """Виконує HTTP запит з повторними спробами та обробкою помилок"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await delay_request()
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params, timeout=30) as response:
                    if response.status == 429:
                        wait_time = int(response.headers.get('Retry-After', 60))
                        logging.warning(f"Rate limit reached. Waiting {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        continue
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as e:
            if attempt == max_retries - 1:
                logging.error(f"Failed after {max_retries} attempts: {str(e)}")
                return None
            await asyncio.sleep(5 * (attempt + 1))
    return None

async def parse_item(headers: dict, item_id: str) -> tuple[dict, dict] | None:
    """Повертає дані про товар за ID із сайту."""
    url = "https://aliexpress-datahub.p.rapidapi.com/item_detail_7"
    url_reviews = "https://aliexpress-datahub.p.rapidapi.com/item_review"

    querystring = {"itemId": item_id, "region": "US"}
    querystring_reviews = {"itemId": item_id, "page": "1", "sort": "default", "filter": "allReviews"}

    data_item = await make_request(url, querystring)
    if not data_item or data_item.get("result", {}).get("status", {}).get("data") == "error":
        return None

    await delay_request()
    data_reviews = await make_request(url_reviews, querystring_reviews)
    if not data_reviews or data_reviews.get("result", {}).get("status", {}).get("data") == "error":
        data_reviews = None

    return data_item, data_reviews

def get_item_id_from_url(link: str) -> str:
    """Повертає ID товару з посилання."""
    try:
        if "item/" in link:
            item_id = link.split("item/")[1].split(".")[0]
        elif "/_i/" in link:
            item_id = link.split("/_i/")[1].split(".")[0]
        else:
            return ""
        return item_id.strip()
    except (IndexError, AttributeError):
        return ""

def get_query_from_url(url: str) -> str:
    """Витягує пошуковий запит з URL AliExpress"""
    try:
        # Очищаємо URL
        url = url.lower().strip()
        
        # Спробуємо знайти пошуковий запит в різних форматах URL
        if 'wholesale-' in url:
            query = url.split('wholesale-')[1].split('.')[0]
            logging.info(f"Знайдено пошуковий запит в URL: {query}")
            return query.replace('-', ' ')
        elif 'SearchText=' in url:
            query = url.split('SearchText=')[1].split('&')[0]
            logging.info(f"Знайдено пошуковий запит в URL: {query}")
            return query
        elif '/search/' in url:
            query = url.split('/search/')[1].split('.html')[0]
            logging.info(f"Знайдено пошуковий запит в URL: {query}")
            return query
        else:
            # Якщо це просто текстовий запит
            logging.info(f"Використовуємо текстовий запит: {url}")
            return url
            
    except Exception as e:
        logging.error(f"Помилка отримання пошукового запиту: {e}")
        return url

async def parse_query(headers: dict, query: str) -> dict:
    """Повертає дані про товари за пошуковим запитом."""
    url_query = "https://aliexpress-datahub.p.rapidapi.com/item_search_4"
    
    # Очищаємо та форматуємо пошуковий запит
    clean_query = query.replace("+", " ").strip()
    
    if "aliexpress" in clean_query.lower():
        try:
            # Якщо це URL, витягуємо пошуковий запит
            if "SearchText=" in clean_query:
                clean_query = clean_query.split("SearchText=")[1].split("&")[0]
            elif "wholesale-" in clean_query:
                clean_query = clean_query.split("wholesale-")[1].split(".")[0]
                clean_query = clean_query.replace("-", " ")
            elif "w/wholesale-" in clean_query:
                clean_query = clean_query.split("wholesale-")[1].split(".")[0]
                clean_query = clean_query.replace("-", " ")
            elif "keywords=" in clean_query:
                clean_query = clean_query.split("keywords=")[1].split("&")[0]
                
            # Декодуємо URL-encoded символи
            clean_query = requests.utils.unquote(clean_query)
            clean_query = clean_query.replace("-", " ")
            
        except Exception as e:
            logging.error(f"Помилка обробки URL: {e}")
            return {}
    
    logging.info(f"Пошуковий запит: {clean_query}")
    
    querystring = {
        "q": clean_query,
        "page": "1", 
        "sort": "total_tranpro_desc",  # Сортування за продажами
        "region": "US",
        "shipTo": "US",
        "size": "50"
    }
    
    try:
        data = await make_request(url_query, querystring)
        if not data:
            logging.error("Не отримано відповіді від API")
            return {}
            
        # Перевіряємо наявність результатів
        items = data.get("result", {}).get("resultList", [])
        if not items:
            logging.error("Немає результатів пошуку")
            return {}
            
        logging.info(f"✅ Знайдено {len(items)} товарів")
        return data
        
    except Exception as e:
        logging.error(f"❌ Помилка пошуку товарів: {e}")
        return {}

def get_items_list_from_query(items: dict) -> list:
    """Повертає список ID товарів із результатів пошукового запиту."""
    try:
        result_list = items.get('result', {}).get('resultList', [])
        item_ids = []
        for item in result_list:
            if isinstance(item, dict):
                # Перевіряємо різні можливі шляхи до ID товару
                item_id = (
                    item.get('productId') or 
                    item.get('item', {}).get('productId') or
                    item.get('item', {}).get('itemId')
                )
                if item_id:
                    item_ids.append(str(item_id))
        return item_ids
    except Exception as e:
        logging.error(f"Помилка отримання списку товарів: {str(e)}")
        return []

def parse_item_from_link(link: str) -> None:
    """Парсинг та збереження одного товару за посиланням."""
    item_id = get_item_id_from_url(link)
    item_data = parse_item(headers, item_id)
    if item_data:
        item_dict = get_item_info(item_data)
        save_json(item_dict, item_id)
        save_csv(item_dict.copy(), item_id)
        main_photos_url = upload_photos(item_dict["MainPhotoLinks"], f"{item_id}/MainPhotos")
        upload_photos(item_dict["ReviewsPhotoLinks"], f"{item_id}/PhotoReview")
        shopify_info = get_shopify_one_item(item_dict, main_photos_url)
        save_shopify_csv_one_item(shopify_info, item_id)

def parse_items_from_links(headers: dict, items_id: list, filename: str = "list_items") -> bool:
    """Парсинг та збереження багатьох товарів із списку."""
    try:
        items = []
        shopify_list = []
        for item_id in items_id:
            try:
                item_data = parse_item(headers, str(item_id))  # Конвертуємо ID в рядок
                if item_data:
                    item_dict = get_item_info(item_data)
                    if item_dict:
                        items.append(item_dict)
                        main_photos_url = upload_photos(item_dict.get("MainPhotoLinks", []), f"{item_id}/MainPhotos")
                        if item_dict.get("ReviewsPhotoLinks"):
                            upload_photos(item_dict["ReviewsPhotoLinks"], f"{item_id}/PhotoReview")
                        shopify_info = get_shopify_one_item(item_dict, main_photos_url)
                        shopify_list.append(shopify_info)
            except Exception as e:
                logging.error(f"Помилка при парсингу товару {item_id}: {str(e)}")
                continue
        if items and shopify_list:
            save_json(items, filename)
            save_csv(items, filename)
            save_shopify_csv_list_items(shopify_list, filename)
            return True
        return False
    except Exception as e:
        logging.error(f"Помилка при парсингу списку товарів: {str(e)}")
        return False

async def parse_items_from_query(headers: dict, query: str, items_count: int, log_callback=None, folder_name="list_items") -> bool:
    """Парсинг багатьох товарів за пошуковим запитом."""
    try:
        async def log(text: str):
            logging.info(text)
            if log_callback:
                await log_callback(text)
        
        await log("🔍 Підготовка пошукового запиту...")
        
        if "aliexpress" in query.lower():
            query = get_query_from_url(query)
            if not query:
                await log("❌ Не вдалося отримати пошуковий запит з URL")
                return False
            await log(f"✅ Отримано пошуковий запит: {query}")
        
        await log("🔍 Пошук товарів...")
        query_data = await parse_query(headers, query)
        if not query_data:
            await log("❌ Не отримано результатів пошуку")
            return False
            
        items_list = get_items_list_from_query(query_data)
        if not items_list:
            await log("❌ Не знайдено товарів")
            return False
            
        await log(f"✅ Знайдено {len(items_list)} товарів")
        await log(f"⚙️ Обробка перших {items_count} товарів")
        
        # Парсимо товари
        items_data = []
        shopify_list = []
        
        for idx, item_id in enumerate(items_list[:items_count], 1):
            try:
                await log(f"📦 Обробка товару {idx}/{items_count}")
                item_data = await parse_item(headers, item_id)
                if not item_data:
                    await log(f"❌ Помилка отримання даних товару {idx}")
                    continue
                    
                item_dict = get_item_info(item_data)
                if item_dict:
                    items_data.append(item_dict)
                    await log(f"📸 Завантаження фото товару {idx}")
                    main_photos_url = upload_photos(
                        item_dict["MainPhotoLinks"],
                        f"{item_id}/MainPhotos"
                    )
                    if item_dict["ReviewsPhotoLinks"]:
                        upload_photos(
                            item_dict["ReviewsPhotoLinks"],
                            f"{item_id}/PhotoReview"
                        )
                    shopify_info = get_shopify_one_item(item_dict, main_photos_url)
                    shopify_list.append(shopify_info)
                    await log(f"✅ Товар {idx} успішно оброблено")
                    
            except Exception as e:
                await log(f"❌ Помилка обробки товару {idx}: {e}")
                continue
        
        if items_data and shopify_list:
            await log("💾 Збереження результатів...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_path = os.path.join(folder_name, f"items_{timestamp}")
            
            try:
                save_json(items_data, base_path)
                save_csv(items_data, base_path)
                save_shopify_csv_list_items(shopify_list, base_path)
                await log(f"✅ Збережено {len(items_data)} товарів")
                return True
            except Exception as e:
                await log(f"❌ Помилка збереження файлів: {e}")
                return False
            
        return False
        
    except Exception as e:
        if log_callback:
            await log(f"❌ Помилка при парсингу запиту: {e}")
        return False
