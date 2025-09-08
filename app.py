import os
import sys
import logging
from flask import Flask
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем абсолютный путь к корневой папке
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Добавляем путь к модулям в sys.path (для импортов)
sys.path.append(BASE_DIR)

# Загружаем переменные окружения из .env
load_dotenv()

# Импортируем конфигурацию
from config import Config

# Создаём приложение Flask с правильными путями к шаблонам и статике
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'app', 'templates'),
            static_folder=os.path.join(BASE_DIR, 'app', 'static'))

# Загружаем конфигурацию из класса Config
app.config.from_object(Config)

# === Подключение кэширования ===
try:
    from app.services.cache_service import cache, init_cache
    init_cache(app)
    logger.info("✓ Cache initialized successfully")
except ImportError as e:
    logger.error(f"Error initializing cache: {e}")
    # Приложение продолжит работу без кэша
    pass

# === Регистрация кастомных фильтров шаблонов ===
# Вынесено в отдельный модуль для соблюдения best practices
try:
    from app.template_filters import format_datetime, format_duration, format_price, truncate_text
    
    app.jinja_env.filters['format_datetime'] = format_datetime
    app.jinja_env.filters['format_duration'] = format_duration
    app.jinja_env.filters['format_price'] = format_price
    app.jinja_env.filters['truncate'] = truncate_text
    
    logger.info("✓ Template filters registered successfully")
except ImportError as e:
    logger.error(f"Error importing template filters: {e}")
    # Приложение может работать и без фильтров (шаблоны будут использовать сырые значения)

# === Регистрация blueprint'ов ===
try:
    from app.routes import bp
    app.register_blueprint(bp)
    logger.info("✓ Routes loaded successfully")
except ImportError as e:
    logger.error(f"Error importing routes: {e}", exc_info=True)
    # Fallback: создаём минимальные роуты, чтобы приложение не падало
    @app.route('/')
    def index():
        return f"""
        <h1>🚧 ZaTravel — Routes Not Loaded</h1>
        <p><strong>Ошибка:</strong> {str(e)}</p>
        <p>Проверьте логи и структуру проекта.</p>
        <pre>{str(e)}</pre>
        """, 500

# === Служебные роуты ===
@app.route('/health')
def health_check():
    """Эндпоинт для health-check (например, для Docker или мониторинга)"""
    return {'status': 'ok', 'message': 'ZaTravel is running'}

@app.route('/debug')
def debug_info():
    """Страница отладки — проверка конфигурации"""
    return {
        'amadeus_key_exists': bool(app.config.get('AMADEUS_API_KEY')),
        'amadeus_secret_exists': bool(app.config.get('AMADEUS_API_SECRET')),
        'template_folder': app.template_folder,
        'static_folder': app.static_folder,
        'debug_mode': app.debug,
        'cache_configured': hasattr(app, 'extensions') and 'cache' in app.extensions,
        'filters_registered': len(app.jinja_env.filters) > 0
    }

# === Запуск приложения ===
if __name__ == '__main__':
    logger.info("🚀 Starting ZaTravel application...")
    logger.info(f"📁 Template folder: {app.template_folder}")
    logger.info(f"📁 Static folder: {app.static_folder}")
    logger.info(f"🔑 Amadeus API Key: {'SET' if app.config.get('AMADEUS_API_KEY') else 'MISSING'}")
    logger.info(f"🔒 Debug mode: {app.debug}")

    # Получаем порт из переменной окружения или используем 5001 по умолчанию
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"🌐 Running on http://localhost:{port}")

    # Запускаем сервер
    app.run(debug=app.debug, host='0.0.0.0', port=port)