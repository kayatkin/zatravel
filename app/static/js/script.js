class FlightSearchApp {
    constructor() {
        this.isSearching = false;
        this.initEventListeners();
        this.setDefaultDates();
        this.setupDebugTools();
    }

    initEventListeners() {
        const form = document.getElementById('searchForm');
        if (form) {
            // Клонируем форму, чтобы сбросить старые обработчики
            const newForm = form.cloneNode(true);
            form.parentNode.replaceChild(newForm, form);
            
            // Добавляем новый обработчик
            newForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.searchFlights();
            });
        }

        // Автодополнение аэропортов
        ['originInput', 'destinationInput'].forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                // Удаляем старые обработчики
                input.oninput = null;
                input.addEventListener('input', this.debounce((e) => this.handleAirportSuggestions(e), 500));
            }
        });
    }

    setDefaultDates() {
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 2);
        
        const todayStr = today.toISOString().split('T')[0];
        const tomorrowStr = tomorrow.toISOString().split('T')[0];
        
        const departureDate = document.getElementById('departureDate');
        const returnDate = document.getElementById('returnDate');
        
        if (departureDate) {
            departureDate.min = todayStr;
            departureDate.value = tomorrowStr;
        }
        if (returnDate) returnDate.min = todayStr;
    }

    setupDebugTools() {
        const debugBtn = document.createElement('button');
        debugBtn.type = 'button';
        debugBtn.className = 'btn btn-outline-info btn-sm mt-3';
        debugBtn.innerHTML = '<i class="bi bi-bug"></i> Режим отладки';
        debugBtn.onclick = () => this.toggleDebugMode();
        
        const form = document.getElementById('searchForm');
        if (form) form.appendChild(debugBtn);
    }

    toggleDebugMode() {
        const debugMode = localStorage.getItem('debugMode') === 'true';
        localStorage.setItem('debugMode', !debugMode);
        alert(`Режим отладки ${!debugMode ? 'включен' : 'выключен'}`);
    }

    showError(message) {
        const isDebug = localStorage.getItem('debugMode') === 'true';
        if (isDebug) {
            console.error('Error:', message);
        }
        alert('Ошибка: ' + message);
    }

    showLoading(show) {
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        
        if (loading) loading.style.display = show ? 'block' : 'none';
        if (results) {
            if (show) {
                results.classList.remove('show');
            } else {
                results.classList.add('show');
            }
        }

        const submitBtn = document.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = show;
            submitBtn.innerHTML = show ? 
                '<i class="bi bi-hourglass-split"></i> Поиск...' : 
                '<i class="bi bi-search"></i> Найти билеты';
        }
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    async searchFlights() {
        if (this.isSearching) {
            console.log('Поиск уже выполняется...');
            return;
        }

        this.isSearching = true;

        const originInput = document.getElementById('originInput');
        const destinationInput = document.getElementById('destinationInput');
        const departureDate = document.getElementById('departureDate');
        const returnDate = document.getElementById('returnDate');
        const passengers = document.getElementById('passengers');

        if (!originInput || !destinationInput || !departureDate || !passengers) {
            this.showError('Не все поля формы найдены');
            this.isSearching = false;
            return;
        }

        const cleanAirportCode = (code) => {
            return code.split('(').pop().replace(')', '').trim().toUpperCase();
        };

        const formData = {
            origin: cleanAirportCode(originInput.value),
            destination: cleanAirportCode(destinationInput.value),
            departureDate: departureDate.value,
            returnDate: returnDate ? returnDate.value : '',
            adults: passengers.value,
            maxResults: 10
        };

        if (!formData.origin || !formData.destination || !formData.departureDate) {
            this.showError('Заполните все обязательные поля');
            this.isSearching = false;
            return;
        }

        if (formData.origin.length < 3 || formData.destination.length < 3) {
            this.showError('Введите корректные коды аэропортов (например: SVO, IST, LED)');
            this.isSearching = false;
            return;
        }

        this.showLoading(true);

        try {
            console.log('🚀 Отправка запроса с данными:', formData);
            
            const response = await fetch('/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const data = await response.json();
            console.log('✅ Получен ответ:', data);

            if (!response.ok) {
                throw new Error(data.error || `Ошибка сервера: ${response.status}`);
            }

            if (data.success) {
                this.displayResults(data.flights || []);
            } else {
                this.showError(data.error || 'Произошла ошибка при поиске');
            }
        } catch (error) {
            console.error('❌ Ошибка поиска:', error);
            this.showError(error.message || 'Ошибка сети. Проверьте консоль для подробностей.');
        } finally {
            this.showLoading(false);
            this.isSearching = false;
        }
    }

    displayResults(flights) {
        console.log('📊 Отображаем рейсы:', flights);
        console.log('🔢 Количество рейсов:', flights.length);

        const resultsDiv = document.getElementById('flightResults');
        if (!resultsDiv) {
            console.error('❌ Элемент #flightResults не найден!');
            return;
        }

        const loadingDiv = document.getElementById('loading');
        if (loadingDiv) loadingDiv.style.display = 'none';

        resultsDiv.innerHTML = '';

        if (!flights || flights.length === 0) {
            resultsDiv.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i> Рейсы не найдены. Попробуйте изменить параметры поиска.
                </div>
            `;
            return;
        }

        try {
            const flightsHTML = flights.map((flight, index) => {
                try {
                    const price = flight.price || 'N/A';
                    const currency = flight.currency || 'EUR';
                    const segments = flight.segments || [];

                    console.log(`✈️ Рейс ${index + 1}:`, flight);

                    return `
                        <div class="card mb-3 flight-card" style="animation-delay: ${index * 0.1}s">
                            <div class="card-body">
                                <div class="row align-items-center">
                                    <div class="col-md-3 text-center">
                                        <h4 class="text-primary mb-1">${price} ${currency}</h4>
                                        <small class="text-muted">за пассажира</small>
                                    </div>
                                    <div class="col-md-6">
                                        ${this.formatSegments(segments)}
                                    </div>
                                    <div class="col-md-3">
                                        <div class="d-grid gap-2">
                                            <button class="btn btn-primary" onclick="alert('Бронирование рейса №${index + 1}')">
                                                <i class="bi bi-cart3"></i> Выбрать
                                            </button>
                                            <button class="btn btn-outline-secondary" onclick="this.closest('.flight-card').classList.toggle('expanded')">
                                                <i class="bi bi-info-circle"></i> Подробнее
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                } catch (error) {
                    console.error('❌ Ошибка форматирования рейса:', error, flight);
                    return `
                        <div class="card mb-3 border-danger">
                            <div class="card-body">
                                <div class="text-danger">
                                    <i class="bi bi-exclamation-triangle"></i> Ошибка отображения рейса
                                </div>
                                <div class="mt-2">
                                    <button class="btn btn-sm btn-outline-secondary" onclick="console.log('Flight data:', ${JSON.stringify(flight)})">
                                        Посмотреть данные
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                }
            }).join('');

            resultsDiv.innerHTML = flightsHTML;

            const resultsContainer = document.getElementById('results');
            if (resultsContainer) {
                resultsContainer.style.display = 'block';
                resultsContainer.classList.add('show');
            }

        } catch (error) {
            console.error('❌ Критическая ошибка отображения:', error);
            resultsDiv.innerHTML = `
                <div class="alert alert-danger">
                    <h6><i class="bi bi-exclamation-triangle"></i> Ошибка отображения</h6>
                    <p>Произошла ошибка при отображении результатов.</p>
                    <button class="btn btn-sm btn-outline-secondary mt-2" onclick="console.log('Flights ', ${JSON.stringify(flights)})">
                        Посмотреть данные в консоли
                    </button>
                </div>
            `;
        }
    }

    formatSegments(segments) {
        if (!segments || !Array.isArray(segments) || segments.length === 0) {
            return '<div class="text-muted">Информация о маршруте недоступна</div>';
        }

        return segments.map((segment, idx) => `
            <div class="flight-segment mb-2 p-2 bg-light rounded">
                <div class="d-flex justify-content-between fw-bold">
                    <span>${segment.departure_airport}</span>
                    <span>→</span>
                    <span>${segment.arrival_airport}</span>
                </div>
                <div class="d-flex justify-content-between text-muted small">
                    <span>${this.formatDateTime(segment.departure_time)}</span>
                    <span>${this.formatDuration(segment.duration)}</span>
                    <span>${this.formatDateTime(segment.arrival_time)}</span>
                </div>
                <div class="text-end mt-1">
                    <span class="badge bg-secondary">${segment.airline} ${segment.flight_number}</span>
                </div>
            </div>
        `).join('');
    }

    formatDateTime(dateTimeString) {
        if (!dateTimeString) return '--:--';
        try {
            const date = new Date(dateTimeString);
            return date.toLocaleString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return dateTimeString;
        }
    }

    formatDuration(duration) {
        if (!duration) return 'N/A';
        return duration.replace('PT', '')
                      .replace('H', 'ч ')
                      .replace('M', 'м')
                      .replace('S', 'с')
                      .trim();
    }

    async handleAirportSuggestions(event) {
        const inputId = event.target.id;
        const suggestionsId = inputId === 'originInput' ? 'originSuggestions' : 'destinationSuggestions';
        const suggestions = document.getElementById(suggestionsId);
        const query = event.target.value.trim();

        if (query.length < 2) {
            suggestions.innerHTML = '';
            suggestions.style.display = 'none';
            return;
        }

        try {
            const response = await fetch(`/api/airports?q=${encodeURIComponent(query)}`);
            const airports = await response.json();

            if (!Array.isArray(airports) || airports.length === 0) {
                suggestions.innerHTML = '<div class="dropdown-item text-muted">Ничего не найдено</div>';
                suggestions.style.display = 'block';
                return;
            }

            suggestions.innerHTML = airports.map(airport => `
                <div class="dropdown-item" data-code="${airport.code}" 
                     data-name="${airport.name}" data-city="${airport.city}">
                    <strong>${airport.code}</strong> - ${airport.name}
                    ${airport.city ? `<br><small class="text-muted">${airport.city}, ${airport.country}</small>` : ''}
                </div>
            `).join('');

            suggestions.style.display = 'block';

            // Удаляем старые обработчики
            suggestions.querySelectorAll('.dropdown-item').forEach(item => {
                item.onclick = null;
                item.addEventListener('click', () => {
                    const code = item.getAttribute('data-code');
                    const name = item.getAttribute('data-name');
                    event.target.value = `${name} (${code})`;
                    suggestions.style.display = 'none';
                });
            });

        } catch (error) {
            console.error('❌ Ошибка автодополнения:', error);
            suggestions.innerHTML = '<div class="dropdown-item text-danger">Ошибка загрузки</div>';
            suggestions.style.display = 'block';
        }
    }
}

// Инициализируем приложение только после загрузки DOM
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔄 Инициализация приложения...');
    const app = new FlightSearchApp();
    window.flightApp = app;
    console.log('✅ ZaTravel app initialized');
});

function testSearch(origin = 'SVO', destination = 'IST') {
    document.getElementById('originInput').value = origin;
    document.getElementById('destinationInput').value = destination;
    document.getElementById('departureDate').value = '2025-06-15';
    window.flightApp.searchFlights();
}