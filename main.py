import asyncio
import logging
import aiohttp
import sys
from signalbot import SignalBot, Command, Context
from config import API_HOST, API_PORT, PHONE_NUMBER, DEVICE_NAME
from database import init_db, store_received_message, mark_received_message_processed, create_outgoing_message, get_pending_outgoing_messages, mark_outgoing_message_sent

logging.basicConfig(level=logging.INFO, format="{asctime} [{levelname}] {message}", style="{")
logger = logging.getLogger("SignalBot")

async def check_linking():
    url = f"http://{API_HOST}:{API_PORT}/v1/about"
    for attempt in range(5):  # Retry 5 times
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    logger.info(f"Signal API response status: {resp.status}")
                    if resp.status == 200:
                        logger.info("Bot is linked and Signal API is reachable.")
                        return True
                    else:
                        logger.warning(f"Signal API returned status {resp.status}, attempt {attempt + 1}/5")
        except Exception as e:
            logger.error(f"Error checking Signal API, attempt {attempt + 1}/5: {e}")
            if attempt < 4:  # Don't sleep on the last attempt
                await asyncio.sleep(2)  # Wait 2 seconds before retrying
    logger.error("Failed to verify linking after 5 attempts.")
    return False

class MessageHandler(Command):
    async def handle(self, c: Context):
        message = c.message
        logger.info(f"Received message: {message.text} from {message.source}")
        is_sync = message.source == PHONE_NUMBER
        logger.info(f"Is sync message: {is_sync}")
        recipient = PHONE_NUMBER if is_sync else (message.group if hasattr(message, 'group') else message.source)
        logger.info(f"Set recipient to: {recipient}")
        try:
            message_id = await store_received_message(message)
            if message.text == "Ping":
                await create_outgoing_message(message_id, recipient, "Pong")
                await mark_received_message_processed(message_id)
                logger.info(f"Created outgoing message 'Pong' for message {message_id}")
            elif message.text.startswith("!compute"):
                await create_outgoing_message(message_id, recipient, "Processing your request...")
                logger.info(f"Created outgoing message 'Processing your request...' for message {message_id}")
            else:
                response = f"Echo: {message.text}"
                await create_outgoing_message(message_id, recipient, response)
                await mark_received_message_processed(message_id)
                logger.info(f"Created outgoing message '{response}' for message {message_id}")
        except Exception as e:
            logger.error(f"Error in MessageHandler: {e}")
            raise

async def send_outgoing_messages(bot):
    while True:
        messages = await get_pending_outgoing_messages()
        for msg in messages:
            msg_id, recipient, content = msg
            logger.info(f"Attempting to send message {msg_id} to {recipient}: {content}")
            try:
                await bot.send(recipient, content)
                await mark_outgoing_message_sent(msg_id)
                logger.info(f"Sent message {msg_id} to {recipient}")
            except Exception as e:
                logger.error(f"Failed to send message {msg_id} to {recipient}: {e}")
        await asyncio.sleep(10)

def main():
    loop = asyncio.get_event_loop()
    # Check linking with retries
    if not loop.run_until_complete(check_linking()):
        logger.error("Bot is not linked or Signal API is unreachable after retries. Please ensure signal-cli-rest-api is running and linked.")
        sys.exit(1)
    logger.info("Initializing database")
    loop.run_until_complete(init_db())
    logger.info("Database initialized, setting up SignalBot")
    service = f"{API_HOST}:{API_PORT}"
    bot = SignalBot({
        "signal_service": service,
        "phone_number": PHONE_NUMBER
    })
    logger.info("SignalBot initialized, registering handler")
    bot.register(MessageHandler())
    logger.info("Starting send_outgoing_messages task")
    asyncio.ensure_future(send_outgoing_messages(bot))
    logger.info("Starting bot")
    bot.start()

if __name__ == "__main__":
    main()