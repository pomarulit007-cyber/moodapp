import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import json
import os
import threading
from dotenv import load_dotenv


with open('moods.json', 'r') as f:
    data = json.load(f)

real_user_id = "1019422671"  

if "unknown" in data:
    if real_user_id not in data:
        data[real_user_id] = {}
    data[real_user_id].update(data["unknown"])
    del data["unknown"]

# Сохраняем обратно
with open('moods.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ Готово!")

# Загружаем переменные из .env
load_dotenv()

# ===== НАСТРОЙКИ =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BOT_USERNAME = "MyLoveMood_bot"

if not TELEGRAM_TOKEN:
    raise ValueError("Токен не найден! Создай файл .env с TELEGRAM_TOKEN=твой_токен")

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

# ===== КОМАНДЫ ТЕЛЕГРАМ БОТА =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        {"text": "🌸 Открыть дневник настроения", "web_app": {"url": WEBAPP_URL}}
    ]]
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
        await update.message.reply_text(
            "📭 У тебя пока нет записей о настроении.\n"
            "Нажми /start и открой дневник, чтобы начать!"
        )
        return
    
    user_moods = moods_data[user_id]
    last_moods = list(user_moods.items())[-10:]
    
    message = "📊 *Твои последние настроения:*\n\n"
    for date, mood in last_moods:
        mood_emoji = {
            "happy": "😊", "normal": "😐", "sad": "😔", 
            "love": "🥰", "angry": "😠"
        }.get(mood, "❓")
        message += f"• {date}: {mood_emoji}\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")

# ===== ОБРАБОТЧИК ДАННЫХ ИЗ МИНИ-АППА =====
async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        
        # Обработка команды истории
        if data.get('action') == 'history':
            user_id = str(update.effective_user.id)
            if user_id in moods_data and moods_data[user_id]:
                user_moods = moods_data[user_id]
                last_moods = list(user_moods.items())[-10:]
                message = "📊 *Твои последние настроения:*\n\n"
                for date, mood in last_moods:
                    mood_emoji = {
                        "happy": "😊", "normal": "😐", "sad": "😔",
                        "love": "🥰", "angry": "😠"
                    }.get(mood, "❓")
                    message += f"• {date}: {mood_emoji}\n"
                await update.message.reply_text(message, parse_mode="Markdown")
            else:
                await update.message.reply_text("📭 У тебя пока нет записей о настроении.")
            return
        
        # Обработка настроения
        mood = data.get('mood')
        mood_emoji = data.get('mood_emoji', '❓')
        timestamp = data.get('timestamp', datetime.now().isoformat())
        user_id = str(update.effective_user.id)
        
        date_str = datetime.fromisoformat(timestamp).strftime("%d.%m.%Y %H:%M")
        
        if user_id not in moods_data:
            moods_data[user_id] = {}
        moods_data[user_id][date_str] = mood
        save_moods(moods_data)
        
        print(f"✅ Сохранено: {user_id} -> {mood} в {date_str}")
        
        await update.message.reply_text(
            f"✅ Твоё настроение {mood_emoji} сохранено! ❤️"
        )
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text("❌ Не удалось сохранить настроение")

# ===== FLASK СЕРВЕР (для приёма данных через fetch) =====
flask_app = Flask(__name__)
CORS(flask_app)

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
        
        print(f"✅ Сохранено через Flask: {user_id} -> {mood} в {date_str}")
        
        return jsonify({"status": "ok", "message": "Настроение сохранено"}), 200
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@flask_app.route('/history', methods=['GET'])
def get_history():
    user_id = request.args.get('user_id', '')
    if user_id in moods_data:
        return jsonify(moods_data[user_id]), 200
    return jsonify({}), 200

@flask_app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "alive"}), 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# ===== ЗАПУСК =====
if __name__ == '__main__':
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Запускаем Telegram бота
    print("🤖 Запускаю бота...")
    print(f"📱 Твой бот: @{BOT_USERNAME}")
    print("🛑 Для остановки нажми Ctrl+C")
    
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("history", history))
    telegram_app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    
    print("✅ Бот и веб-сервер запущены!")
    print("🌐 Flask сервер на http://localhost:5000")
    telegram_app.run_polling()