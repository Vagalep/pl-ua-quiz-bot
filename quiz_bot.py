import os
import logging
import random
import json
import datetime
from telegram import Update, Poll
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import pytz
from telegram.error import Forbidden

CONFIG_FILE = "config.json"
WORDS_FILE = "words.json"
SCHEDULE_FILE = "schedule.json"

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

def load_json_file(filename: str) -> dict:
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error(f"File {filename} not found.")
        return {}

def save_json_file(data: dict, filename: str) -> None:
    try:
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Error saving in {filename}: {e}")

# Loading the configuration
TOKEN = os.getenv("TOKEN")

channel_names_env = os.getenv("CHANNEL_NAMES", "")
if channel_names_env:
    channel_names = [channel.strip() for channel in channel_names_env.split(",")]
    config = load_json_file(CONFIG_FILE)
    existing_channels = set(config.get("channel_names", []))
    new_channels = set(channel_names) - existing_channels

    if new_channels:
        config["channel_names"] = list(existing_channels | new_channels)
        save_json_file(config, CONFIG_FILE)
        logger.info(f"New channels added from environment variable: {', '.join(new_channels)} to config.json")
    else:
        logger.info("No new channels to add from environment variable.")
else:
    logger.info(f"Environment variable CHANNEL_NAMES is absent. The list of channels is taken from config.json")
    config = load_json_file(CONFIG_FILE)
    channel_names = config.get("channel_names", [])

CHANNEL_NAMES = config.get("channel_names", [])

words = load_json_file(WORDS_FILE)
schedule = load_json_file(SCHEDULE_FILE)
history_limit = len(schedule)
used_words_history = []
poland_timezone = pytz.timezone("Europe/Warsaw")

def format_schedule_text(schedule) -> str:
    return "\n".join(f" - {entry['hour']:02d}:{entry['minute']:02d} (Europe/Warsaw UTC+1)" for entry in schedule)

async def is_bot_member(context: ContextTypes.DEFAULT_TYPE, channel_username):
    try:
        chat_member = await context.bot.get_chat_member(channel_username, context.bot.id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

async def send_message(context, chat_id, text):
    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
        logger.info(f"Message sent to {chat_id}")
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")

def get_random_word(words, used_words_history, history_limit):
    available_words = [word for word in words if word not in used_words_history]

    if not available_words:
        logger.warning("All the words have been used. Starts from the beginning.")
        used_words_history.clear()
        available_words = words.copy()

    selected_word = random.choice(available_words)

    # Refresh history
    used_words_history.append(selected_word)
    if len(used_words_history) > history_limit:
        used_words_history.pop(0)

    return selected_word

async def start_poll(context: ContextTypes.DEFAULT_TYPE):
    if not words:
        logger.error("The word list is empty or not loaded.")
        return

    logger.info("Starting a poll")
    word_data = get_random_word(words, used_words_history, history_limit)
    correct_answer = word_data["options"][word_data["correct_option_id"]]

    for channel_username in CHANNEL_NAMES:
        if not await is_bot_member(context, channel_username):
            logger.info(f"Bot is not a member of {channel_username}, skipping poll.")
            continue

        try:
            await context.bot.send_poll(
                chat_id=channel_username,
                question=f"Як перекладається слово {word_data['word']}",
                options=word_data["options"],
                is_anonymous=True,
                type=Poll.QUIZ,
                correct_option_id=word_data["correct_option_id"],
                explanation=f"Правильна відповідь - {correct_answer}"
            )
            logger.info(f"Poll sent to {channel_username}")
        except Forbidden:
            logger.error(f"Failed to send poll to {channel_username}: Forbidden")
        except Exception as e:
            logger.error(f"An error occurred while sending poll: {e}")

async def schedule_polls(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Configuring the survey schedule")
    if not CHANNEL_NAMES:
        logger.info("Failed to send bot launch message because channel list is empty.")

    schedule_text = "Ось розклад опитувань:\n" + format_schedule_text(schedule)

    for channel_name in CHANNEL_NAMES:
        await send_message(context, channel_name, f'Бот запущено! Опитування будуть проводитись відповідно до розкладу.\n{schedule_text}')

    for time_entry in schedule:
        logger.info(f"Adding a task at {time_entry['hour']}:{time_entry['minute']} local time")
        context.application.job_queue.run_daily(start_poll, time=datetime.time(
            hour=time_entry["hour"], minute=time_entry["minute"], tzinfo=poland_timezone))

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        if update.message:
            await update.message.reply_text("Будь ласка, введіть назву каналу після команди /add.")
        return

    channel_name = context.args[0]
    if not channel_name.startswith('@'):
        if update.message:
            await update.message.reply_text("Будь ласка, введіть назву каналу з символом @ на початку.")
        return

    try:
        chat_member = await context.bot.get_chat_member(channel_name, update.effective_user.id)
        if chat_member.status in ['member', 'administrator', 'creator']:
            if channel_name not in CHANNEL_NAMES:
                CHANNEL_NAMES.append(channel_name)
                config["channel_names"] = CHANNEL_NAMES
                save_json_file(config, CONFIG_FILE)
                schedule_text = "Ось розклад опитувань:\n" + format_schedule_text(schedule)
                await send_message(context, channel_name, f'Бот підключено до каналу {channel_name}! Опитування будуть проводитись відповідно до розкладу.\n{schedule_text}')
                if update.message:
                    await update.message.reply_text(f"Канал {channel_name} додано до списку.")
                    logger.info(f"Channel {channel_name} added to the list")
            else:
                 if update.message:
                    await update.message.reply_text(f"Канал {channel_name} вже є в списку.")
        else:
            if update.message:
                await update.message.reply_text(f"Бот не є учасником каналу {channel_name}.")
    except Exception as e:
        if update.message:
            await update.message.reply_text(f"Не вдалося перевірити канал {channel_name}. Переконайтеся, що він існує і бот є його учасником.")
        logger.error(f"Error checking channel {channel_name}: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ви можете додати свій канал для проведення опитувань, використовуючи команду /add @channel_name. "
        "Після цього опитування будуть автоматично проводитись на вашому каналі згідно з розкладом."
    )

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.job_queue.run_once(schedule_polls, when=0)

    application.add_handler(CommandHandler("add", add_channel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling()

if __name__ == '__main__':
    main()