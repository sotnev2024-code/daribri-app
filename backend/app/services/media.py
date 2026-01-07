"""
Сервис для работы с медиа файлами товаров.
"""

import hashlib
import shutil
import os
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
import aiofiles

from ..config import settings


class MediaService:
    """Сервис для работы с медиа файлами."""
    
    def __init__(self):
        self.media_dir = settings.PRODUCTS_MEDIA_DIR
        self.max_size = settings.MAX_FILE_SIZE
        self.allowed_images = settings.ALLOWED_IMAGE_TYPES
        self.allowed_videos = settings.ALLOWED_VIDEO_TYPES
        
        # Создаём директории при инициализации
        self.media_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_shop_photo(
        self,
        file: UploadFile,
        shop_id: int
    ) -> Tuple[str, str]:
        """
        Сохраняет фото магазина на диск.
        
        Args:
            file: Загружаемый файл
            shop_id: ID магазина
            
        Returns:
            Tuple[str, str]: (относительный URL, полный путь к файлу)
            
        Raises:
            HTTPException: Если файл невалидный
        """
        # Валидация размера
        content = await file.read()
        await file.seek(0)
        
        if len(content) > self.max_size:
            raise HTTPException(
                status_code=413,
                detail=f"Файл слишком большой. Максимальный размер: {self.max_size / 1024 / 1024:.1f} MB"
            )
        
        # Валидация типа файла
        content_type = file.content_type
        if content_type not in self.allowed_images:
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый тип файла: {content_type}. Разрешены: {', '.join(self.allowed_images)}"
            )
        
        # Создаём хэш для уникального имени
        file_hash = hashlib.md5(content).hexdigest()[:12]
        
        # Определяем расширение файла
        original_filename = file.filename or "file"
        extension = Path(original_filename).suffix.lower()
        if not extension:
            extension_map = {
                "image/jpeg": ".jpg",
                "image/jpg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
            }
            extension = extension_map.get(content_type, ".jpg")
        
        # Создаём папку для фото магазинов
        shops_photos_dir = self.media_dir.parent / "shops"
        shops_photos_dir.mkdir(parents=True, exist_ok=True)
        shop_dir = shops_photos_dir / str(shop_id)
        shop_dir.mkdir(parents=True, exist_ok=True)
        
        # Генерируем имя файла
        filename = f"photo_{file_hash}{extension}"
        file_path = shop_dir / filename
        
        # Сохраняем файл
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Возвращаем относительный URL и полный путь
        relative_url = f"/media/shops/{shop_id}/{filename}"
        return relative_url, str(file_path)
    
    async def save_media(
        self, 
        file: UploadFile, 
        product_id: int,
        is_primary: bool = False
    ) -> Tuple[str, str]:
        """
        Сохраняет медиа файл на диск.
        
        Args:
            file: Загружаемый файл
            product_id: ID товара
            is_primary: Является ли главным изображением
            
        Returns:
            Tuple[str, str]: (относительный URL, полный путь к файлу)
            
        Raises:
            HTTPException: Если файл невалидный
        """
        # Валидация размера
        if hasattr(file, 'size') and file.size and file.size > self.max_size:
            raise HTTPException(
                status_code=413,
                detail=f"Файл слишком большой. Максимальный размер: {self.max_size / 1024 / 1024:.1f} MB"
            )
        
        # Валидация типа файла
        content_type = file.content_type
        media_type = None
        
        if content_type in self.allowed_images:
            media_type = "photo"
        elif content_type in self.allowed_videos:
            media_type = "video"
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый тип файла: {content_type}. "
                       f"Разрешены: {', '.join(self.allowed_images + self.allowed_videos)}"
            )
        
        # Читаем содержимое для проверки размера и создания хэша
        content = await file.read()
        await file.seek(0)  # Возвращаем курсор в начало
        
        # Проверка размера по содержимому
        if len(content) > self.max_size:
            raise HTTPException(
                status_code=413,
                detail=f"Файл слишком большой. Максимальный размер: {self.max_size / 1024 / 1024:.1f} MB"
            )
        
        # Создаём хэш для уникального имени
        file_hash = hashlib.md5(content).hexdigest()[:12]
        
        # Определяем расширение файла
        original_filename = file.filename or "file"
        extension = Path(original_filename).suffix.lower()
        if not extension:
            # Определяем расширение по content_type
            extension_map = {
                "image/jpeg": ".jpg",
                "image/jpg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
                "video/mp4": ".mp4",
                "video/webm": ".webm",
            }
            extension = extension_map.get(content_type, ".bin")
        
        # Создаём структуру папок: uploads/products/{product_id}/
        product_dir = self.media_dir / str(product_id)
        product_dir.mkdir(parents=True, exist_ok=True)
        
        # Генерируем имя файла
        prefix = "primary" if is_primary else "media"
        filename = f"{prefix}_{file_hash}{extension}"
        file_path = product_dir / filename
        
        # Сохраняем файл
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Возвращаем относительный URL и полный путь
        relative_url = f"/media/products/{product_id}/{filename}"
        return relative_url, str(file_path)
    
    async def delete_media(self, url: str) -> bool:
        """
        Удаляет медиа файл по URL.
        
        Args:
            url: Относительный URL файла (например, /media/products/1/primary_abc123.jpg)
            
        Returns:
            bool: True если файл удалён, False если не найден
        """
        if not url.startswith("/media/products/"):
            # Если это внешний URL или base64, не удаляем
            return False
        
        # Извлекаем путь к файлу
        parts = url.split("/")
        if len(parts) < 5:
            return False
        
        product_id = parts[3]
        filename = parts[4]
        file_path = self.media_dir / product_id / filename
        
        if file_path.exists():
            try:
                os.remove(file_path)
                return True
            except Exception as e:
                print(f"[ERROR] Ошибка удаления файла {file_path}: {e}")
                return False
        
        return False
    
    async def delete_product_media(self, product_id: int) -> bool:
        """
        Удаляет все медиа файлы товара.
        
        Args:
            product_id: ID товара
            
        Returns:
            bool: True если папка удалена, False если не найдена
        """
        product_dir = self.media_dir / str(product_id)
        if product_dir.exists():
            try:
                shutil.rmtree(product_dir)
                return True
            except Exception as e:
                print(f"[ERROR] Ошибка удаления папки {product_dir}: {e}")
                return False
        return False
    
    def get_file_path(self, url: str) -> Optional[Path]:
        """
        Возвращает путь к файлу по URL.
        
        Args:
            url: Относительный URL файла
            
        Returns:
            Path или None если URL не локальный
        """
        if not url.startswith("/media/products/"):
            return None
        
        parts = url.split("/")
        if len(parts) < 5:
            return None
        
        product_id = parts[3]
        filename = parts[4]
        return self.media_dir / product_id / filename


# Глобальный экземпляр сервиса
_media_service: Optional[MediaService] = None


def get_media_service() -> MediaService:
    """Возвращает экземпляр MediaService."""
    global _media_service
    if _media_service is None:
        _media_service = MediaService()
    return _media_service

