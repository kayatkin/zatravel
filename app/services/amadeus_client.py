import requests
from flask import current_app
import time
import logging

logger = logging.getLogger(__name__)


class AmadeusClient:
    def __init__(self):
        # ❗ ВАЖНО: УБРАЛ ЛИШНИЙ ПРОБЕЛ В КОНЦЕ URL
        self.base_url = "https://test.api.amadeus.com"
        self.token_url = f"{self.base_url}/v1/security/oauth2/token"
        self._token_cache = None
        self._token_expiry = 0
        self.last_request_time = 0
        self.request_delay = 1.0  # начальная задержка
        self.max_delay = 5.0      # максимальная задержка

    def _get_access_token(self):
        """Получение access token с кэшированием"""
        if self._token_cache and time.time() < self._token_expiry:
            return self._token_cache

        try:
            logger.info("Requesting new access token from Amadeus...")
            response = requests.post(
                self.token_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': current_app.config['AMADEUS_API_KEY'],
                    'client_secret': current_app.config['AMADEUS_API_SECRET']
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )

            logger.info(f"Token response status: {response.status_code}")

            if response.status_code != 200:
                error_detail = response.json() if response.content else response.text
                logger.error(f"Token request failed: {error_detail}")
                raise Exception(f"Token request failed: {response.status_code}")

            token_data = response.json()
            self._token_cache = token_data['access_token']
            # Обновляем за 60 секунд до истечения
            self._token_expiry = time.time() + token_data.get('expires_in', 1800) - 60

            logger.info("Successfully obtained access token")
            return self._token_cache

        except requests.exceptions.RequestException as e:
            logger.error(f"Amadeus token error: {e}")
            raise Exception("Failed to get access token")

    def _rate_limit(self):
        """Задержка между запросами чтобы избежать 429 ошибок"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _make_request_with_retry(self, method, url, headers=None, params=None, data=None, max_retries=3):
        """Выполняет HTTP-запрос с повторными попытками при 429/400 ошибках"""
        for attempt in range(max_retries + 1):
            try:
                self._rate_limit()
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    timeout=15
                )

                if response.status_code == 429:
                    # Увеличиваем задержку, но не больше max_delay
                    self.request_delay = min(self.request_delay * 1.5, self.max_delay)
                    logger.warning(f"Rate limit 429 on attempt {attempt + 1}. New delay: {self.request_delay:.2f}s")

                    if attempt < max_retries:
                        time.sleep(self.request_delay)
                        continue
                    else:
                        raise Exception("Rate limit exceeded after retries")

                elif response.status_code == 400:
                    # Пробуем повторить 400 ошибку — иногда это временные сбои
                    logger.warning(f"Bad Request 400 on attempt {attempt + 1}: {response.text[:200]}")
                    if attempt < max_retries:
                        time.sleep(2)  # ждём 2 секунды
                        continue

                # Для любых других ошибок — пробуем повторить только если 5xx
                if 500 <= response.status_code < 600 and attempt < max_retries:
                    logger.warning(f"Server error {response.status_code} on attempt {attempt + 1}")
                    time.sleep(3)
                    continue

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                if attempt == max_retries:
                    raise
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}. Retrying...")
                time.sleep(2 ** attempt)  # экспоненциальная задержка

        raise Exception("Max retries exceeded")

    def search_flights(self, search_params):
        """Поиск авиабилетов с retry-логикой"""
        token = self._get_access_token()

        # Очищаем параметры — убираем None и пустые строки
        clean_params = {k: v for k, v in search_params.items() if v not in (None, '', 'null')}

        try:
            logger.info(f"Searching flights with params: {clean_params}")

            response = self._make_request_with_retry(
                method='GET',
                url=f"{self.base_url}/v2/shopping/flight-offers",
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                },
                params=clean_params
            )

            data = response.json()
            count = data.get('meta', {}).get('count', len(data.get('data', [])))
            logger.info(f"Found {count} flights")

            return data

        except Exception as e:
            logger.error(f"Amadeus search error: {e}")
            # Пытаемся извлечь детали ошибки
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Amadeus error details: {error_detail}")
                    raise Exception(f"Amadeus API error: {error_detail}")
                except:
                    pass
            raise Exception("Flight search failed")

    def get_airport_suggestions(self, keyword):
        """Автодополнение для аэропортов"""
        if not keyword or len(keyword.strip()) < 2:
            return {'data': []}

        token = self._get_access_token()

        try:
            response = self._make_request_with_retry(
                method='GET',
                url=f"{self.base_url}/v1/reference-data/locations",
                headers={'Authorization': f'Bearer {token}'},
                params={
                    'subType': 'AIRPORT',
                    'keyword': keyword.strip(),
                    'page[limit]': 5
                },
                max_retries=1  # не критично, можно не повторять много раз
            )

            return response.json()

        except Exception as e:
            logger.warning(f"Airport suggestions error (non-critical): {e}")
            return {'data': []}  # всегда возвращаем что-то