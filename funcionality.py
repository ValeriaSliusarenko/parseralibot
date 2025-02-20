import io
import sys
import threading
from datetime import datetime
from ali_parse import (
    headers,
    parse_item,
    parse_query,
    get_query_from_url,
    get_item_id_from_url,
    get_items_list_from_query,
)
from data import (
    get_item_info,
    get_shopify_one_item,
    save_json,
    save_csv,
    save_shopify_csv_one_item,
    save_shopify_csv_list_items,
)
from hosting import upload_photos

def log_message(msg: str, log_callback=None):
    if log_callback:
        log_callback(msg)
    else:
        print(msg)

class LogRedirect(io.StringIO):
    def __init__(self, log_callback=None):
        super().__init__()
        self.log_callback = log_callback

    def write(self, text):
        super().write(text)
        text = text.strip()
        if text and self.log_callback:
            self.log_callback(text)

def parse_single_product(link: str, log_callback=None, progress_callback=None):
    total_steps = 9
    current_step = 0
    def update_progress_step():
        nonlocal current_step
        current_step += 1
        if progress_callback:
            progress_callback(int((current_step/total_steps)*100))
    saved_stdout = sys.stdout
    try:
        sys.stdout = LogRedirect(log_callback)
        log_message("=== Парсинг одного товару ===", log_callback)
        # 1. Отримання ID товару
        item_id = get_item_id_from_url(link)
        log_message(f"Отримано ID: {item_id}", log_callback)
        update_progress_step()
        # 2. Отримання даних
        item_data = parse_item(headers, item_id)
        if not item_data:
            log_message("Помилка отримання даних з сайту.", log_callback)
            if progress_callback:
                progress_callback(0)
            return
        log_message("Дані успішно отримано.", log_callback)
        update_progress_step()
        # 3. Формування словника
        item_dict = get_item_info(item_data)
        log_message("Сформовано дані товару.", log_callback)
        update_progress_step()
        # 4. Збереження JSON
        save_json(item_dict, item_id)
        log_message("JSON файл збережено.", log_callback)
        update_progress_step()
        # 5. Збереження CSV
        save_csv(item_dict.copy(), item_id)
        log_message("CSV файл збережено.", log_callback)
        update_progress_step()
        # 6. Завантаження основних фото
        main_photos_url = []
        if item_dict["MainPhotoLinks"]:
            main_photos_url = upload_photos(item_dict["MainPhotoLinks"], f"{item_id}/MainPhotos")
            log_message(f"Завантажено основних фото: {len(main_photos_url)}.", log_callback)
        update_progress_step()
        # 7. Завантаження фото відгуків
        if item_dict["ReviewsPhotoLinks"]:
            upload_photos(item_dict["ReviewsPhotoLinks"], f"{item_id}/PhotoReview")
            log_message("Фото відгуків завантажено.", log_callback)
        update_progress_step()
        # 8. Генерація даних для Shopify
        shopify_info = get_shopify_one_item(item_dict, main_photos_url)
        log_message("Shopify дані сформовано.", log_callback)
        update_progress_step()
        # 9. Збереження Shopify CSV
        save_shopify_csv_one_item(shopify_info, item_id)
        log_message("Shopify CSV файл збережено.", log_callback)
        update_progress_step()
        log_message("=== Парсинг одного товару завершено успішно! ===", log_callback)
    except Exception as e:
        log_message(f"Помилка при парсингу: {e}", log_callback)
        if progress_callback:
            progress_callback(0)
    finally:
        sys.stdout = saved_stdout

def parse_multiple_links(links_str: str, log_callback=None, progress_callback=None):
    saved_stdout = sys.stdout
    product_list = []
    shopify_products = []
    try:
        sys.stdout = LogRedirect(log_callback)
        links_list = [lnk.strip() for lnk in links_str.split(",") if lnk.strip()]
        if not links_list:
            log_message("Список лінків порожній.", log_callback)
            if progress_callback:
                progress_callback(0)
            return
        total_links = len(links_list)
        log_message(f"Початок парсингу {total_links} товарів.", log_callback)
        total_steps = total_links * 9
        current_step = 0
        def update_progress():
            nonlocal current_step
            current_step += 1
            if progress_callback:
                progress_callback(int((current_step/total_steps)*100))
        for idx, link in enumerate(links_list, start=1):
            log_message(f"--- Товар {idx} з {total_links} ---", log_callback)
            item_id = get_item_id_from_url(link)
            log_message(f"ID товару: {item_id}", log_callback)
            update_progress()
            item_data = parse_item(headers, item_id)
            if not item_data:
                log_message(f"Не вдалося отримати дані для товару {item_id}.", log_callback)
                update_progress()
                continue
            update_progress()
            item_dict = get_item_info(item_data)
            product_list.append(item_dict)
            update_progress()
            log_message(f"Дані товару {item_id} сформовано.", log_callback)
            main_photos_url = []
            if item_dict["MainPhotoLinks"]:
                main_photos_url = upload_photos(item_dict["MainPhotoLinks"], f"{item_id}/MainPhotos")
                log_message(f"Завантажено фото товару {item_id}: {len(main_photos_url)}.", log_callback)
            update_progress()
            if item_dict["ReviewsPhotoLinks"]:
                upload_photos(item_dict["ReviewsPhotoLinks"], f"{item_id}/PhotoReview")
            update_progress()
            shopify_info = get_shopify_one_item(item_dict, main_photos_url)
            shopify_products.append(shopify_info)
            update_progress()
            log_message(f"Товар {idx} оброблено успішно.", log_callback)
            update_progress()
        log_message("Збереження агрегованих файлів.", log_callback)
        timestamp = datetime.now().strftime("%H_%M_%S")
        save_json(product_list, f"list_items_{timestamp}")
        save_csv(product_list.copy(), f"list_items_{timestamp}")
        save_shopify_csv_list_items(shopify_products, f"list_items_{timestamp}")
        log_message("Агреговані файли успішно збережено.", log_callback)
        if progress_callback:
            progress_callback(100)
    except Exception as e:
        log_message(f"Помилка при парсингу списку лінків: {e}", log_callback)
        if progress_callback:
            progress_callback(0)
    finally:
        sys.stdout = saved_stdout

def parse_search_query(link: str, limit: int, log_callback=None, progress_callback=None):
    saved_stdout = sys.stdout
    product_list = []
    shopify_products = []
    try:
        sys.stdout = LogRedirect(log_callback)
        log_message("=== Парсинг за пошуковим запитом ===", log_callback)
        query = get_query_from_url(link)
        if not query:
            log_message("Не вдалося отримати query з посилання.", log_callback)
            if progress_callback:
                progress_callback(0)
            return
        log_message(f"Пошуковий запит: {query}", log_callback)
        query_items = parse_query(headers, query)
        if not query_items:
            log_message("Не вдалося отримати дані з пошукового запиту.", log_callback)
            if progress_callback:
                progress_callback(0)
            return
        all_items_id = get_items_list_from_query(query_items)
        if not all_items_id:
            log_message("Немає товарів за даним запитом.", log_callback)
            if progress_callback:
                progress_callback(0)
            return
        items_id_list = all_items_id[:limit]
        total_count = len(items_id_list)
        log_message(f"Буде оброблено {total_count} товарів.", log_callback)
        total_steps = total_count * 9
        current_step = 0
        def update_progress():
            nonlocal current_step
            current_step += 1
            if progress_callback:
                progress_callback(int((current_step/total_steps)*100))
        for idx, item_id in enumerate(items_id_list, start=1):
            log_message(f"--- Товар {idx} з {total_count}, ID: {item_id} ---", log_callback)
            item_data = parse_item(headers, item_id)
            if not item_data:
                log_message(f"Не вдалося отримати дані для товару {item_id}.", log_callback)
                update_progress()
                continue
            update_progress()
            item_dict = get_item_info(item_data)
            product_list.append(item_dict)
            update_progress()
            log_message(f"Дані товару {item_id} сформовано.", log_callback)
            main_photos_url = []
            if item_dict["MainPhotoLinks"]:
                main_photos_url = upload_photos(item_dict["MainPhotoLinks"], f"{item_id}/MainPhotos")
                log_message(f"Завантажено фото товару {item_id}: {len(main_photos_url)}.", log_callback)
            update_progress()
            if item_dict["ReviewsPhotoLinks"]:
                upload_photos(item_dict["ReviewsPhotoLinks"], f"{item_id}/PhotoReview")
            update_progress()
            shopify_info = get_shopify_one_item(item_dict, main_photos_url)
            shopify_products.append(shopify_info)
            update_progress()
            log_message(f"Товар {idx} оброблено успішно.", log_callback)
            update_progress()
        log_message("Збереження агрегованих файлів.", log_callback)
        save_json(product_list, f"list_items_from_{query}")
        save_csv(product_list.copy(), f"list_items_from_{query}")
        save_shopify_csv_list_items(shopify_products, f"list_items_from_{query}")
        log_message("Агреговані файли успішно збережено.", log_callback)
        if progress_callback:
            progress_callback(100)
    except Exception as e:
        log_message(f"Помилка при парсингу за пошуковим запитом: {e}", log_callback)
        if progress_callback:
            progress_callback(0)
    finally:
        sys.stdout = saved_stdout

async def start_parsing(mode: str, link_or_links: str, limit: int = 0,
                       log_callback=None, progress_callback=None):
    """Асинхронна версія функції start_parsing"""
    try:
        if mode == "single":
            parse_single_product(link_or_links, log_callback, progress_callback)
        elif mode == "query":
            parse_search_query(link_or_links, limit, log_callback, progress_callback)
        elif mode == "multiple":
            parse_multiple_links(link_or_links, log_callback, progress_callback)
        else:
            if log_callback:
                await log_callback(f"Невідомий режим парсингу: {mode}")
    except Exception as e:
        if log_callback:
            await log_callback(f"Критична помилка: {str(e)}")
        if progress_callback:
            progress_callback(0)

def run_in_thread(target, *args, **kwargs):
    th = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
    th.start()
