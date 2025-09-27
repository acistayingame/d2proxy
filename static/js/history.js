// JavaScript для страницы истории сканирований

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    loadHistory();
});

// Загрузка истории сканирований
function loadHistory() {
    fetch('/api/history')
    .then(response => response.json())
    .then(data => {
        displayHistory(data);
    })
    .catch(error => {
        console.error('Ошибка при загрузке истории:', error);
        showError('Ошибка при загрузке истории сканирований');
    });
}

// Отображение истории
function displayHistory(history) {
    const historyContent = document.getElementById('historyContent');
    
    if (!history || history.length === 0) {
        historyContent.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-history fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">История сканирований пуста</h5>
                <p class="text-muted">Выполните первое сканирование, чтобы увидеть результаты здесь</p>
                <a href="/" class="btn btn-primary">
                    <i class="fas fa-search"></i> Начать сканирование
                </a>
            </div>
        `;
        return;
    }
    
    let html = '';
    
    history.forEach((scan, index) => {
        html += createHistoryItem(scan, index);
    });
    
    historyContent.innerHTML = html;
}

// Создание элемента истории
function createHistoryItem(scan, index) {
    const scanDate = new Date(scan.timestamp).toLocaleString();
    const scanDuration = scan.scan_time ? scan.scan_time.toFixed(2) + ' сек' : 'Неизвестно';
    
    return `
        <div class="history-item fade-in" style="animation-delay: ${index * 0.1}s">
            <div class="history-header">
                <div>
                    <div class="history-target">
                        <i class="fas fa-server"></i> ${scan.target}
                    </div>
                    <div class="history-time">
                        <i class="fas fa-clock"></i> ${scanDate}
                    </div>
                </div>
                <div class="dropdown">
                    <button class="btn btn-outline-secondary btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown">
                        <i class="fas fa-ellipsis-v"></i>
                    </button>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="#" onclick="viewScanDetails(${index})">
                            <i class="fas fa-eye"></i> Подробности
                        </a></li>
                        <li><a class="dropdown-item" href="#" onclick="exportScan(${index})">
                            <i class="fas fa-download"></i> Экспорт
                        </a></li>
                        <li><a class="dropdown-item" href="#" onclick="copyScanResults(${index})">
                            <i class="fas fa-copy"></i> Копировать
                        </a></li>
                    </ul>
                </div>
            </div>
            
            <div class="history-stats">
                <div class="stat-item">
                    <div class="stat-number">${scan.open_ports.length}</div>
                    <div class="stat-label">Открытых портов</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">${scan.successful_connections.length}</div>
                    <div class="stat-label">Подключений</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">${scanDuration}</div>
                    <div class="stat-label">Время сканирования</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">${scan.scan_type}</div>
                    <div class="stat-label">Тип сканирования</div>
                </div>
            </div>
            
            ${scan.open_ports.length > 0 ? `
                <div class="mt-3">
                    <h6><i class="fas fa-list"></i> Найденные порты:</h6>
                    <div class="row">
                        ${scan.open_ports.slice(0, 6).map(port => {
                            const service = scan.service_info[port] || {};
                            const connection = scan.successful_connections.find(conn => conn[0] === port);
                            return `
                                <div class="col-md-4 col-sm-6 mb-2">
                                    <div class="d-flex align-items-center">
                                        <span class="badge bg-primary me-2">${port}</span>
                                        <small class="text-muted">${service.name || 'Неизвестный'}</small>
                                        ${connection ? '<i class="fas fa-check-circle text-success ms-2"></i>' : ''}
                                    </div>
                                </div>
                            `;
                        }).join('')}
                        ${scan.open_ports.length > 6 ? `
                            <div class="col-12">
                                <small class="text-muted">... и еще ${scan.open_ports.length - 6} портов</small>
                            </div>
                        ` : ''}
                    </div>
                </div>
            ` : `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i> Открытые порты не найдены
                </div>
            `}
        </div>
    `;
}

// Просмотр деталей сканирования
function viewScanDetails(index) {
    // В будущем можно добавить модальное окно с подробностями
    console.log('Просмотр деталей сканирования:', index);
    showInfo('Функция просмотра деталей будет добавлена в следующей версии');
}

// Экспорт результатов сканирования
function exportScan(index) {
    // В будущем можно добавить экспорт в CSV/JSON
    console.log('Экспорт сканирования:', index);
    showInfo('Функция экспорта будет добавлена в следующей версии');
}

// Копирование результатов сканирования
function copyScanResults(index) {
    // В будущем можно добавить копирование результатов
    console.log('Копирование результатов сканирования:', index);
    showInfo('Функция копирования будет добавлена в следующей версии');
}

// Показ уведомлений
function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'danger');
}

function showInfo(message) {
    showNotification(message, 'info');
}

function showNotification(message, type) {
    // Создаем уведомление
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Автоматически скрываем через 5 секунд
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Фильтрация истории
function filterHistory(filter) {
    // В будущем можно добавить фильтрацию по дате, типу сканирования и т.д.
    console.log('Фильтрация истории:', filter);
}

// Поиск в истории
function searchHistory(query) {
    // В будущем можно добавить поиск по целевым хостам
    console.log('Поиск в истории:', query);
}

// Сортировка истории
function sortHistory(sortBy) {
    // В будущем можно добавить сортировку по дате, количеству портов и т.д.
    console.log('Сортировка истории по:', sortBy);
}

