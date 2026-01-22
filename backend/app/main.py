"""
Telegram Mini App - FastAPI Backend
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .config import settings
from .services.database import _db_service, DatabaseService
from .routes import (
    users_router,
    shops_router,
    categories_router,
    products_router,
    cart_router,
    favorites_router,
    orders_router,
    reviews_router,
    subscriptions_router,
    geocode_router,
    promo_router,
    banners_router,
)
from .routes.bot import router as bot_router

# Пути к директориям
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
UPLOADS_DIR = Path(__file__).parent.parent.parent / "uploads"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle управление приложением."""
    # Startup
    global _db_service
    from .services import database
    # Используем путь из настроек, чтобы он был единым для всего приложения
    database._db_service = DatabaseService(db_path=settings.DATABASE_PATH)
    await database._db_service.connect()
    print(f"[OK] Database connected: {settings.DATABASE_PATH}")
    
    # Проверяем и деактивируем товары магазинов с истекшими подписками
    try:
        from .services.subscription_manager import SubscriptionManager
        deactivated_shops = await SubscriptionManager.check_all_expired_subscriptions(database._db_service)
        if deactivated_shops > 0:
            print(f"[SUBSCRIPTION] Deactivated products for {deactivated_shops} shops with expired subscriptions")
    except Exception as sub_check_error:
        print(f"[WARNING] Error checking expired subscriptions: {sub_check_error}")
    
    # Выполняем миграции
    try:
        # Проверяем, существует ли поле product_name в order_items
        columns = await database._db_service.fetch_all("PRAGMA table_info(order_items)")
        column_names = [col["name"] for col in columns]
        
        if "product_name" not in column_names:
            print("[MIGRATION] Adding product_name column to order_items table...")
            await database._db_service.execute(
                "ALTER TABLE order_items ADD COLUMN product_name TEXT"
            )
            # Заполняем существующие записи названиями товаров
            await database._db_service.execute(
                """UPDATE order_items 
                   SET product_name = (
                       SELECT name 
                       FROM products 
                       WHERE products.id = order_items.product_id
                   )
                   WHERE product_id IS NOT NULL AND product_name IS NULL"""
            )
            await database._db_service.commit()
            print("[MIGRATION] product_name column added successfully")
        
        # Проверяем, существует ли таблица shop_requests
        tables = await database._db_service.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='shop_requests'")
        if tables:
            # Проверяем, существует ли поле group_message_id в shop_requests
            shop_request_columns = await database._db_service.fetch_all("PRAGMA table_info(shop_requests)")
            shop_request_column_names = [col["name"] for col in shop_request_columns]
            
            if "group_message_id" not in shop_request_column_names:
                print("[MIGRATION] Adding group_message_id column to shop_requests...")
                await database._db_service.execute(
                    "ALTER TABLE shop_requests ADD COLUMN group_message_id INTEGER"
                )
                await database._db_service.commit()
                print("[MIGRATION] group_message_id column added successfully")
        
        # Проверяем, существует ли таблица shops
        shops_table = await database._db_service.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='shops'")
        if shops_table:
            # Проверяем, существует ли поле city в shops
            shops_columns = await database._db_service.fetch_all("PRAGMA table_info(shops)")
            shops_column_names = [col["name"] for col in shops_columns]
            
            if "city" not in shops_column_names:
                print("[MIGRATION] Adding city column to shops...")
                await database._db_service.execute(
                    "ALTER TABLE shops ADD COLUMN city TEXT"
                )
                await database._db_service.commit()
                print("[MIGRATION] city column added successfully")
        
        # Обновляем рейтинги всех магазинов на основе существующих отзывов
        try:
            shops_with_reviews = await database._db_service.fetch_all(
                """SELECT DISTINCT shop_id FROM shop_reviews"""
            )
            for shop_row in shops_with_reviews:
                shop_id = shop_row["shop_id"]
                stats = await database._db_service.fetch_one(
                    """SELECT 
                          COUNT(*) as total_reviews,
                          ROUND(AVG(rating), 2) as average_rating
                       FROM shop_reviews
                       WHERE shop_id = ?""",
                    (shop_id,)
                )
                if stats:
                    total_reviews = stats["total_reviews"] or 0
                    average_rating = stats["average_rating"] if stats["average_rating"] is not None else None
                    
                    update_data = {
                        "total_reviews": total_reviews
                    }
                    if average_rating is not None:
                        update_data["average_rating"] = average_rating
                    else:
                        update_data["average_rating"] = None
                    
                    set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
                    values = list(update_data.values()) + [shop_id]
                    
                    await database._db_service.execute(
                        f"UPDATE shops SET {set_clause} WHERE id = ?",
                        tuple(values)
                    )
            await database._db_service.commit()
            print("[MIGRATION] Shop ratings updated successfully")
        except Exception as e:
            print(f"[MIGRATION] Error updating shop ratings: {e}")
        
        # Проверяем, существует ли таблица promos
        promos_table = await database._db_service.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='promos'")
        if not promos_table:
            print("[MIGRATION] Creating promos table...")
            await database._db_service.execute("""
                CREATE TABLE IF NOT EXISTS promos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    promo_type TEXT NOT NULL CHECK(promo_type IN ('percent', 'fixed', 'free_delivery')),
                    value DECIMAL(10, 2) NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    use_once INTEGER DEFAULT 0,
                    first_order_only INTEGER DEFAULT 0,
                    shop_id INTEGER,
                    min_order_amount DECIMAL(10, 2),
                    valid_from DATE,
                    valid_until DATE,
                    max_uses INTEGER,
                    current_uses INTEGER DEFAULT 0,
                    usage_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE
                )
            """)
            await database._db_service.commit()
            print("[MIGRATION] promos table created successfully")
        else:
            # Проверяем структуру таблицы и добавляем недостающие колонки
            promos_columns = await database._db_service.fetch_all("PRAGMA table_info(promos)")
            promos_column_names = [col["name"] for col in promos_columns]
            
            # Список обязательных колонок с их определениями
            required_columns = {
                "value": "DECIMAL(10, 2) NOT NULL DEFAULT 0",
                "description": "TEXT",
                "is_active": "INTEGER DEFAULT 1",
                "use_once": "INTEGER DEFAULT 0",
                "first_order_only": "INTEGER DEFAULT 0",
                "shop_id": "INTEGER",
                "min_order_amount": "DECIMAL(10, 2)",
                "valid_from": "DATE",
                "valid_until": "DATE",
                "max_uses": "INTEGER",
                "current_uses": "INTEGER DEFAULT 0",
                "usage_count": "INTEGER DEFAULT 0",
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            }
            
            # Если discount_type или discount_value существуют и имеют NOT NULL без DEFAULT, обновляем их
            if "discount_type" in promos_column_names:
                discount_type_col = next((col for col in promos_columns if col["name"] == "discount_type"), None)
                if discount_type_col and discount_type_col.get("notnull") == 1 and not discount_type_col.get("dflt_value"):
                    print("[MIGRATION] Note: discount_type column exists with NOT NULL constraint")
                    try:
                        await database._db_service.execute(
                            "UPDATE promos SET discount_type = promo_type WHERE discount_type IS NULL OR discount_type = ''"
                        )
                        await database._db_service.commit()
                        print("[MIGRATION] Updated existing promos with discount_type = promo_type")
                    except Exception as e:
                        print(f"[MIGRATION] Could not update discount_type: {e}")
            
            if "discount_value" in promos_column_names:
                discount_value_col = next((col for col in promos_columns if col["name"] == "discount_value"), None)
                if discount_value_col and discount_value_col.get("notnull") == 1 and not discount_value_col.get("dflt_value"):
                    print("[MIGRATION] Note: discount_value column exists with NOT NULL constraint")
                    try:
                        await database._db_service.execute(
                            "UPDATE promos SET discount_value = value WHERE discount_value IS NULL"
                        )
                        await database._db_service.commit()
                        print("[MIGRATION] Updated existing promos with discount_value = value")
                    except Exception as e:
                        print(f"[MIGRATION] Could not update discount_value: {e}")
            
            # Добавляем все недостающие колонки
            for column_name, column_definition in required_columns.items():
                if column_name not in promos_column_names:
                    print(f"[MIGRATION] Adding {column_name} column to promos table...")
                    try:
                        await database._db_service.execute(
                            f"ALTER TABLE promos ADD COLUMN {column_name} {column_definition}"
                        )
                        await database._db_service.commit()
                        print(f"[MIGRATION] {column_name} column added successfully")
                    except Exception as e:
                        print(f"[MIGRATION] Error adding {column_name} column: {e}")
        
        # Проверяем, существует ли таблица shop_requests
        shop_requests_table = await database._db_service.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='shop_requests'")
        if shop_requests_table:
            # Проверяем, существуют ли поля photo_url и shop_id в shop_requests
            shop_requests_columns = await database._db_service.fetch_all("PRAGMA table_info(shop_requests)")
            shop_requests_column_names = [col["name"] for col in shop_requests_columns]
            
            if "photo_url" not in shop_requests_column_names:
                print("[MIGRATION] Adding photo_url column to shop_requests...")
                await database._db_service.execute(
                    "ALTER TABLE shop_requests ADD COLUMN photo_url TEXT"
                )
                await database._db_service.commit()
                print("[MIGRATION] photo_url column added successfully")
            
            if "shop_id" not in shop_requests_column_names:
                print("[MIGRATION] Adding shop_id column to shop_requests...")
                await database._db_service.execute(
                    "ALTER TABLE shop_requests ADD COLUMN shop_id INTEGER"
                )
                await database._db_service.commit()
                print("[MIGRATION] shop_id column added successfully")
        
        # Проверяем, существует ли таблица subscription_plans
        subscription_plans_table = await database._db_service.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='subscription_plans'")
        if not subscription_plans_table:
            print("[MIGRATION] Creating subscription_plans table...")
            await database._db_service.execute("""
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    price DECIMAL(10, 2) NOT NULL,
                    duration_days INTEGER NOT NULL,
                    max_products INTEGER DEFAULT 50,
                    features TEXT DEFAULT '{}',
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await database._db_service.commit()
            print("[MIGRATION] subscription_plans table created successfully")
        
        # Проверяем и добавляем поля для промокодов в таблицу orders
        orders_table = await database._db_service.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
        if orders_table:
            orders_columns = await database._db_service.fetch_all("PRAGMA table_info(orders)")
            orders_column_names = [col["name"] for col in orders_columns]
            
            if "promo_code" not in orders_column_names:
                print("[MIGRATION] Adding promo_code column to orders...")
                await database._db_service.execute(
                    "ALTER TABLE orders ADD COLUMN promo_code TEXT"
                )
                await database._db_service.commit()
                print("[MIGRATION] promo_code column added successfully")
            
            if "promo_discount_amount" not in orders_column_names:
                print("[MIGRATION] Adding promo_discount_amount column to orders...")
                await database._db_service.execute(
                    "ALTER TABLE orders ADD COLUMN promo_discount_amount DECIMAL(10, 2) DEFAULT 0"
                )
                await database._db_service.commit()
                print("[MIGRATION] promo_discount_amount column added successfully")
            
            if "delivery_fee" not in orders_column_names:
                print("[MIGRATION] Adding delivery_fee column to orders...")
                await database._db_service.execute(
                    "ALTER TABLE orders ADD COLUMN delivery_fee DECIMAL(10, 2) DEFAULT 0"
                )
                await database._db_service.commit()
                print("[MIGRATION] delivery_fee column added successfully")
        
        # Проверяем, существует ли таблица banners
        banners_table = await database._db_service.fetch_all("SELECT name FROM sqlite_master WHERE type='table' AND name='banners'")
        if not banners_table:
            print("[MIGRATION] Creating banners table...")
            await database._db_service.execute("""
                CREATE TABLE IF NOT EXISTS banners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    emoji TEXT,
                    description TEXT,
                    image_url TEXT,
                    link_type TEXT DEFAULT 'none' CHECK(link_type IN ('none', 'category', 'product', 'shop', 'external')),
                    link_value TEXT,
                    display_order INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await database._db_service.commit()
            print("[MIGRATION] banners table created successfully")
    
    except Exception as migration_error:
        print(f"[WARNING] Migration error (may be expected if column exists): {migration_error}")
        try:
            await database._db_service.rollback()
        except:
            pass
    
    yield
    
    # Shutdown
    if database._db_service:
        await database._db_service.disconnect()
        print("[OK] Database disconnected")


# Создаём приложение
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API для Telegram Mini App - Маркетплейс цветов и подарков",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(users_router, prefix="/api/users", tags=["Users"])

# Регистрируем маршруты /my и /my/statistics напрямую ПЕРЕД подключением shops_router
# чтобы они не перехватывались маршрутом /{shop_id}
from .routes.users import get_current_user
from .models.shop import ShopWithStats
from .routes.shops import ShopStatistics, get_shop_statistics
from .services.database import get_db
from .models.user import User
from fastapi import Depends, Query
from typing import Optional

# Регистрируем маршрут /my/statistics с помощью add_api_route для явного контроля приоритета
async def get_shop_statistics_direct(
    start_date: Optional[str] = Query(None, description="Дата начала в формате YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Дата окончания в формате YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Получает статистику магазина за указанный период."""
    import sys
    print(f"[MAIN.PY] /api/shops/my/statistics called: start_date={start_date}, end_date={end_date}, user_id={current_user.id}", file=sys.stderr, flush=True)
    try:
        result = await get_shop_statistics(start_date, end_date, current_user, db)
        print(f"[MAIN.PY] Statistics returned successfully", file=sys.stderr, flush=True)
        return result
    except Exception as e:
        print(f"[MAIN.PY] Error in get_shop_statistics: {e}", file=sys.stderr, flush=True)
        raise

# Используем add_api_route для явной регистрации маршрута
# ВАЖНО: Этот маршрут должен быть зарегистрирован ПЕРЕД подключением shops_router
app.add_api_route(
    "/api/shops/my/statistics",
    get_shop_statistics_direct,
    methods=["GET"],
    response_model=ShopStatistics,
    tags=["Shops"],
    name="get_shop_statistics"
)

# Простой тестовый эндпоинт для проверки, что маршрут работает
@app.get("/api/shops/test-statistics")
async def test_statistics_route():
    """Тестовый эндпоинт для проверки регистрации маршрута статистики."""
    routes_with_statistics = [
        {
            'path': route.path,
            'methods': list(route.methods) if hasattr(route, 'methods') and route.methods else [],
            'name': getattr(route, 'name', 'unknown')
        }
        for route in app.routes
        if hasattr(route, 'path') and '/my/statistics' in route.path
    ]
    return {
        'statistics_routes': routes_with_statistics,
        'total_found': len(routes_with_statistics),
        'message': 'Проверка регистрации маршрута /api/shops/my/statistics'
    }

# Тестовый эндпоинт для проверки регистрации маршрутов
@app.get("/api/test-routes")
async def test_routes():
    """Проверка зарегистрированных маршрутов."""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            if '/shops' in route.path:
                routes.append({
                    'path': route.path,
                    'methods': list(route.methods) if route.methods else [],
                    'name': getattr(route, 'name', 'unknown')
                })
    # Сортируем по пути для удобства
    routes.sort(key=lambda x: x['path'])
    return {
        'shops_routes': routes,
        'statistics_route_exists': any('/my/statistics' in r.path for r in app.routes if hasattr(r, 'path')),
        'total_routes': len([r for r in app.routes if hasattr(r, 'path') and '/shops' in r.path])
    }

@app.get("/api/shops/my", response_model=Optional[ShopWithStats], tags=["Shops"])
async def get_my_shop_direct(
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Получает магазин текущего пользователя."""
    shop = await db.fetch_one(
        "SELECT * FROM shops WHERE owner_id = ?",
        (current_user.id,)
    )
    if not shop:
        return None
    
    # Получаем статистику
    products_count = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM products WHERE shop_id = ? AND is_active = 1 AND quantity > 0",
        (shop["id"],)
    )
    orders_count = await db.fetch_one(
        "SELECT COUNT(*) as cnt FROM orders WHERE shop_id = ?",
        (shop["id"],)
    )
    subscription = await db.fetch_one(
        """SELECT * FROM shop_subscriptions 
           WHERE shop_id = ? AND is_active = 1 AND end_date > datetime('now')""",
        (shop["id"],)
    )
    
    return ShopWithStats(
        **shop,
        products_count=products_count["cnt"],
        orders_count=orders_count["cnt"],
        subscription_active=subscription is not None
    )

app.include_router(shops_router, prefix="/api/shops", tags=["Shops"])
app.include_router(categories_router, prefix="/api/categories", tags=["Categories"])
app.include_router(products_router, prefix="/api/products", tags=["Products"])
app.include_router(cart_router, prefix="/api/cart", tags=["Cart"])
app.include_router(favorites_router, prefix="/api/favorites", tags=["Favorites"])
app.include_router(orders_router, prefix="/api/orders", tags=["Orders"])
app.include_router(reviews_router, prefix="/api/reviews", tags=["Reviews"])
# ВРЕМЕННЫЙ ДУБЛИРУЮЩИЙ ЭНДПОИНТ ДЛЯ ДИАГНОСТИКИ - регистрируем ДО подключения роутера
from .routes.subscriptions import request_subscription_payment
from .routes.users import get_current_user as get_user
from .services.database import get_db as get_database
from fastapi import Depends

@app.post("/api/subscriptions/request-payment-direct/{plan_id}", tags=["Subscriptions-Debug"])
async def request_subscription_payment_direct(
    plan_id: int,
    current_user = Depends(get_user),
    db = Depends(get_database)
):
    """Дублирующий эндпоинт для диагностики - вызывает оригинальную функцию."""
    print(f"[DEBUG] Direct endpoint called with plan_id={plan_id}")
    return await request_subscription_payment(plan_id, current_user, db)

app.include_router(subscriptions_router, prefix="/api/subscriptions", tags=["Subscriptions"])

app.include_router(geocode_router, prefix="/api/geocode", tags=["Geocode"])
app.include_router(promo_router, prefix="/api/promo", tags=["Promo"])
app.include_router(banners_router, prefix="/api/banners", tags=["Banners"])
app.include_router(bot_router, prefix="/api/bot", tags=["Bot"])

# Admin router
from .routes.admin import router as admin_router
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])


@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Проверка здоровья сервиса."""
    return {"status": "healthy"}


@app.get("/api/config")
async def get_config():
    """Возвращает публичную конфигурацию для фронтенда."""
    return {
        "yandex_api_key": settings.YANDEX_API_KEY if settings.YANDEX_API_KEY else None
    }


@app.get("/")
async def root():
    """Главная страница - полная версия приложения."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(
            index_path,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache",
                "X-Content-Type-Options": "nosniff"
            }
        )
    return {"message": "Frontend not found", "path": str(index_path)}


@app.get("/test_connection.html")
async def test_connection():
    """Страница для тестирования подключения к API."""
    test_path = Path(__file__).parent.parent.parent / "test_connection.html"
    if test_path.exists():
        return FileResponse(
            test_path,
            media_type="text/html",
            headers={"Cache-Control": "no-cache"}
        )
    return {"message": "Test page not found"}

@app.get("/full")
async def full_app():
    """Полная версия приложения."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(
            index_path,
            media_type="text/html",
            headers={"Cache-Control": "no-cache"}
        )
    return {"message": "Frontend not found", "path": str(index_path)}


@app.get("/app")
async def webapp():
    """Mini App страница."""
    return FileResponse(
        FRONTEND_DIR / "index.html",
        media_type="text/html",
        headers={"Cache-Control": "no-cache"}
    )


# Статические файлы frontend (монтируем в конце, ВАЖНО: после всех роутов!)
# Также добавляем роут для debug.html
@app.get("/simple_test.html")
async def simple_test():
    """Простая тестовая страница."""
    test_path = FRONTEND_DIR / "simple_test.html"
    if test_path.exists():
        return FileResponse(
            test_path,
            media_type="text/html",
            headers={"Cache-Control": "no-cache"}
        )
    return {"message": "Test page not found"}

@app.get("/minimal.html")
async def minimal():
    """Минимальная тестовая страница."""
    path = FRONTEND_DIR / "minimal.html"
    if path.exists():
        return FileResponse(
            path,
            media_type="text/html",
            headers={"Cache-Control": "no-cache"}
        )
    return {"message": "Page not found"}

@app.get("/debug.html")
async def debug():
    """Страница диагностики."""
    debug_path = FRONTEND_DIR / "debug.html"
    if debug_path.exists():
        return FileResponse(
            debug_path,
            media_type="text/html",
            headers={"Cache-Control": "no-cache"}
        )
    return {"message": "Debug page not found"}

@app.get("/test.html")
async def test():
    """Тестовая страница."""
    test_path = FRONTEND_DIR / "test.html"
    if test_path.exists():
        return FileResponse(
            test_path,
            media_type="text/html",
            headers={"Cache-Control": "no-cache"}
        )
    return {"message": "Test page not found"}

@app.get("/test_browser.html")
async def test_browser():
    """Тестовая страница для диагностики."""
    test_path = Path(__file__).parent.parent.parent / "test_browser.html"
    if test_path.exists():
        return FileResponse(
            test_path,
            media_type="text/html",
            headers={"Cache-Control": "no-cache"}
        )
    return {"message": "Test browser page not found"}

@app.get("/test_simple.html")
async def test_simple():
    """Простая тестовая страница."""
    test_path = FRONTEND_DIR / "test_simple.html"
    if test_path.exists():
        return FileResponse(
            test_path,
            media_type="text/html",
            headers={"Cache-Control": "no-cache"}
        )
    return {"message": "Test simple page not found"}

# Монтируем статические файлы ПОСЛЕ всех роутов
if (FRONTEND_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
if (FRONTEND_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
if (FRONTEND_DIR / "images").exists():
    app.mount("/images", StaticFiles(directory=FRONTEND_DIR / "images"), name="images")
if (FRONTEND_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

# Раздача медиа файлов (товары и магазины)
# Создаём специальный роут для видео с поддержкой range requests
@app.get("/media/{path:path}")
async def serve_media(path: str, request: Request = None):
    """Отдает медиа файлы с правильными MIME-типами и поддержкой range requests для видео."""
    from fastapi.responses import Response, StreamingResponse
    from fastapi import Request, HTTPException
    import aiofiles
    import os
    
    file_path = UPLOADS_DIR / path
    
    # Проверяем существование файла
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Определяем MIME-тип по расширению
    extension = file_path.suffix.lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.gif': 'image/gif',
    }
    media_type = mime_types.get(extension, 'application/octet-stream')
    
    file_size = file_path.stat().st_size
    
    # Для видео файлов добавляем поддержку range requests
    if extension in ['.mp4', '.webm']:
        range_header = request.headers.get('range') if request else None
        
        if range_header:
            # Парсим range header (например: "bytes=0-1023")
            import re
            match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else file_size - 1
                
                # Ограничиваем диапазон размером файла
                end = min(end, file_size - 1)
                content_length = end - start + 1
                
                async def generate():
                    async with aiofiles.open(file_path, 'rb') as f:
                        await f.seek(start)
                        remaining = content_length
                        while remaining > 0:
                            chunk_size = min(8192, remaining)
                            chunk = await f.read(chunk_size)
                            if not chunk:
                                break
                            remaining -= len(chunk)
                            yield chunk
                
                headers = {
                    'Content-Range': f'bytes {start}-{end}/{file_size}',
                    'Accept-Ranges': 'bytes',
                    'Content-Length': str(content_length),
                    'Content-Type': media_type,
                }
                
                return StreamingResponse(
                    generate(),
                    status_code=206,  # Partial Content
                    headers=headers,
                    media_type=media_type
                )
        
        # Если нет range header, возвращаем весь файл
        headers = {
            'Accept-Ranges': 'bytes',
            'Content-Length': str(file_size),
            'Content-Type': media_type,
        }
        
        async def generate_full():
            async with aiofiles.open(file_path, 'rb') as f:
                while True:
                    chunk = await f.read(8192)
                    if not chunk:
                        break
                    yield chunk
        
        return StreamingResponse(
            generate_full(),
            headers=headers,
            media_type=media_type
        )
    
    # Для изображений используем обычный FileResponse
    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(file_path),
        media_type=media_type
    )

# Также монтируем статику для обратной совместимости (но роут выше будет иметь приоритет)
if UPLOADS_DIR.exists():
    try:
        app.mount("/media-static", StaticFiles(directory=UPLOADS_DIR), name="media-static")
    except Exception:
        pass  # Может быть уже смонтировано

