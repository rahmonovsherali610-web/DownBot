"""PostgreSQL ma'lumotlar bazasi bilan ishlash moduli."""

import asyncpg
import logging
from datetime import datetime, timezone
from typing import Optional

from config import DATABASE_URL

logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL bazasi bilan asinxron ishlash."""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Bazaga ulanish poolini yaratish."""
        try:
            self.pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=60,
            )
            await self._create_tables()
            logger.info("✅ PostgreSQL bazasiga muvaffaqiyatli ulandi.")
        except Exception as e:
            logger.error(f"❌ PostgreSQL ulanish xatosi: {e}")
            raise

    async def disconnect(self):
        """Bazadan uzilish."""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL ulanishi yopildi.")

    async def _create_tables(self):
        """Kerakli jadvallarni yaratish."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    full_name VARCHAR(512),
                    is_banned BOOLEAN DEFAULT FALSE,
                    ban_reason VARCHAR(1024),
                    ban_until TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    last_active TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    url TEXT,
                    media_type VARCHAR(10),
                    quality VARCHAR(50),
                    file_size BIGINT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS error_reports (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    report_text TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            logger.info("✅ Jadvallar muvaffaqiyatli yaratildi/tekshirildi.")

    # ===== Foydalanuvchi operatsiyalari =====

    async def add_user(self, user_id: int, username: str = None, full_name: str = None):
        """Yangi foydalanuvchi qo'shish yoki mavjudini yangilash."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO users (user_id, username, full_name, last_active)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        username = COALESCE($2, users.username),
                        full_name = COALESCE($3, users.full_name),
                        last_active = $4
                """, user_id, username, full_name, datetime.now(timezone.utc))
        except Exception as e:
            logger.error(f"Foydalanuvchi qo'shish xatosi: {e}")

    async def get_user(self, user_id: int) -> Optional[dict]:
        """Foydalanuvchi ma'lumotlarini olish."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM users WHERE user_id = $1", user_id
                )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Foydalanuvchi olish xatosi: {e}")
            return None

    async def is_banned(self, user_id: int) -> tuple[bool, Optional[str]]:
        """Foydalanuvchi ban qilinganmi tekshirish."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT is_banned, ban_reason, ban_until FROM users WHERE user_id = $1",
                    user_id,
                )
                if not row:
                    return False, None
                if row["is_banned"]:
                    # Vaqtinchalik ban muddati tugaganmi?
                    if row["ban_until"] and row["ban_until"] < datetime.now(timezone.utc):
                        await self.unban_user(user_id)
                        return False, None
                    return True, row["ban_reason"]
                return False, None
        except Exception as e:
            logger.error(f"Ban tekshirish xatosi: {e}")
            return False, None

    async def ban_user(self, user_id: int, reason: str = None, until: datetime = None):
        """Foydalanuvchini ban qilish."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE users SET is_banned = TRUE, ban_reason = $2, ban_until = $3
                    WHERE user_id = $1
                """, user_id, reason, until)
        except Exception as e:
            logger.error(f"Ban qilish xatosi: {e}")

    async def unban_user(self, user_id: int):
        """Foydalanuvchi banini olib tashlash."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE users SET is_banned = FALSE, ban_reason = NULL, ban_until = NULL
                    WHERE user_id = $1
                """, user_id)
        except Exception as e:
            logger.error(f"Unban xatosi: {e}")

    async def get_all_users(self) -> list[dict]:
        """Barcha foydalanuvchilar ro'yxati."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT user_id, username, full_name, is_banned, created_at FROM users ORDER BY created_at"
                )
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Foydalanuvchilar ro'yxati xatosi: {e}")
            return []

    async def get_users_count(self) -> int:
        """Foydalanuvchilar soni."""
        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchval("SELECT COUNT(*) FROM users")
        except Exception as e:
            logger.error(f"Foydalanuvchilar soni xatosi: {e}")
            return 0

    async def get_active_user_ids(self) -> list[int]:
        """Ban qilinmagan foydalanuvchilar ID larini olish (global xabar uchun)."""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT user_id FROM users WHERE is_banned = FALSE"
                )
                return [r["user_id"] for r in rows]
        except Exception as e:
            logger.error(f"Aktiv foydalanuvchilar xatosi: {e}")
            return []

    # ===== Yuklashlar tarixi =====

    async def log_download(self, user_id: int, url: str, media_type: str,
                           quality: str = None, file_size: int = None):
        """Yuklab olish tarixini qayd etish."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO downloads (user_id, url, media_type, quality, file_size)
                    VALUES ($1, $2, $3, $4, $5)
                """, user_id, url, media_type, quality, file_size)
        except Exception as e:
            logger.error(f"Download log xatosi: {e}")

    # ===== Xatolik hisobotlari =====

    async def add_error_report(self, user_id: int, report_text: str):
        """Xatolik hisobotini saqlash."""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO error_reports (user_id, report_text)
                    VALUES ($1, $2)
                """, user_id, report_text)
        except Exception as e:
            logger.error(f"Xatolik hisoboti saqlash xatosi: {e}")


# Global instance
db = Database()
