import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters, ContextTypes
import json
import os
from dotenv import load_dotenv

load_dotenv()

# ===== НАСТРОЙКИ =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BOT_USERNAME = "MyLoveMood_bot"

if not TELEGRAM_TOKEN:
    raise ValueError("Токен не найден!")

WEBAPP_URL = "https://pomarulit007-cyber.github.io/moodapp/webapp/"
MOODS_FILE = "moods.json"

# ===== НАСТРОЙКА ЛОГИРОВАНИЯ =====
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ =====
def load_moods():
    if os.path.exists(MOODS_FILE):
        with open(MOODS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_moods(moods):
    with open(MOODS_FILE, 'w', encoding='utf-8') as f:
        json.dump(moods, f, ensure_ascii=False, indent=2)

moods_data = load_moods()

# ===== ИНИЦИАЛИЗАЦИЯ БОТА И ДИСПЕТЧЕРА =====
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

# ===== КОМАНДЫ ТЕЛЕГРАМ БОТА =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[{"text": "🌸 Открыть дневник настроения", "web_app": {"url": WEBAPP_URL}}]]
    reply_markup = {"inline_keyboard": keyboard}
    await update.message.reply_text(
        "Привет, любимая! 🌷\n\n"
        "Я буду запоминать твоё настроение каждый день.\n"
        "Нажми на кнопку ниже, чтобы открыть дневник и выбрать смайлик:",
        reply_markup=reply_markup
    )

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in moods_data or not moods_data[user_id]:
        await update.message.reply_text("📭 У тебя пока нет записей о настроении.\nНажми /start и открой дневник, чтобы начать!")
        return
    user_moods = moods_data[user_id]
    last_moods = list(user_moods.items())[-10:]
    message = "📊 *Твои последние настроения:*\n\n"
    for date, mood in last_moods:
        mood_emoji = {"happy": "😊", "normal": "😐", "sad": "😔", "love": "🥰", "angry": "😠"}.get(mood, "❓")
        message += f"• {date}: {mood_emoji}\n"
    await update.message.reply_text(message, parse_mode="Markdown")

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    ADMIN_ID = "1019422671"
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ У тебя нет прав для этой команды.")
        return
    global moods_data
    moods_data = {}
    save_moods(moods_data)
    await update.message.reply_text("✅ Вся история настроений очищена!")

async def delete_mood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("❌ Укажи дату в формате: /delete 16.04.2026 13:48\n\nПример: /delete 16.04.2026 13:48")
        return
    date_str = " ".join(context.args)
    if user_id not in moods_data or date_str not in moods_data[user_id]:
        await update.message.reply_text(f"❌ Запись на {date_str} не найдена.\n\nПосмотри /history для списка дат")
        return
    del moods_data[user_id][date_str]
    if not moods_data[user_id]:
        del moods_data[user_id]
    save_moods(moods_data)
    await update.message.reply_text(f"✅ Запись на {date_str} удалена!")

async def stats_mood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in moods_data or not moods_data[user_id]:
        await update.message.reply_text("📭 У тебя пока нет записей о настроении.")
        return
    stats = {"happy": 0, "normal": 0, "sad": 0, "love": 0, "angry": 0}
    for mood in moods_data[user_id].values():
        if mood in stats:
            stats[mood] += 1
    emojis = {"happy": "😊", "normal": "😐", "sad": "😔", "love": "🥰", "angry": "😠"}
    message = "📊 *Твоя статистика настроений:*\n\n"
    for mood, count in stats.items():
        if count > 0:
            percentage = (count / len(moods_data[user_id])) * 100
            message += f"{emojis[mood]} {mood}: {count} раз ({percentage:.0f}%)\n"
    message += f"\n📝 Всего записей: {len(moods_data[user_id])}"
    await update.message.reply_text(message, parse_mode="Markdown")

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        if data.get('action') == 'clear':
            user_id = str(update.effective_user.id)
            ADMIN_ID = "1019422671"
            if user_id != ADMIN_ID:
                await update.message.reply_text("❌ У тебя нет прав для очистки.")
                return
            global moods_data
            moods_data = {}
            save_moods(moods_data)
            await update.message.reply_text("✅ Вся история настроений очищена!")
            return
    except Exception as e:
        logging.error(f"Ошибка в handle_web_app_data: {e}")

# Регистрируем обработчики команд
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("history", history))
dispatcher.add_handler(CommandHandler("clear", clear_history))
dispatcher.add_handler(CommandHandler("delete", delete_mood))
dispatcher.add_handler(CommandHandler("stats", stats_mood))
dispatcher.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

# ===== FLASK СЕРВЕР =====
flask_app = Flask(__name__)
CORS(flask_app)

# Эндпоинт для вебхука Telegram
@flask_app.route(f'/webhook/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook():
    if request.method == 'POST':
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        return 'ok', 200

# Эндпоинты для мини-приложения
@flask_app.route('/clear', methods=['POST'])
def clear_history_flask():
    try:
        data = request.json
        user_id = str(data.get('user_id'))
        ADMIN_ID = "1019422671"
        if user_id != ADMIN_ID:
            return jsonify({"status": "error", "message": "Нет прав"}), 403
        global moods_data
        moods_data = {}
        save_moods(moods_data)
        return jsonify({"status": "ok", "message": "История очищена"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@flask_app.route('/mood', methods=['POST', 'OPTIONS'])
def receive_mood():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.json
        user_id = str(data.get('user_id'))
        mood = data.get('mood')
        timestamp = data.get('timestamp', datetime.now().isoformat())
        date_str = datetime.fromisoformat(timestamp).strftime("%d.%m.%Y %H:%M")
        if user_id not in moods_data:
            moods_data[user_id] = {}
        moods_data[user_id][date_str] = mood
        save_moods(moods_data)
        return jsonify({"status": "ok", "message": "Настроение сохранено"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@flask_app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "alive"}), 200

@flask_app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "ok", "message": "Бот для дневника настроения работает"}), 200

# Устанавливаем вебхук при запуске
def set_webhook():
    webhook_url = f"https://moodapp-tszs.onrender.com/webhook/{TELEGRAM_TOKEN}"
    bot.set_webhook(url=webhook_url)
    print(f"✅ Webhook установлен на {webhook_url}")

# ===== ЗАПУСК =====
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    set_webhook()  
    flask_app.run(host='0.0.0.0', port=port)