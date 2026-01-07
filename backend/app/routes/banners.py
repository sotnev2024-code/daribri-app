"""
API Routes для баннеров.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from datetime import datetime

from ..models.banner import Banner, BannerCreate, BannerUpdate
from ..models.user import User
from ..services.database import DatabaseService, get_db
from ..services.media import get_media_service
from .users import get_current_user

router = APIRouter()


@router.get("/", response_model=List[Banner])
async def get_banners(
    active_only: bool = True,
    db: DatabaseService = Depends(get_db)
):
    """Получает список баннеров."""
    conditions = []
    params = []
    
    if active_only:
        conditions.append("is_active = 1")
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    banners = await db.fetch_all(
        f"""
        SELECT * FROM banners
        {where_clause}
        ORDER BY display_order ASC, created_at DESC
        """,
        tuple(params)
    )
    
    return [Banner(**banner) for banner in banners]


@router.post("/", response_model=Banner)
async def create_banner(
    banner_data: BannerCreate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Создает новый баннер. Только для администраторов."""
    # TODO: Добавить проверку на администратора
    
    banner_dict = banner_data.model_dump()
    banner_dict["created_at"] = datetime.now()
    banner_dict["updated_at"] = datetime.now()
    
    banner_id = await db.insert("banners", banner_dict)
    await db.commit()
    
    banner = await db.fetch_one("SELECT * FROM banners WHERE id = ?", (banner_id,))
    return Banner(**banner)


@router.get("/{banner_id}", response_model=Banner)
async def get_banner(
    banner_id: int,
    db: DatabaseService = Depends(get_db)
):
    """Получает баннер по ID."""
    banner = await db.fetch_one("SELECT * FROM banners WHERE id = ?", (banner_id,))
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    return Banner(**banner)


@router.put("/{banner_id}", response_model=Banner)
async def update_banner(
    banner_id: int,
    banner_update: BannerUpdate,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Обновляет баннер. Только для администраторов."""
    # TODO: Добавить проверку на администратора
    
    banner = await db.fetch_one("SELECT * FROM banners WHERE id = ?", (banner_id,))
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    update_data = banner_update.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.now()
        await db.update("banners", update_data, "id = ?", (banner_id,))
        await db.commit()
    
    updated = await db.fetch_one("SELECT * FROM banners WHERE id = ?", (banner_id,))
    return Banner(**updated)


@router.delete("/{banner_id}")
async def delete_banner(
    banner_id: int,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Удаляет баннер. Только для администраторов."""
    # TODO: Добавить проверку на администратора
    
    banner = await db.fetch_one("SELECT * FROM banners WHERE id = ?", (banner_id,))
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    await db.delete("banners", "id = ?", (banner_id,))
    await db.commit()
    
    return {"message": "Banner deleted successfully"}


@router.post("/upload", response_model=dict)
async def upload_banner_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db)
):
    """Загружает изображение баннера."""
    # TODO: Добавить проверку на администратора
    
    media_service = get_media_service()
    
    # Читаем содержимое файла
    contents = await file.read()
    
    # Сохраняем файл через media service
    file_url = await media_service.save_file(
        file=contents,
        filename=file.filename,
        folder="banners"
    )
    
    return {"url": file_url}


