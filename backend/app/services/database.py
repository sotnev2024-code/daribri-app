"""
Сервис для работы с базой данных SQLite.
"""

import aiosqlite
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager


# Путь к базе данных
DATABASE_PATH = Path(__file__).parent.parent.parent.parent / "database" / "miniapp.db"


class DatabaseService:
    """Асинхронный сервис для работы с SQLite."""
    
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> None:
        """Устанавливает соединение с базой данных."""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA foreign_keys = ON")
        await self._connection.execute("PRAGMA encoding = 'UTF-8'")
    
    async def disconnect(self) -> None:
        """Закрывает соединение с базой данных."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    @property
    def connection(self) -> aiosqlite.Connection:
        """Возвращает текущее соединение."""
        if not self._connection:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._connection
    
    async def execute(
        self, 
        query: str, 
        params: tuple = ()
    ) -> aiosqlite.Cursor:
        """Выполняет SQL запрос."""
        return await self.connection.execute(query, params)
    
    async def executemany(
        self, 
        query: str, 
        params_list: List[tuple]
    ) -> aiosqlite.Cursor:
        """Выполняет SQL запрос для множества параметров."""
        return await self.connection.executemany(query, params_list)
    
    async def commit(self) -> None:
        """Фиксирует транзакцию."""
        await self.connection.commit()
    
    async def rollback(self) -> None:
        """Откатывает транзакцию."""
        await self.connection.rollback()
    
    async def fetch_one(
        self, 
        query: str, 
        params: tuple = ()
    ) -> Optional[Dict[str, Any]]:
        """Выполняет запрос и возвращает одну строку."""
        cursor = await self.execute(query, params)
        row = await cursor.fetchone()
        return dict(row) if row else None
    
    async def fetch_all(
        self, 
        query: str, 
        params: tuple = ()
    ) -> List[Dict[str, Any]]:
        """Выполняет запрос и возвращает все строки."""
        cursor = await self.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def insert(
        self, 
        table: str, 
        data: Dict[str, Any]
    ) -> int:
        """Вставляет запись и возвращает ID."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        cursor = await self.execute(query, tuple(data.values()))
        await self.commit()
        return cursor.lastrowid
    
    async def update(
        self, 
        table: str, 
        data: Dict[str, Any], 
        where: str, 
        where_params: tuple = ()
    ) -> int:
        """Обновляет записи и возвращает количество затронутых строк."""
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        
        cursor = await self.execute(query, tuple(data.values()) + where_params)
        await self.commit()
        return cursor.rowcount
    
    async def delete(
        self, 
        table: str, 
        where: str, 
        where_params: tuple = ()
    ) -> int:
        """Удаляет записи и возвращает количество затронутых строк."""
        query = f"DELETE FROM {table} WHERE {where}"
        cursor = await self.execute(query, where_params)
        await self.commit()
        return cursor.rowcount


# Глобальный экземпляр сервиса
_db_service: Optional[DatabaseService] = None


async def get_db() -> AsyncGenerator[DatabaseService, None]:
    """Dependency для FastAPI - возвращает сервис базы данных."""
    global _db_service
    
    if _db_service is None:
        # Используем глобальный экземпляр, если он уже создан в lifespan
        # Иначе создаем новый с путем по умолчанию
        _db_service = DatabaseService()
        await _db_service.connect()
    
    try:
        yield _db_service
    except Exception:
        await _db_service.rollback()
        raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[DatabaseService, None]:
    """Контекстный менеджер для работы с базой данных."""
    db = DatabaseService()
    await db.connect()
    try:
        yield db
    finally:
        await db.disconnect()






