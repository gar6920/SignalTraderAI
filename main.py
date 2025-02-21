import asyncio
import logging
from signalbot import SignalBot, Command, Context
from config import API_HOST, API_PORT, PHONE_NUMBER, DEVICE_NAME
from database import init_db, store_received_message, mark_received_message_processed, create_outgoing_message, get_pending_outgoing_messages, mark_outgoing_message_sent

logging.basicConfig(level=logging.INFO, format="{asctime} [{levelname}] {message}", style="{")
logger = logging.getLogger("SignalBot")

class MessageHandler(Command):
    async def handle(self, c: Context):
        message = c.message
        logger.info(f"Received message: {message.text}")
        message_id = await store_received_message(message)
        recipient = PHONE_NUMBER if message.source == PHONE_NUMBER else (message.group if hasattr(message, 'group') else message.source)
        logger.info(f"Set recipient to: {recipient}")
        if message.text == "Ping":
            await create_outgoing_message(message_id, recipient, "Pong")
            await mark_received_message_processed(message_id)
        elif message.text.startswith("!compute"):
            await create_outgoing_message(message_id, recipient, "Processing your request...")
        else:
            response = f"Echo: {message.text}"
            await create_outgoing_message(message_id, recipient, response)
            await mark_received_message_processed(message_id)

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
    loop.run_until_complete(init_db())
    service = f"{API_HOST}:{API_PORT}"
    bot = SignalBot({
        "signal_service": service,
        "phone_number": PHONE_NUMBER
    })
    bot.register(MessageHandler())
    asyncio.ensure_future(send_outgoing_messages(bot))
    bot.start()

if __name__ == "__main__":
    main()