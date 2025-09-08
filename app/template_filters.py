# app/template_filters.py

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def format_datetime(value):
    """
    Форматирует ISO-дату в читаемый формат: '2025-06-15T10:30:00Z' → '15.06.2025 10:30'
    """
    if not value:
        return ''
    try:
        if isinstance(value, str):
            # Поддержка UTC (Z) и других временных зон
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        else:
            dt = value  # если уже datetime
        return dt.strftime('%d.%m.%Y %H:%M')
    except Exception as e:
        logger.warning(f"Failed to format datetime '{value}': {e}")
        return str(value)

def format_duration(value):
    """
    Форматирует длительность из ISO 8601: 'PT2H30M' → '2ч 30м'
    """
    if not value:
        return ''
    try:
        # Убираем PT, заменяем H/M на ч/м
        result = value.replace('PT', '').replace('H', 'ч ').replace('M', 'м').replace('S', 'с')
        return result.strip()
    except Exception as e:
        logger.warning(f"Failed to format duration '{value}': {e}")
        return str(value)

def format_price(value, currency="₽"):
    """
    Форматирует цену: 1234.5 → '1 234,50 ₽'
    """
    try:
        if isinstance(value, str):
            value = float(value)
        # Форматируем с разделителями: 1234.56 → "1 234,56"
        formatted = f"{value:,.2f}".replace(",", " ").replace(".", ",")
        return f"{formatted} {currency}"
    except Exception as e:
        logger.warning(f"Failed to format price '{value}': {e}")
        return str(value)

def truncate_text(text, length=100):
    """
    Обрезает текст и добавляет многоточие
    """
    if not text or len(text) <= length:
        return text
    return text[:length] + "..."