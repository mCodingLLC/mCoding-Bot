import asyncio
from sqlite3.dbapi2 import Row
from typing import Iterable, Optional

import aiosqlite

from . import tables


class TooManyRows(Exception):
    def __init__(self, num: int):
        self.num = num
        super().__init__(f"Expected 0 or 1 rows, got {num} rows instead.")


class Database:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.con: Optional[aiosqlite.Connection] = None

    async def init(self, path: str = "db.sqlite3"):
        self.con = await aiosqlite.connect(path)
        self.con.row_factory = aiosqlite.Row

        for table in tables.ALL_TABLES:
            await self.execute(table)

    async def close(self):
        async with self.lock:
            await self.con.close()

    async def _execute(
        self, fetch: bool, *args, **kwargs
    ) -> Optional[Iterable[Row]]:
        async with self.lock:
            cur = await self.con.execute(*args, **kwargs)
            if fetch:
                rows = await cur.fetchall()
            else:
                rows = None
            await self.con.commit()
        return rows

    async def execute(self, *args, **kwargs):
        await self._execute(False, *args, **kwargs)

    async def fetch(self, *args, **kwargs) -> Iterable[Row]:
        return await self._execute(True, *args, **kwargs)

    async def fetchone(self, *args, **kwargs) -> Optional[Row]:
        rows = await self.fetch(*args, **kwargs)
        num = len(rows)

        if num > 1:
            raise TooManyRows(num)

        if num:
            return rows[0]
