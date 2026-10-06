import asyncio
import json
import aiosqlite


class Store:
    """One connection, serialized transactions; JSON records plus normalized votes."""
    def __init__(self, path):
        self.path = path
        self.lock = asyncio.Lock()
        self.connection = None

    async def open(self):
        self.connection = await aiosqlite.connect(self.path)
        await self.connection.executescript('''
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=FULL;
            PRAGMA busy_timeout=5000;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS records (
                kind TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL,
                PRIMARY KEY(kind,id));
            CREATE TABLE IF NOT EXISTS votes (
                proposal TEXT NOT NULL, user TEXT NOT NULL,
                choice INTEGER NOT NULL CHECK(choice IN (-1,1)),
                PRIMARY KEY(proposal,user));
        ''')
        await self.connection.commit()

    async def get(self, kind, key):
        async with self.lock:
            async with self.connection.execute('SELECT data FROM records WHERE kind=? AND id=?', (kind, str(key))) as cur:
                row = await cur.fetchone()
                return json.loads(row[0]) if row else None

    async def all(self, kind, *, statuses=None):
        query = 'SELECT id,data FROM records WHERE kind=?'
        params = [kind]
        if statuses is not None:
            if not statuses:
                return []
            query += " AND json_extract(data, '$.status') IN (" + ','.join('?' for _ in statuses) + ')'
            params.extend(statuses)
        async with self.lock:
            async with self.connection.execute(query, params) as cur:
                return [(key, json.loads(data)) for key, data in await cur.fetchall()]

    async def put(self, kind, key, data):
        async with self.lock:
            await self.connection.execute('INSERT INTO records VALUES (?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data',
                                          (kind, str(key), json.dumps(data, ensure_ascii=False)))
            await self.connection.commit()

    async def vote(self, proposal, user, choice):
        if choice not in (-1, 1):
            raise ValueError('Nieprawidłowy głos')
        async with self.lock:
            try:
                await self.connection.execute('BEGIN IMMEDIATE')
                async with self.connection.execute('SELECT choice FROM votes WHERE proposal=? AND user=?', (str(proposal), str(user))) as cur:
                    row = await cur.fetchone()
                if row and row[0] == choice:
                    await self.connection.execute('DELETE FROM votes WHERE proposal=? AND user=?', (str(proposal), str(user)))
                else:
                    await self.connection.execute('INSERT INTO votes VALUES (?,?,?) ON CONFLICT(proposal,user) DO UPDATE SET choice=excluded.choice', (str(proposal), str(user), choice))
                await self.connection.commit()
            except BaseException:
                await self.connection.rollback()
                raise

    async def counts(self, proposal):
        async with self.lock:
            async with self.connection.execute('SELECT choice, COUNT(*) FROM votes WHERE proposal=? GROUP BY choice', (str(proposal),)) as cur:
                return dict(await cur.fetchall())

    async def close(self):
        if self.connection:
            await self.connection.close()
            self.connection = None

