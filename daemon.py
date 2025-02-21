import asyncio
import logging
from database import init_db, get_new_received_message, mark_received_message_processed, create_outgoing_message

logging.basicConfig(level=logging.INFO, format="{asctime} [{levelname}] {message}", style="{")
logger = logging.getLogger("Daemon")

async def perform_computation(message):
    await asyncio.sleep(5)
    return f"Computed result for {message['content']}"

async def process_messages():
    await init_db()
    while True:
        message = await get_new_received_message()
        if message:
            message_id, source, group_id, content = message['id'], message['source'], message['group_id'], message['content']
            logger.info(f"Processing message {message_id}")
            recipient = group_id if group_id else source
            if content.startswith("!compute"):
                result = await perform_computation(message)
                await create_outgoing_message(message_id, recipient, result)
            await mark_received_message_processed(message_id)
            logger.info(f"Completed message {message_id}")
        else:
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(process_messages())