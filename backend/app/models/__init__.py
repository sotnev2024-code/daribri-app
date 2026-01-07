"""
Модели данных для Telegram Mini App.
"""

from .user import User, UserCreate, UserUpdate
from .shop import Shop, ShopCreate, ShopUpdate, ShopWithStats
from .category import Category, CategoryWithChildren
from .product import Product, ProductCreate, ProductUpdate, ProductWithMedia
from .cart import CartItem, CartItemCreate, CartItemUpdate
from .favorite import Favorite, FavoriteCreate
from .order import Order, OrderCreate, OrderItem, OrderWithItems
from .review import ShopReview, ShopReviewCreate
from .subscription import SubscriptionPlan, ShopSubscription
from .banner import Banner, BannerCreate, BannerUpdate

__all__ = [
    # User
    "User", "UserCreate", "UserUpdate",
    # Shop
    "Shop", "ShopCreate", "ShopUpdate", "ShopWithStats",
    # Category
    "Category", "CategoryWithChildren",
    # Product
    "Product", "ProductCreate", "ProductUpdate", "ProductWithMedia",
    # Cart
    "CartItem", "CartItemCreate", "CartItemUpdate",
    # Favorite
    "Favorite", "FavoriteCreate",
    # Order
    "Order", "OrderCreate", "OrderItem", "OrderWithItems",
    # Review
    "ShopReview", "ShopReviewCreate",
    # Subscription
    "SubscriptionPlan", "ShopSubscription",
    # Banner
    "Banner", "BannerCreate", "BannerUpdate",
]






