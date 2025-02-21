import json
import csv
import os
import re
from html import unescape
import logging
import pandas as pd

# Налаштування логування
logger = logging.getLogger(__name__)


def get_range_price(items: dict) -> float:
    """Повертає середнє значення між мінімальною ціною зі знижкою та максимальною оригінальною ціною"""
    try:
        discount_price = items.get("DiscountPrice", "")
        original_price = items.get("OriginalPrice", "")

        # Функція для отримання чисел з рядка
        def get_numbers_from_string(price_str: str) -> list[float]:
            if not price_str:
                return []
            try:
                if " - " in price_str:
                    return [float(p.strip()) for p in price_str.split(" - ")]
                return [float(price_str.strip())]
            except ValueError:
                return []

        # Отримуємо числа з обох цін
        discount_numbers = get_numbers_from_string(str(discount_price))
        original_numbers = get_numbers_from_string(str(original_price))

        # Визначаємо мінімальну ціну зі знижки
        min_price = min(discount_numbers) if discount_numbers else None
        if min_price is None and original_numbers:
            min_price = min(original_numbers)

        # Визначаємо максимальну оригінальну ціну
        max_price = max(original_numbers) if original_numbers else None
        if max_price is None and discount_numbers:
            max_price = max(discount_numbers)

        # Якщо є обидві ціни, повертаємо середнє
        if min_price is not None and max_price is not None:
            return round((min_price + max_price) / 2, 2)
        # Якщо є тільки одна ціна
        elif min_price is not None:
            return round(min_price, 2)
        elif max_price is not None:
            return round(max_price, 2)
        
        return 0.0

    except Exception as e:
        print(f"Помилка при обчисленні ціни: {e}")
        return 0.0


def get_item_info(item_data: tuple) -> dict:
    """Повертає інформацію про товар у вигляді словника."""
    try:
        item, reviews = item_data
        product_id = item["result"]['item']['itemId']
        
        # Формування специфікацій
        specs = item["result"]["item"]["properties"].get("list", [])
        specs_info = "\n".join(f"{spec['name']}: {spec['value']}" for spec in specs) if specs else ""
        
        # Отримання фото з відгуків
        reviews_photo_links = []
        if reviews is not None:  # Додана перевірка на None
            try:
                if isinstance(reviews, dict) and 'result' in reviews:
                    for review in reviews.get('result', {}).get("resultList", []):
                        if isinstance(review, dict) and 'review' in review:
                            imgs = review['review'].get("reviewImages", [])
                            if imgs:
                                reviews_photo_links.extend([f"https:{img}" for img in imgs])
            except Exception as e:
                logger.error(f"Помилка при отриманні фото відгуків: {e}")
        
        # Отримання основних фото
        main_photo_links = []
        try:
            description_obj = item["result"]["item"].get("description", {})
            if description_obj and "images" in description_obj and description_obj["images"]:
                main_photo_links = [f"https:{image}" for image in description_obj["images"]]
            elif "images" in item["result"]["item"] and item["result"]["item"]["images"]:
                main_photo_links = [f"https:{image}" for image in item["result"]["item"]["images"]]
        except Exception as e:
            logger.error(f"Помилка при отриманні основних фото: {e}")
        
        # Формуємо правильні посилання для Cloudinary
        cloud_name = os.getenv('CLOUD_NAME')
        hosting_folder_links = [
            f"https://res.cloudinary.com/{cloud_name}/{product_id}/MainPhotos",
            f"https://res.cloudinary.com/{cloud_name}/{product_id}/PhotoReviews"
        ]
        
        return {
            "Link": f"https:{item['result']['item']['itemUrl']}",
            "Title": item["result"]["item"]["title"],
            "DiscountPrice": item.get('result', {}).get("item", {}).get("sku", {}).get("def", {}).get("promotionPrice", ""),
            "OriginalPrice": item.get('result', {}).get("item", {}).get("sku", {}).get("def", {}).get("price", ""),
            "Rating": float(item["result"]["reviews"]["averageStar"]),
            "Likes": item["result"]["item"]["wishCount"],
            "MainDeliveryOption": get_delivery_option(item),
            "Description": get_description(item),
            "Specifications": specs_info,
            "MainPhotoLinks": main_photo_links,
            "ReviewsPhotoLinks": reviews_photo_links,
            "HostingFolderLink": hosting_folder_links,
            "CloudinaryFolders": hosting_folder_links
        }
        
    except Exception as e:
        logger.error(f"Помилка при обробці даних товару: {e}")
        return None


def get_delivery_option(item: dict) -> str:
    """Отримує інформацію про доставку."""
    try:
        delivery_note = item.get("result", {}).get("delivery", {}).get("shippingList", [{}])[0].get('note', [])
        if delivery_note and len(delivery_note) >= 2:
            return f"{delivery_note[0]}\nDelivery: {delivery_note[1]}"
        return ""
    except Exception:
        return ""


def get_description(item: dict) -> str:
    """Отримує опис товару."""
    try:
        description_obj = item.get("result", {}).get("item", {}).get("description", {})
        description_text = description_obj.get("text", "").strip()
        if not description_text:
            raw_html = description_obj.get("html", "")
            description_text = re.sub(r'<[^>]*>', '', raw_html).strip()
        
        description_text = re.sub(r'window\.adminAccountId=\d+;', '', description_text)
        description_text = re.sub(r'with\(document\).*?src="[^"]+"', '', description_text, flags=re.DOTALL)
        description_text = re.sub(r'&bull;', '', description_text)
        description_text = re.sub(r'\s+', ' ', description_text).strip()
        return unescape(description_text)
    except Exception:
        return ""


def get_items_list_from_query(query_data: dict) -> list:
    """Повертає список ID товарів із результатів пошукового запиту."""
    try:
        items = query_data.get("result", {}).get("resultList", [])
        if not items:
            return []
        return [item['item']['itemId'] for item in items]
    except Exception as e:
        print(f"Помилка отримання списку товарів: {e}")
        return []


def get_shopify_one_item(items: dict, photos_url: list[str]) -> list[dict]:
    """Готує дані одного товару для Shopify."""
    body_html = (
        f"{items.get('Specifications', '')}\n"
        f"{items.get('Description', '')}"
    ).strip()
    
    price = get_range_price(items)
    
    # Базовий шаблон для першого рядка з усіма даними
    main_row = {
        "Handle": "1",
        "Title": items.get("Title", ""),
        "Body (HTML)": body_html,
        "Vendor": "",
        "Product Category": "Uncategorized",
        "Type": "",
        "Tags": items.get("Title", ""),
        "Published": "FALSE",
        "Option1 Name": "",
        "Option1 Value": "",
        "Option2 Name": "",
        "Option2 Value": "",
        "Option3 Name": "",
        "Option3 Value": "",
        "Variant SKU": "",
        "Variant Grams": "",
        "Variant Inventory Tracker": "shopify",
        "Variant Inventory Qty": "100",
        "Variant Inventory Policy": "continue",
        "Variant Fulfillment Service": "manual",
        "Variant Price": str(price),
        "Variant Compare At Price": "",
        "Variant Requires Shipping": "",
        "Variant Taxable": "",
        "Variant Barcode": "",
        "Image Src": photos_url[0] if photos_url else "",
        "Image Position": "1",
        "Image Alt Text": "",
        "Gift Card": "",
        "SEO Title": "",
        "SEO Description": "",
        "Google Shopping / Google Product Category": "",
        "Google Shopping / Gender": "",
        "Google Shopping / Age Group": "",
        "Google Shopping / MPN": "",
        "Google Shopping / AdWords Grouping": "",
        "Google Shopping / AdWords Labels": "",
        "Google Shopping / Condition": "",
        "Google Shopping / Custom Product": "",
        "Google Shopping / Custom Label 0": "",
        "Google Shopping / Custom Label 1": "",
        "Google Shopping / Custom Label 2": "",
        "Google Shopping / Custom Label 3": "",
        "Google Shopping / Custom Label 4": "",
        "Variant Image": "",
        "Variant Weight Unit": "",
        "Variant Tax Code": "",
        "Cost per item": "",
        "Price / International": "",
        "Compare At Price / International": "",
        "Status": "draft"
    }
    
    shopify_items = [main_row]
    
    # Додаємо рядки для інших фотографій
    for i, photo_url in enumerate(photos_url[1:], 2):
        extra_row = {
            "Handle": "1",
            "Image Src": photo_url,
            "Image Position": str(i)
        }
        shopify_items.append(extra_row)
    
    return shopify_items


def save_json(data: dict | list, filename: str) -> None:
    """Зберігає дані в JSON файл."""
    try:
        with open(f"{filename}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"✅ JSON файл збережено: {filename}.json")
    except Exception as e:
        logging.error(f"Помилка при збереженні JSON: {e}")
        raise


def save_csv(data: dict | list, filename: str) -> None:
    """Зберігає дані в CSV файл."""
    try:
        if isinstance(data, dict):
            data = [data]
            
        df = pd.DataFrame(data)
        df.to_csv(f"{filename}.csv", index=False)
        logging.info(f"✅ CSV файл збережено: {filename}.csv")
    except Exception as e:
        logging.error(f"Помилка при збереженні CSV: {e}")
        raise


def save_shopify_csv_one_item(items: list[dict] | dict, filename: str) -> None:
    """Зберігає дані для Shopify (один товар) у CSV файл."""
    try:
        if isinstance(items, dict):
            items = [items]
            
        df = pd.DataFrame(items)
        df.to_csv(f"{filename}_shopify.csv", index=False)
        logging.info(f"✅ Shopify CSV файл збережено: {filename}_shopify.csv")
    except Exception as e:
        logging.error(f"Помилка при збереженні Shopify CSV: {e}")
        raise


def save_shopify_csv_list_items(items: list[list[dict]], filename: str) -> None:
    """Зберігає дані для Shopify у CSV файл."""
    try:
        # Підготовка даних
        all_items = []
        count = 1
        for product_items in items:
            for item in product_items:
                item["Handle"] = count
                all_items.append(item)
            count += 1
            
        # Збереження файлу
        df = pd.DataFrame(all_items)
        df.to_csv(f"{filename}_shopify.csv", index=False)
        logging.info(f"✅ Shopify CSV файл збережено: {filename}_shopify.csv")
    except Exception as e:
        logging.error(f"Помилка при збереженні Shopify CSV: {e}")
        raise


def prepare_json(data: dict | list) -> str:
    """Готує JSON дані для відправки."""
    return json.dumps(data, ensure_ascii=False, indent=2)


def prepare_csv(data: dict | list) -> str:
    """Готує CSV дані для відправки."""
    try:
        if isinstance(data, dict):
            data = [data]
        
        # Конвертуємо списки в рядки для фото
        for item in data:
            if isinstance(item.get("MainPhotoLinks"), list):
                item["MainPhotoLinks"] = ",".join(item["MainPhotoLinks"])
            if isinstance(item.get("ReviewsPhotoLinks"), list):
                item["ReviewsPhotoLinks"] = ",".join(item["ReviewsPhotoLinks"])
            if isinstance(item.get("HostingFolderLink"), list):
                item["HostingFolderLink"] = ",".join(item["HostingFolderLink"])
        
        return pd.DataFrame(data).to_csv(index=False, encoding='utf-8')
    except Exception as e:
        print(f"Помилка при підготовці CSV: {e}")
        return ""


def prepare_shopify_csv(items: list[dict] | dict) -> str:
    """Готує Shopify CSV дані для відправки."""
    try:
        if isinstance(items, dict):
            items = [items]
        elif isinstance(items, list) and all(isinstance(i, list) for i in items):
            # Якщо це список списків словників, об'єднуємо їх з правильними Handle
            processed_items = []
            count = 1
            for product_items in items:
                for item in product_items:
                    item = item.copy()  # Створюємо копію щоб не змінювати оригінал
                    item["Handle"] = str(count)
                    processed_items.append(item)
                count += 1
            items = processed_items
        else:
            # Якщо це простий список словників для одного товару
            for item in items:
                item = item.copy()
                item["Handle"] = "1"
        
        # Створюємо DataFrame і зберігаємо як CSV
        df = pd.DataFrame(items)
        # Переконуємося що Handle перший у колонках
        cols = ['Handle'] + [col for col in df.columns if col != 'Handle']
        df = df[cols]
        return df.to_csv(index=False, encoding='utf-8')
    except Exception as e:
        print(f"Помилка при підготовці Shopify CSV: {e}")
        return ""
