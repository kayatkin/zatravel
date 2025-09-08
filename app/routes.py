from flask import Blueprint, render_template, request, jsonify
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('app', __name__)

# Импортируем после создания bp, чтобы избежать циклических импортов
from app.services.amadeus_client import AmadeusClient
from app.models import FlightOffer

amadeus_client = AmadeusClient()


def extract_iata_code(input_str):
    """
    Извлекает IATA-код из строки вида "Город (IATA)" или просто "IATA".
    Возвращает строку из 3 заглавных букв.
    """
    if not input_str:
        return ""
    s = str(input_str).strip()
    # Если есть скобки — извлекаем содержимое последних скобок
    if '(' in s and ')' in s:
        try:
            # Берём часть после последней открывающей скобки
            code = s.split('(')[-1].split(')')[0].strip().upper()
            if len(code) == 3 and code.isalpha():
                return code
        except:
            pass
    # Если скобок нет — берём первые 3 буквы
    code = ''.join(filter(str.isalpha, s))[:3].upper()
    return code if len(code) == 3 else ""


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/search', methods=['POST'])
def search_flights():
    try:
        search_data = request.get_json()
        if not search_data:
            return jsonify({'error': 'No JSON data provided'}), 400

        logger.info(f"Received search request: {search_data}")

        # Валидация обязательных полей
        origin_input = search_data.get('origin')
        destination_input = search_data.get('destination')
        departure_date = search_data.get('departureDate')

        if not all([origin_input, destination_input, departure_date]):
            logger.warning("Missing required fields in search request")
            return jsonify({'error': 'Missing required fields: origin, destination, departureDate'}), 400

        # Извлекаем IATA-коды
        origin = extract_iata_code(origin_input)
        destination = extract_iata_code(destination_input)

        if not origin or not destination:
            return jsonify({'error': 'Invalid airport codes'}), 400

        # Формируем параметры для Amadeus API
        search_params = {
            'originLocationCode': origin,
            'destinationLocationCode': destination,
            'departureDate': departure_date,
            'adults': int(search_data.get('adults', 1)),
            'max': int(search_data.get('maxResults', 5))
        }

        # Добавляем returnDate только если он не пустой и не состоит из пробелов
        return_date = search_data.get('returnDate')
        if return_date and str(return_date).strip():
            search_params['returnDate'] = str(return_date).strip()

        logger.info(f"Processed search params: {search_params}")

        # Выполняем поиск
        results = amadeus_client.search_flights(search_params)

        # Преобразуем в объекты FlightOffer
        flights = []
        for offer in results.get('data', []):
            try:
                flight = FlightOffer.from_amadeus_data(offer)
                flights.append(flight.to_dict())
            except Exception as e:
                logger.warning(f"Failed to parse flight offer: {e}")
                continue

        logger.info(f"Found {len(flights)} flights")

        return jsonify({
            'success': True,
            'flights': flights,
            'total': len(flights)
        })

    except Exception as e:
        error_msg = str(e)
        # Пытаемся получить детали ошибки от Amadeus (если это HTTP ошибка)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                logger.error(f"Amadeus API error details: {error_detail}")
                if isinstance(error_detail, dict) and 'errors' in error_detail and len(error_detail['errors']) > 0:
                    first_error = error_detail['errors'][0]
                    title = first_error.get('title', 'Error')
                    detail = first_error.get('detail', 'Unknown error')
                    error_msg = f"{title}: {detail}"
            except Exception as parse_error:
                logger.error(f"Failed to parse error response: {parse_error}")
        logger.error(f"Search error: {error_msg}", exc_info=True)
        return jsonify({'error': error_msg}), 500


@bp.route('/api/airports')
def get_airports():
    try:
        keyword = request.args.get('q', '').strip()
        logger.info(f"Airport search for: {keyword}")

        if len(keyword) < 2:
            return jsonify([])

        results = amadeus_client.get_airport_suggestions(keyword)
        airports = []

        for item in results.get('data', []):
            airports.append({
                'code': item.get('iataCode', ''),
                'name': item.get('name', ''),
                'city': item.get('address', {}).get('cityName', ''),
                'country': item.get('address', {}).get('countryName', '')
            })

        logger.info(f"Found {len(airports)} airports")
        return jsonify(airports)

    except Exception as e:
        logger.error(f"Airport search error: {e}", exc_info=True)
        return jsonify([])


@bp.route('/test-search')
def test_search():
    """Тестовый маршрут для проверки поиска"""
    try:
        # Тестовый поиск (используем SVO вместо MOW — надёжнее в тестовом API)
        search_params = {
            'originLocationCode': 'SVO',
            'destinationLocationCode': 'LED',
            'departureDate': '2025-06-15',  # дата ближе к текущей — надёжнее
            'adults': 1,
            'max': 2
        }

        logger.info(f"Running test search with params: {search_params}")
        results = amadeus_client.search_flights(search_params)

        return jsonify({
            'success': True,
            'data': results
        })

    except Exception as e:
        logger.error(f"Test search error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        })