import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    AMADEUS_API_KEY = os.getenv('AMADEUS_API_KEY')
    AMADEUS_API_SECRET = os.getenv('AMADEUS_API_SECRET')
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    CACHE_TYPE = 'SimpleCache'  # Актуально для Flask-Caching 2.x
    CACHE_DEFAULT_TIMEOUT = 300  # 5 минут

    # Валидация обязательных переменных
    if not AMADEUS_API_KEY:
        raise ValueError("❌ Отсутствует обязательная переменная: AMADEUS_API_KEY")
    if not AMADEUS_API_SECRET:
        raise ValueError("❌ Отсутствует обязательная переменная: AMADEUS_API_SECRET")

    # Режимы (опционально)
    DEBUG = os.getenv('FLASK_DEBUG', '0').lower() in ['true', '1', 'yes']
    TESTING = os.getenv('FLASK_TESTING', '0').lower() in ['true', '1', 'yes']

    # На будущее — Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')