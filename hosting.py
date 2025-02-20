import os
import logging
import cloudinary
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError

# Налаштування логування
logger = logging.getLogger(__name__)

# Налаштування Cloudinary
# https://console.cloudinary.com/settings/c-6f5534e46e74f613fa802f99963078/api-keys


cloudinary.config(
    cloud_name= 'dtvxnruxj',
    api_key= '932412845955356',
    api_secret= 'O0z4A7hR3wQFgCYSu7J_o2MX71k',
    secure=True
)

def upload_photos(photo_links: list, folder_name: str) -> list[str]:
    """
    Завантажує фото на хостинг та повертає список посилань на завантажені фото.
    """
    photos_url = []
    if not photo_links:
        logger.warning("Список фото порожній")
        return photos_url
        
    for photo_link in photo_links:
        if not photo_link:
            continue
            
        try:
            # Перевірка та виправлення URL
            if not photo_link.startswith(('http://', 'https://')):
                photo_link = f"https:{photo_link}"
            
            # Завантаження фото з додатковими параметрами
            response = cloudinary.uploader.upload(
                photo_link, 
                folder=folder_name,
                timeout=30,
                format='jpg',  # Конвертуємо всі фото в jpg
                quality='auto:good',  # Автоматична оптимізація якості
                fetch_format='auto'  # Автоматичний формат доставки
            )
            
            secure_url = response.get("secure_url")
            if secure_url:
                photos_url.append(secure_url)
                logger.info(f"Фото успішно завантажено: {secure_url}")
            else:
                logger.warning(f"Не отримано URL для фото: {photo_link}")
                
        except CloudinaryError as ce:
            logger.error(f"Помилка Cloudinary для {photo_link}: {str(ce)}")
            continue
        except Exception as e:
            logger.error(f"Загальна помилка для {photo_link}: {str(e)}")
            continue
            
    logger.info(f"Завантажено {len(photos_url)} з {len(photo_links)} фото")
    return photos_url
