import asyncpg
import logging
import asyncio
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

logging.basicConfig(level=logging.INFO, format="{asctime} [{levelname}] {message}", style="{")
logger = logging.getLogger("Database")

async def init_db():
    max_attempts = 10
    delay = 2  # Seconds between retries
    for attempt in range(max_attempts):
        try:
            conn = await asyncpg.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            logger.info(f"Connected to PostgreSQL at {DB_HOST}:{DB_PORT}")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages_received (
                    id SERIAL PRIMARY KEY,
                    timestamp TEXT,
                    source TEXT,
                    group_id TEXT,
                    content TEXT,
                    status TEXT DEFAULT 'new'
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS outgoing_messages (
                    id SERIAL PRIMARY KEY,
                    received_message_id INTEGER REFERENCES messages_received(id),
                    recipient TEXT,
                    content TEXT,
                    status TEXT DEFAULT 'pending',
                    sent_at TIMESTAMP
                )
            """)
            await conn.close()
            logger.info("Database initialized successfully")
            return  # Exit on success
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed to connect to PostgreSQL: {e}")
            if attempt < max_attempts - 1:
                await asyncio.sleep(delay)
            else:
                logger.error(f"Failed to initialize database after {max_attempts} attempts")
                raise

async def store_received_message(message):
    conn = await asyncpg.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    group_id = message.group if hasattr(message, 'group') else None
    message_id = await conn.fetchval("""
        INSERT INTO messages_received (timestamp, source, group_id, content, status)
        VALUES ($1, $2, $3, $4, 'new')
        RETURNING id
    """, message.timestamp, message.source, group_id, message.text)
    await conn.close()
    logger.info(f"Stored received message {message_id}")
    return message_id

async def mark_received_message_processed(message_id):
    conn = await asyncpg.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    await conn.execute("""
        UPDATE messages_received
        SET status = 'processed'
        WHERE id = $1
    """, message_id)
    await conn.close()
    logger.info(f"Marked message {message_id} as processed")

async def get_new_received_message():
    conn = await asyncpg.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    message = await conn.fetchrow("""
        SELECT id, source, group_id, content
        FROM messages_received
        WHERE status = 'new'
        LIMIT 1
    """)
    if message:
        await conn.execute("""
            UPDATE messages_received
            SET status = 'processing'
            WHERE id = $1
        """, message['id'])
        logger.info(f"Fetched new message {message['id']}")
    await conn.close()
    return message

async def create_outgoing_message(received_message_id, recipient, content):
    conn = await asyncpg.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    await conn.execute("""
        INSERT INTO outgoing_messages (received_message_id, recipient, content, status)
        VALUES ($1, $2, $3, 'pending')
    """, received_message_id, recipient, content)
    await conn.close()
    logger.info(f"Created outgoing message for received_message_id {received_message_id} to {recipient}")

async def get_pending_outgoing_messages():
    conn = await asyncpg.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    messages = await conn.fetch("""
        SELECT id, recipient, content
        FROM outgoing_messages
        WHERE status = 'pending'
    """)
    await conn.close()
    logger.info(f"Fetched {len(messages)} pending outgoing messages")
    return messages

async def mark_outgoing_message_sent(message_id):
    conn = await asyncpg.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )
    await conn.execute("""
        UPDATE outgoing_messages
        SET status = 'sent',
            sent_at = CURRENT_TIMESTAMP
        WHERE id = $1
    """, message_id)
    await conn.close()
    logger.info(f"Marked outgoing message {message_id} as sent")