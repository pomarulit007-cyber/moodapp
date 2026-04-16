import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from dotenv import load_dotenv

load_dotenv()

# ===== НАСТРОЙКИ =====
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

# ===== FLASK СЕРВЕР =====
flask_app = Flask(__name__)
CORS(flask_app)

@flask_app.route('/clear', methods=['POST', 'OPTIONS'])
def clear_history_flask():
    if request.method == 'OPTIONS':
        return '', 200
    
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
        
        print(f"✅ Сохранено: {user_id} -> {mood} в {date_str}")
        
        return jsonify({"status": "ok", "message": "Настроение сохранено"}), 200
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@flask_app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "alive"}), 200

@flask_app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "ok", "message": "Бот для дневника настроения работает"}), 200

# ===== ЗАПУСК =====
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host='0.0.0.0', port=port)