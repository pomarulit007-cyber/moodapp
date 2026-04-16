# 1. Импорты
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

# 2. Загрузка переменных
load_dotenv()

# 3. Настройки
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BOT_USERNAME = "MyLoveMood_bot"

if not TELEGRAM_TOKEN:
    raise ValueError("Токен не найден!")

WEBAPP_URL = "https://pomarulit007-cyber.github.io/moodapp/webapp/"
MOODS_FILE = "moods.json"

# 4. Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 5. Функции для работы с данными
def load_moods():
    if os.path.exists(MOODS_FILE):
        with open(MOODS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_moods(moods):
    with open(MOODS_FILE, 'w', encoding='utf-8') as f:
        json.dump(moods, f, ensure_ascii=False, indent=2)

moods_data = load_moods()

# 6. Миграция данных
REAL_USER_ID = "1019422671"
if "unknown" in moods_data and REAL_USER_ID:
    if REAL_USER_ID not in moods_data:
        moods_data[REAL_USER_ID] = {}
    moods_data[REAL_USER_ID].update(moods_data["unknown"])
    del moods_data["unknown"]
    save_moods(moods_data)
    print("✅ Данные из 'unknown' перенесены в твой ID!")

# 7. ВСЕ КОМАНДЫ БОТА (ОПРЕДЕЛЯЮТСЯ ЗДЕСЬ, ДО ЗАПУСКА!)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0] == 'history':
        await history(update, context)
        return
    
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
        await update.message.reply_text("❌ Укажи дату в формате: /delete 16.04.2026 13:48")
        return
    
    date_str = " ".join(context.args)
    
    if user_id not in moods_data or date_str not in moods_data[user_id]:
        await update.message.reply_text(f"❌ Запись на {date_str} не найдена.")
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
        
        if data.get('action') == 'history':
            user_id = str(update.effective_user.id)
            if user_id in moods_data and moods_data[user_id]:
                user_moods = moods_data[user_id]
                last_moods = list(user_moods.items())[-10:]
                message = "📊 *Твои последние настроения:*\n\n"
                for date, mood in last_moods:
                    mood_emoji = {"happy": "😊", "normal": "😐", "sad": "😔", "love": "🥰", "angry": "😠"}.get(mood, "❓")
                    message += f"• {date}: {mood_emoji}\n"
                await update.message.reply_text(message, parse_mode="Markdown")
            else:
                await update.message.reply_text("📭 У тебя пока нет записей о настроении.")
            return
        
        mood = data.get('mood')
        mood_emoji = data.get('mood_emoji', '❓')
        timestamp = data.get('timestamp', datetime.now().isoformat())
        user_id = str(update.effective_user.id)
        
        date_str = datetime.fromisoformat(timestamp).strftime("%d.%m.%Y %H:%M")
        
        if user_id not in moods_data:
            moods_data[user_id] = {}
        moods_data[user_id][date_str] = mood
        save_moods(moods_data)
        
        print(f"✅ Сохранено через sendData: {user_id} -> {mood} в {date_str}")
        await update.message.reply_text(f"✅ Твоё настроение {mood_emoji} сохранено! ❤️")
        
    except Exception as e:
        logging.error(f"Ошибка в handle_web_app_data: {e}")
        await update.message.reply_text("❌ Не удалось сохранить настроение")

# 8. Flask сервер (определяется после всех функций)
flask_app = Flask(__name__)
CORS(flask_app)

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
        
        print(f"✅ История очищена пользователем {user_id}")
        return jsonify({"status": "ok", "message": "История очищена"}), 200
    except Exception as e:
        logging.error(f"Ошибка очистки: {e}")
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
        
        print(f"✅ Сохранено через Flask: {user_id} -> {mood} в {date_str}")
        return jsonify({"status": "ok", "message": "Настроение сохранено"}), 200
    except Exception as e:
        logging.error(f"Ошибка в Flask: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@flask_app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "alive"}), 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# 9. ЗАПУСК (в самом конце!)
if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    print("🤖 Запускаю бота...")
    print(f"📱 Твой бот: @{BOT_USERNAME}")
    print("🛑 Для остановки нажми Ctrl+C")
    
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("history", history))
    telegram_app.add_handler(CommandHandler("clear", clear_history))
    telegram_app.add_handler(CommandHandler("delete", delete_mood))
    telegram_app.add_handler(CommandHandler("stats", stats_mood))
    telegram_app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    
    print("✅ Бот и веб-сервер запущены!")
    print("🌐 Flask сервер на http://localhost:5000")
    telegram_app.run_polling()