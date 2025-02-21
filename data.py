import json
import csv
import os
import re
from html import unescape
import logging
import pandas as pd


def get_range_price(items: dict) -> float:
    """Повертає середнє значення від діапазону цін"""
    try:
        # Отримуємо ціни зі знижкою та оригінальні
        discount_price = items.get("DiscountPrice", None)
        original_price = items.get("OriginalPrice", None)
        
        def convert_to_float_list(price) -> list[float]:
            """Конвертує ціну будь-якого типу в список чисел"""
            if price is None:
                return []
                
            # Якщо це вже число
            if isinstance(price, (int, float)):
                return [float(price)]
                
            # Якщо це список/кортеж
            if isinstance(price, (list, tuple)):
                result = []
                for p in price:
                    if isinstance(p, (int, float)):
                        result.append(float(p))
                    elif isinstance(p, str):
                        try:
                            result.append(float(p.strip()))
                        except ValueError:
                            continue
                return result
                
            # Якщо це рядок
            if isinstance(price, str):
                # Спробуємо розділити за різними роздільниками
                for separator in [" - ", ",", ";", "|"]:
                    if separator in price:
                        try:
                            return [float(p.strip()) for p in price.split(separator) if p.strip()]
                        except ValueError:
                            continue
                # Якщо немає роздільників, спробуємо конвертувати як одне число
                try:
                    return [float(price.strip())]
                except ValueError:
                    return []
                    
            return []
        
        # Отримуємо списки цін
        discount_prices = convert_to_float_list(discount_price)
        original_prices = convert_to_float_list(original_price)
        
        # Використовуємо ціни зі знижкою, якщо вони є
        if discount_prices:
            return sum(discount_prices) / len(discount_prices)
            
        # Інакше використовуємо оригінальні ціни
        if original_prices:
            return sum(original_prices) / len(original_prices)
            
        # Якщо взагалі немає цін, повертаємо оригінальну ціну або ціну зі знижкою як є
        if discount_price is not None:
            try:
                return float(str(discount_price).strip())
            except (ValueError, TypeError):
                pass
                
        if original_price is not None:
            try:
                return float(str(original_price).strip())
            except (ValueError, TypeError):
                pass
        
        return 0.0  # повертаємо 0 тільки якщо взагалі немає цін
        
    except Exception as e:
        print(f"Помилка при обчисленні ціни: {e}")
        # Якщо сталася помилка, спробуємо повернути хоч якусь ціну
        try:
            if discount_price is not None:
                return float(str(discount_price).strip())
            if original_price is not None:
                return float(str(original_price).strip())
        except:
            pass
        return 0.0


def get_item_info(item_data: tuple) -> dict:
    """
    Повертає інформацію про товар у вигляді словника.
    Об'єднує дані (опис, специфікації, ціни, фото, інші дані) із API.
    
    **Основні ціни для головного товару (які бачить користувач) визначаються за першим SKU:**
      - Якщо значення 'price' містить роздільник "-", то:
            NewPrice (DiscountPrice) = перша частина (мінімальна ціна)
            OldPrice (OriginalPrice) = друга частина (максимальна ціна)
      - Якщо роздільника немає:
            NewPrice (DiscountPrice) = значення з 'promotionPrice', якщо воно задане (не None і не пусте), інакше – значення 'price'
            OldPrice (OriginalPrice) = значення 'price'
    
    Додатково формується поле "SKUPriceRange" як рядок із діапазоном цін по всім варіантам.
    """
    item, reviews = item_data
    product_id = item["result"]['item']['itemId']
    
    # Формування специфікацій
    specs = item["result"]["item"]["properties"]["list"]
    specs_info = "\n".join(f"{spec['name']}: {spec['value']}" for spec in specs) if specs else ""
    
    # Отримання фото з відгуків
    reviews_photo = []
    
    try:
        delivery_note = item["result"]["delivery"]["shippingList"][0]['note']
        if delivery_note and len(delivery_note) >= 2:
            main_delivery_option = f"{delivery_note[0]}\nDelivery: {delivery_note[1]}"
        else:
            main_delivery_option = ""
    except Exception:
        main_delivery_option = ''
    
    # Отримання фото з опису: беремо список з ключа "images" у "description"
    description_obj = item["result"]["item"]["description"]
    # Перший варіант: фото із description (якщо є)
    if "images" in description_obj and description_obj["images"]:
        main_photo_links = ["https:" + image for image in description_obj["images"]]
    else:
        # Резервний варіант: спробуємо отримати фото з іншого місця, наприклад з основного поля товару
        if "images" in item["result"]["item"] and item["result"]["item"]["images"]:
            main_photo_links = ["https:" + image for image in item["result"]["item"]["images"]]
    
    # Отримання фото відгуків
    reviews_photo_links = ["https:" + image for image in reviews_photo]
    
    # Отримання текстового опису: спочатку ключ "text", інакше очищення HTML з "html"
    description_text = description_obj.get("text", "").strip()
    if not description_text:
        raw_html = description_obj.get("html", "")
        description_text = re.sub(r'<[^>]*>', '', raw_html).strip()
    
    # Видалення небажаних фрагментів із опису
    description_text = re.sub(r'window\.adminAccountId=\d+;', '', description_text)
    description_text = re.sub(r'with\(document\).*?src="[^"]+"', '', description_text, flags=re.DOTALL)
    description_text = re.sub(r'&bull;', '', description_text)
    description_text = re.sub(r'\s+', ' ', description_text).strip()
    description_text = unescape(description_text)
    
    if not description_text:
        description_text = ""
    else:
        description_text = description_text
    
    original_price = item.get('result', {}).get("item", {}).get("sku", {}).get("def", {}).get("price", "")
    discount_price = item.get('result', {}).get("item", {}).get("sku", {}).get("def", {}).get("promotionPrice", "")
    
    return {
        "Link": "https:" + item["result"]["item"]["itemUrl"],
        "Title": item["result"]["item"]["title"],
        "DiscountPrice": discount_price if discount_price else "",
        "OriginalPrice": original_price if original_price else "",
        "Rating": float(item["result"]["reviews"]["averageStar"]),
        "Likes": item["result"]["item"]["wishCount"],
        "MainDeliveryOption": main_delivery_option,
        "Description": description_text,
        "Specifications": specs_info,
        "MainPhotoLinks": main_photo_links,
        "ReviewsPhotoLinks": reviews_photo_links,
        "HostingFolderLink": [
            f"https://res.cloudinary.com/dnghh41px/{product_id}/MainPhotos",
            f"https://res.cloudinary.com/dnghh41px/{product_id}/PhotoReview"
        ],
    }


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


def get_shopify_one_item(items: dict, photos_url: list) -> list[dict]:
    """Готує дані одного товару для Shopify."""
    
    # Формуємо повний опис товару
    body_html = (
        f"{items.get('Specifications', '')}\n"
        f"{items.get('Description', '')}"
    ).strip()
    
    # Отримуємо ціну
    price = items.get('DiscountPrice') or items.get('OriginalPrice') or 0
    
    # Базовий шаблон для першого рядка з усіма даними
    main_row = {
        "Handle": "1",
        "Title": items.get("Title", ""),
        "Body (HTML)": body_html,  # Тепер містить і специфікації, і опис
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
        "Status": "draft"
    }
    
    # Шаблон для додаткових рядків (тільки Handle та фото)
    extra_row = {
        "Handle": "1",
        "Image Src": "",
        "Image Position": ""
    }
    
    shopify_items = [main_row]
    
    # Додаємо рядки для інших фотографій
    for i, photo_url in enumerate(photos_url[1:], 2):
        row = extra_row.copy()
        row["Image Src"] = photo_url
        row["Image Position"] = str(i)
        shopify_items.append(row)
    
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
    if isinstance(data, dict):
        data = [data]
    return pd.DataFrame(data).to_csv(index=False)


def prepare_shopify_csv(items: list[dict] | dict) -> str:
    """Готує Shopify CSV дані для відправки."""
    if isinstance(items, dict):
        items = [items]
    return pd.DataFrame(items).to_csv(index=False)
import json
import csv
import os
import re
from html import unescape
import logging
import pandas as pd


def get_range_price(items: dict) -> float:
    """Повертає середнє значення від діапазону цін"""
    try:
        # Отримуємо ціни зі знижкою та оригінальні
        discount_price = items.get("DiscountPrice", None)
        original_price = items.get("OriginalPrice", None)
        
        def convert_to_float_list(price) -> list[float]:
            """Конвертує ціну будь-якого типу в список чисел"""
            if price is None:
                return []
                
            # Якщо це вже число
            if isinstance(price, (int, float)):
                return [float(price)]
                
            # Якщо це список/кортеж
            if isinstance(price, (list, tuple)):
                result = []
                for p in price:
                    if isinstance(p, (int, float)):
                        result.append(float(p))
                    elif isinstance(p, str):
                        try:
                            result.append(float(p.strip()))
                        except ValueError:
                            continue
                return result
                
            # Якщо це рядок
            if isinstance(price, str):
                # Спробуємо розділити за різними роздільниками
                for separator in [" - ", ",", ";", "|"]:
                    if separator in price:
                        try:
                            return [float(p.strip()) for p in price.split(separator) if p.strip()]
                        except ValueError:
                            continue
                # Якщо немає роздільників, спробуємо конвертувати як одне число
                try:
                    return [float(price.strip())]
                except ValueError:
                    return []
                    
            return []
        
        # Отримуємо списки цін
        discount_prices = convert_to_float_list(discount_price)
        original_prices = convert_to_float_list(original_price)
        
        # Використовуємо ціни зі знижкою, якщо вони є
        if discount_prices:
            return sum(discount_prices) / len(discount_prices)
            
        # Інакше використовуємо оригінальні ціни
        if original_prices:
            return sum(original_prices) / len(original_prices)
            
        # Якщо взагалі немає цін, повертаємо оригінальну ціну або ціну зі знижкою як є
        if discount_price is not None:
            try:
                return float(str(discount_price).strip())
            except (ValueError, TypeError):
                pass
                
        if original_price is not None:
            try:
                return float(str(original_price).strip())
            except (ValueError, TypeError):
                pass
        
        return 0.0  # повертаємо 0 тільки якщо взагалі немає цін
        
    except Exception as e:
        print(f"Помилка при обчисленні ціни: {e}")
        # Якщо сталася помилка, спробуємо повернути хоч якусь ціну
        try:
            if discount_price is not None:
                return float(str(discount_price).strip())
            if original_price is not None:
                return float(str(original_price).strip())
        except:
            pass
        return 0.0


def get_item_info(item_data: tuple) -> dict:
    """
    Повертає інформацію про товар у вигляді словника.
    Об'єднує дані (опис, специфікації, ціни, фото, інші дані) із API.
    
    **Основні ціни для головного товару (які бачить користувач) визначаються за першим SKU:**
      - Якщо значення 'price' містить роздільник "-", то:
            NewPrice (DiscountPrice) = перша частина (мінімальна ціна)
            OldPrice (OriginalPrice) = друга частина (максимальна ціна)
      - Якщо роздільника немає:
            NewPrice (DiscountPrice) = значення з 'promotionPrice', якщо воно задане (не None і не пусте), інакше – значення 'price'
            OldPrice (OriginalPrice) = значення 'price'
    
    Додатково формується поле "SKUPriceRange" як рядок із діапазоном цін по всім варіантам.
    """
    item, reviews = item_data
    product_id = item["result"]['item']['itemId']
    
    # Формування специфікацій
    specs = item["result"]["item"]["properties"]["list"]
    specs_info = "\n".join(f"{spec['name']}: {spec['value']}" for spec in specs) if specs else ""
    
    # Отримання фото з відгуків
    reviews_photo = []
    
    try:
        delivery_note = item["result"]["delivery"]["shippingList"][0]['note']
        if delivery_note and len(delivery_note) >= 2:
            main_delivery_option = f"{delivery_note[0]}\nDelivery: {delivery_note[1]}"
        else:
            main_delivery_option = ""
    except Exception:
        main_delivery_option = ''
    
    # Отримання фото з опису: беремо список з ключа "images" у "description"
    description_obj = item["result"]["item"]["description"]
    # Перший варіант: фото із description (якщо є)
    if "images" in description_obj and description_obj["images"]:
        main_photo_links = ["https:" + image for image in description_obj["images"]]
    else:
        # Резервний варіант: спробуємо отримати фото з іншого місця, наприклад з основного поля товару
        if "images" in item["result"]["item"] and item["result"]["item"]["images"]:
            main_photo_links = ["https:" + image for image in item["result"]["item"]["images"]]
    
    # Отримання фото відгуків
    reviews_photo_links = ["https:" + image for image in reviews_photo]
    
    # Отримання текстового опису: спочатку ключ "text", інакше очищення HTML з "html"
    description_text = description_obj.get("text", "").strip()
    if not description_text:
        raw_html = description_obj.get("html", "")
        description_text = re.sub(r'<[^>]*>', '', raw_html).strip()
    
    # Видалення небажаних фрагментів із опису
    description_text = re.sub(r'window\.adminAccountId=\d+;', '', description_text)
    description_text = re.sub(r'with\(document\).*?src="[^"]+"', '', description_text, flags=re.DOTALL)
    description_text = re.sub(r'&bull;', '', description_text)
    description_text = re.sub(r'\s+', ' ', description_text).strip()
    description_text = unescape(description_text)
    
    if not description_text:
        description_text = ""
    else:
        description_text = description_text
    
    original_price = item.get('result', {}).get("item", {}).get("sku", {}).get("def", {}).get("price", "")
    discount_price = item.get('result', {}).get("item", {}).get("sku", {}).get("def", {}).get("promotionPrice", "")
    
    return {
        "Link": "https:" + item["result"]["item"]["itemUrl"],
        "Title": item["result"]["item"]["title"],
        "DiscountPrice": discount_price if discount_price else "",
        "OriginalPrice": original_price if original_price else "",
        "Rating": float(item["result"]["reviews"]["averageStar"]),
        "Likes": item["result"]["item"]["wishCount"],
        "MainDeliveryOption": main_delivery_option,
        "Description": description_text,
        "Specifications": specs_info,
        "MainPhotoLinks": main_photo_links,
        "ReviewsPhotoLinks": reviews_photo_links,
        "HostingFolderLink": [
            f"https://res.cloudinary.com/dnghh41px/{product_id}/MainPhotos",
            f"https://res.cloudinary.com/dnghh41px/{product_id}/PhotoReview"
        ],
    }


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


def get_shopify_one_item(items: dict, photos_url: list) -> list[dict]:
    """Готує дані одного товару для Shopify."""
    
    # Формуємо повний опис товару
    body_html = (
        f"{items.get('Specifications', '')}\n"
        f"{items.get('Description', '')}"
    ).strip()
    
    # Отримуємо ціну
    price = items.get('DiscountPrice') or items.get('OriginalPrice') or 0
    
    # Базовий шаблон для першого рядка з усіма даними
    main_row = {
        "Handle": "1",
        "Title": items.get("Title", ""),
        "Body (HTML)": body_html,  # Тепер містить і специфікації, і опис
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
        "Status": "draft"
    }
    
    # Шаблон для додаткових рядків (тільки Handle та фото)
    extra_row = {
        "Handle": "1",
        "Image Src": "",
        "Image Position": ""
    }
    
    shopify_items = [main_row]
    
    # Додаємо рядки для інших фотографій
    for i, photo_url in enumerate(photos_url[1:], 2):
        row = extra_row.copy()
        row["Image Src"] = photo_url
        row["Image Position"] = str(i)
        shopify_items.append(row)
    
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
    if isinstance(data, dict):
        data = [data]
    return pd.DataFrame(data).to_csv(index=False)


def prepare_shopify_csv(items: list[dict] | dict) -> str:
    """Готує Shopify CSV дані для відправки."""
    if isinstance(items, dict):
        items = [items]
    return pd.DataFrame(items).to_csv(index=False)
