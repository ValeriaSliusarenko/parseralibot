import os
import logging
import cloudinary
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from dotenv import load_dotenv

# Завантаження змінних середовища
load_dotenv()

# Налаштування логування
logger = logging.getLogger(__name__)

# Налаштування Cloudinary з змінних середовища
# https://console.cloudinary.com/settings/c-6f5534e46e74f613fa802f99963078/api-keys

cloudinary.config(
    cloud_name=os.getenv('CLOUD_NAME'),
    api_key=os.getenv('API_KEY'),
    api_secret=os.getenv('API_SECRET'),
    secure=True
)

def upload_photos(item_info: dict) -> dict:
    """
    Завантажує фото в Cloudinary у відповідні папки.
    
    Args:
        item_info (dict): Словник з інформацією про товар
        
    Returns:
        dict: Словник з URL завантажених фото
    """
    uploaded_urls = {"MainPhotos": [], "PhotoReviews": []}
    
    try:
        # Отримуємо посилання на фото
        main_photos = item_info.get("MainPhotoLinks", [])
        review_photos = item_info.get("ReviewsPhotoLinks", [])
        
        # Отримуємо ID товару з посилання
        product_id = item_info.get("Link", "").split("/")[-1].split(".")[0]
        
        # Формуємо папки для завантаження
        folders = {
            "MainPhotos": f"{product_id}/MainPhotos",
            "PhotoReviews": f"{product_id}/PhotoReviews"
        }
        
        # Завантаження основних фото
        if main_photos:
            logger.info(f"Завантаження {len(main_photos)} основних фото")
            for photo_url in main_photos:
                try:
                    result = cloudinary.uploader.upload(
                        photo_url,
                        folder=folders["MainPhotos"],
                        use_filename=True,
                        unique_filename=False
                    )
                    if result and "url" in result:
                        uploaded_urls["MainPhotos"].append(result["url"])
                        logger.info(f"Завантажено основне фото: {result['url']}")
                except Exception as e:
                    logger.error(f"Помилка завантаження основного фото: {e}")
                    continue
        
        # Завантаження фото відгуків
        if review_photos:
            logger.info(f"Завантаження {len(review_photos)} фото відгуків")
            for photo_url in review_photos:
                try:
                    result = cloudinary.uploader.upload(
                        photo_url,
                        folder=folders["PhotoReviews"],
                        use_filename=True,
                        unique_filename=False
                    )
                    if result and "url" in result:
                        uploaded_urls["PhotoReviews"].append(result["url"])
                        logger.info(f"Завантажено фото відгуку: {result['url']}")
                except Exception as e:
                    logger.error(f"Помилка завантаження фото відгуку: {e}")
                    continue
                    
    except Exception as e:
        logger.error(f"Загальна помилка при завантаженні фото: {e}")
    
    # Формуємо посилання на папки
    cloud_name = os.getenv('CLOUD_NAME')
    hosting_folder_links = [
        f"https://res.cloudinary.com/{cloud_name}/{product_id}/MainPhotos",
        f"https://res.cloudinary.com/{cloud_name}/{product_id}/PhotoReviews"
    ]
    uploaded_urls["HostingFolderLinks"] = hosting_folder_links
    
    return uploaded_urls
