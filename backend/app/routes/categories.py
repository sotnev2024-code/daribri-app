"""
API Routes для категорий.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from ..models.category import Category, CategoryWithChildren
from ..services.database import DatabaseService, get_db

router = APIRouter()


@router.get("/", response_model=List[CategoryWithChildren])
async def get_categories(
    db: DatabaseService = Depends(get_db)
):
    """Получает дерево категорий."""
    # Получаем все категории
    all_categories = await db.fetch_all(
        """SELECT c.*, 
                  (SELECT COUNT(*) FROM products p WHERE p.category_id = c.id AND p.is_active = 1) as products_count
           FROM categories c 
           WHERE c.is_active = 1 
           ORDER BY c.sort_order"""
    )
    
    # Строим дерево
    categories_dict = {cat["id"]: {**cat, "children": []} for cat in all_categories}
    root_categories = []
    
    for cat in all_categories:
        if cat["parent_id"] is None:
            root_categories.append(categories_dict[cat["id"]])
        else:
            parent = categories_dict.get(cat["parent_id"])
            if parent:
                parent["children"].append(categories_dict[cat["id"]])
    
    return [CategoryWithChildren(**cat) for cat in root_categories]


@router.get("/flat", response_model=List[Category])
async def get_categories_flat(
    db: DatabaseService = Depends(get_db)
):
    """Получает плоский список всех категорий."""
    categories = await db.fetch_all(
        "SELECT * FROM categories WHERE is_active = 1 ORDER BY sort_order"
    )
    return [Category(**cat) for cat in categories]


@router.get("/{category_id}", response_model=CategoryWithChildren)
async def get_category(
    category_id: int,
    db: DatabaseService = Depends(get_db)
):
    """Получает категорию по ID с подкатегориями."""
    category = await db.fetch_one(
        """SELECT c.*, 
                  (SELECT COUNT(*) FROM products p WHERE p.category_id = c.id AND p.is_active = 1) as products_count
           FROM categories c 
           WHERE c.id = ? AND c.is_active = 1""",
        (category_id,)
    )
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Получаем подкатегории
    children = await db.fetch_all(
        """SELECT c.*, 
                  (SELECT COUNT(*) FROM products p WHERE p.category_id = c.id AND p.is_active = 1) as products_count
           FROM categories c 
           WHERE c.parent_id = ? AND c.is_active = 1 
           ORDER BY c.sort_order""",
        (category_id,)
    )
    
    return CategoryWithChildren(
        **category,
        children=[CategoryWithChildren(**child, children=[]) for child in children]
    )


@router.get("/{category_id}/products")
async def get_category_products(
    category_id: int,
    include_subcategories: bool = True,
    skip: int = 0,
    limit: int = 20,
    db: DatabaseService = Depends(get_db)
):
    """Получает товары категории."""
    if include_subcategories:
        # Получаем ID всех подкатегорий
        subcategories = await db.fetch_all(
            "SELECT id FROM categories WHERE parent_id = ? AND is_active = 1",
            (category_id,)
        )
        category_ids = [category_id] + [s["id"] for s in subcategories]
        placeholders = ",".join(["?" for _ in category_ids])
        
        products = await db.fetch_all(
            f"""SELECT p.*, 
                       s.name as shop_name,
                       (SELECT url FROM product_media WHERE product_id = p.id AND is_primary = 1 LIMIT 1) as primary_image
                FROM products p
                JOIN shops s ON p.shop_id = s.id
                WHERE p.category_id IN ({placeholders}) AND p.is_active = 1 AND p.quantity > 0 AND s.is_active = 1
                AND EXISTS (
                    SELECT 1 FROM shop_subscriptions ss 
                    WHERE ss.shop_id = s.id 
                    AND ss.is_active = 1 
                    AND ss.end_date > datetime('now')
                )
                ORDER BY p.created_at DESC
                LIMIT ? OFFSET ?""",
            tuple(category_ids) + (limit, skip)
        )
    else:
        products = await db.fetch_all(
            """SELECT p.*, 
                      s.name as shop_name,
                      (SELECT url FROM product_media WHERE product_id = p.id AND is_primary = 1 LIMIT 1) as primary_image
               FROM products p
               JOIN shops s ON p.shop_id = s.id
               WHERE p.category_id = ? AND p.is_active = 1 AND p.quantity > 0 AND s.is_active = 1
               AND EXISTS (
                   SELECT 1 FROM shop_subscriptions ss 
                   WHERE ss.shop_id = s.id 
                   AND ss.is_active = 1 
                   AND ss.end_date > datetime('now')
               )
               ORDER BY p.created_at DESC
               LIMIT ? OFFSET ?""",
            (category_id, limit, skip)
        )
    
    return products






