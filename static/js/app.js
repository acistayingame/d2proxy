// JavaScript для веб-панели сканера портов

let scanInterval = null;
let isScanning = false;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Обработчики событий
    document.getElementById('scanForm').addEventListener('submit', handleScanSubmit);
    document.getElementById('stopBtn').addEventListener('click', handleStopScan);
    
    // Проверяем статус при загрузке
    checkScanStatus();
}

// Обработка отправки формы сканирования
function handleScanSubmit(e) {
    e.preventDefault();
    
    if (isScanning) {
        showError('Сканирование уже выполняется');
        return;
    }
    
    const formData = {
        target: document.getElementById('target').value.trim(),
        username: document.getElementById('username').value.trim(),
        password: document.getElementById('password').value.trim(),
        port_range: 'all_ports',  // Всегда многопоточное сканирование всех портов
        scan_type: 'aggressive'   // Всегда агрессивный метод
    };
    
    // Валидация
    if (!formData.target) {
        showError('Укажите целевой хост');
        return;
    }
    
    // Логин и пароль теперь необязательны
    // if (!formData.username) {
    //     showError('Укажите имя пользователя');
    //     return;
    // }
    
    // if (!formData.password) {
    //     showError('Укажите пароль');
    //     return;
    // }
    
    // Запуск сканирования
    startScan(formData);
}

// Запуск сканирования
function startScan(data) {
    fetch('/scan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showError(data.error);
        } else {
            showSuccess('Сканирование запущено');
            isScanning = true;
            showStatusCard();
            startStatusUpdates();
        }
    })
    .catch(error => {
        showError('Ошибка при запуске сканирования: ' + error.message);
    });
}

// Остановка сканирования
function handleStopScan() {
    fetch('/stop', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showError(data.error);
        } else {
            showInfo('Сканирование остановлено');
            stopStatusUpdates();
            hideStatusCard();
        }
    })
    .catch(error => {
        showError('Ошибка при остановке сканирования: ' + error.message);
    });
}

// Показ карточки статуса
function showStatusCard() {
    const statusCard = document.getElementById('statusCard');
    statusCard.style.display = 'block';
    statusCard.classList.add('fade-in');
    
    const stopBtn = document.getElementById('stopBtn');
    stopBtn.style.display = 'block';
}

// Скрытие карточки статуса
function hideStatusCard() {
    const statusCard = document.getElementById('statusCard');
    statusCard.style.display = 'none';
    isScanning = false;
}

// Запуск обновления статуса
function startStatusUpdates() {
    scanInterval = setInterval(checkScanStatus, 1000);
}

// Остановка обновления статуса
function stopStatusUpdates() {
    if (scanInterval) {
        clearInterval(scanInterval);
        scanInterval = null;
    }
}

// Проверка статуса сканирования
function checkScanStatus() {
    fetch('/status')
    .then(response => response.json())
    .then(data => {
        updateStatusDisplay(data);
        
        // Если сканирование завершено
        if (!data.is_running && data.results) {
            stopStatusUpdates();
            isScanning = false;
            showResults(data.results);
            hideStatusCard();
        }
        
        // Если произошла ошибка
        if (!data.is_running && data.error) {
            stopStatusUpdates();
            isScanning = false;
            showError(data.error);
            hideStatusCard();
        }
    })
    .catch(error => {
        console.error('Ошибка при проверке статуса:', error);
    });
}

// Обновление отображения статуса
function updateStatusDisplay(status) {
    const progressBar = document.getElementById('progressBar');
    const statusText = document.getElementById('statusText');
    
    if (status.is_running) {
        progressBar.style.width = status.progress + '%';
        progressBar.textContent = status.progress + '%';
        
        if (status.current_target) {
            statusText.innerHTML = `
                <i class="fas fa-spinner fa-spin"></i> 
                Сканирование ${status.current_target}... (${status.progress}%)
            `;
        }
    } else if (status.results) {
        progressBar.style.width = '100%';
        progressBar.textContent = '100%';
        statusText.innerHTML = '<i class="fas fa-check-circle text-success"></i> Сканирование завершено';
    } else if (status.error) {
        statusText.innerHTML = '<i class="fas fa-exclamation-triangle text-danger"></i> ' + status.error;
    }
}

// Показ результатов сканирования
function showResults(results) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsContent = document.getElementById('resultsContent');
    
    console.log('Отображение результатов:', results);
    
    let html = `
        <div class="row">
            <div class="col-md-6">
                <h6><i class="fas fa-info-circle"></i> Информация о сканировании</h6>
                <ul class="list-unstyled">
                    <li><strong>Цель:</strong> ${results.target}</li>
                    <li><strong>Пользователь:</strong> ${results.username}</li>
                    <li><strong>Время сканирования:</strong> ${results.scan_time ? results.scan_time.toFixed(2) + ' сек' : 'Неизвестно'}</li>
                    <li><strong>Время завершения:</strong> ${new Date(results.timestamp).toLocaleString()}</li>
                </ul>
            </div>
            <div class="col-md-6">
                <h6><i class="fas fa-chart-bar"></i> Статистика</h6>
                <div class="row">
                    <div class="col-6">
                        <div class="text-center">
                            <div class="h3 text-primary">${results.open_ports ? results.open_ports.length : 0}</div>
                            <small>Открытых портов</small>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="text-center">
                            <div class="h3 text-success">${results.successful_connections ? results.successful_connections.length : 0}</div>
                            <small>Успешных подключений</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    if (results.open_ports && results.open_ports.length > 0) {
        html += `
            <hr>
            <h6><i class="fas fa-list"></i> Найденные порты (${results.open_ports.length})</h6>
            <div class="row">
        `;
        
        results.open_ports.forEach(port => {
            const service = results.service_info && results.service_info[port] ? results.service_info[port] : {};
            const connection = results.successful_connections ? results.successful_connections.find(conn => conn[0] === port) : null;
            
            html += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="port-item">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <div class="port-number">Порт ${port}</div>
                                <div class="service-name">${service.name || 'Неизвестный сервис'}</div>
                                ${service.version ? `<div class="service-version">${service.version}</div>` : ''}
                            </div>
                            <div>
                                ${connection ? 
                                    '<span class="connection-status connection-success">Подключен</span>' : 
                                    '<span class="connection-status connection-failed">Не подключен</span>'
                                }
                            </div>
                        </div>
                        ${connection ? `<small class="text-success">${connection[1]}</small>` : ''}
                        ${connection ? `
                            <div class="mt-2">
                                <button class="btn btn-outline-primary btn-sm" onclick="openManagementModal(${port}, '${connection[1]}', '${results.target}')">
                                    <i class="fas fa-cog"></i> Управлять
                                </button>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        
        // Кнопки действий убраны
    } else {
        html += `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i> 
                Открытые порты не найдены. Возможные причины:
                <ul class="mt-2 mb-0">
                    <li>Целевой хост недоступен</li>
                    <li>Файрвол блокирует соединения</li>
                    <li>Неправильный диапазон портов</li>
                    <li>Проблемы с nmap</li>
                </ul>
            </div>
        `;
    }
    
    resultsContent.innerHTML = html;
    resultsSection.style.display = 'block';
    resultsSection.classList.add('fade-in');
}

// Функция больше не нужна - убрана возможность выбора портов

// Показ уведомлений
function showAlert(type, message) {
    const alertClass = type === 'warning' ? 'alert-warning' : 
                     type === 'info' ? 'alert-info' : 
                     type === 'success' ? 'alert-success' : 'alert-danger';
    
    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            <i class="fas fa-info-circle"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Добавляем уведомление в начало формы
    const form = document.getElementById('scanForm');
    const existingAlert = form.querySelector('.alert');
    if (existingAlert) {
        existingAlert.remove();
    }
    
    form.insertAdjacentHTML('afterbegin', alertHtml);
}

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

// Показ модального окна с ошибкой
function showErrorModal(message) {
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    
    const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
    errorModal.show();
}

// Очистка формы
function clearForm() {
    document.getElementById('scanForm').reset();
    document.getElementById('port_range').value = '1-1000';
    document.getElementById('scan_type').value = 'fast';
}

// Функции управления подключениями
function openManagementModal(port, serviceType, target) {
    console.log(`Открытие управления для порта ${port}, сервис: ${serviceType}, цель: ${target}`);
    
    if (serviceType === 'SSH') {
        openSshModal(port, target);
    } else if (serviceType === 'RDP') {
        openRdpModal(port, target);
    } else if (serviceType === 'VNC') {
        openVncModal(port, target);
    } else {
        showError('Тип сервиса не поддерживается для управления');
    }
}

function openSshModal(port, target) {
    document.getElementById('sshTarget').value = target;
    document.getElementById('sshPort').value = port;
    
    const modal = new bootstrap.Modal(document.getElementById('sshManagementModal'));
    modal.show();
    
    // Инициализируем терминал после показа модального окна
    setTimeout(() => {
        initSshTerminal(target, port);
    }, 500);
}

function openRdpModal(port, target) {
    document.getElementById('rdpTarget').value = target;
    document.getElementById('rdpPort').value = port;
    
    const modal = new bootstrap.Modal(document.getElementById('rdpManagementModal'));
    modal.show();
    
    // Инициализируем RDP клиент после показа модального окна
    setTimeout(() => {
        initRdpClient(target, port);
    }, 500);
}

function openVncModal(port, target) {
    document.getElementById('vncTarget').value = target;
    document.getElementById('vncPort').value = port;
    
    const modal = new bootstrap.Modal(document.getElementById('vncManagementModal'));
    modal.show();
    
    // Инициализируем VNC клиент после показа модального окна
    setTimeout(() => {
        initVncClient(target, port);
    }, 500);
}

// Функции копирования команд
function copySshCommand() {
    const command = document.getElementById('sshCommand').value;
    navigator.clipboard.writeText(command)
        .then(() => showSuccess('SSH команда скопирована в буфер обмена'))
        .catch(() => showError('Не удалось скопировать команду'));
}

function copyRdpCommand() {
    const command = document.getElementById('rdpCommand').value;
    navigator.clipboard.writeText(command)
        .then(() => showSuccess('RDP адрес скопирован в буфер обмена'))
        .catch(() => showError('Не удалось скопировать адрес'));
}

function copyVncCommand() {
    const command = document.getElementById('vncCommand').value;
    navigator.clipboard.writeText(command)
        .then(() => showSuccess('VNC адрес скопирован в буфер обмена'))
        .catch(() => showError('Не удалось скопировать адрес'));
}

// Инициализация SSH терминала
function initSshTerminal(target, port) {
    const terminalContainer = document.getElementById('sshTerminal');
    terminalContainer.innerHTML = ''; // Очищаем контейнер
    
    const terminal = new Terminal({
        cursorBlink: true,
        theme: {
            background: '#000000',
            foreground: '#ffffff'
        }
    });
    
    const fitAddon = new FitAddon.FitAddon();
    const webLinksAddon = new WebLinksAddon.WebLinksAddon();
    
    terminal.loadAddon(fitAddon);
    terminal.loadAddon(webLinksAddon);
    terminal.open(terminalContainer);
    fitAddon.fit();
    
    // Приветственное сообщение
    terminal.writeln('\x1b[32mSSH Терминал\x1b[0m');
    terminal.writeln(`Подключение к: ${target}:${port}`);
    terminal.writeln('Введите команду для подключения:');
    terminal.write('$ ');
    
    // Обработка ввода
    terminal.onData(data => {
        terminal.write(data);
        
        if (data === '\r') { // Enter
            const line = terminal.buffer.active.getLine(terminal.buffer.active.cursorY).translateToString().trim();
            if (line.startsWith('$ ')) {
                const command = line.substring(2);
                handleSshCommand(command, target, port, terminal);
            }
        }
    });
}

// Обработка SSH команд
function handleSshCommand(command, target, port, terminal) {
    if (command === 'ssh' || command.startsWith('ssh ')) {
        terminal.writeln('');
        terminal.writeln('\x1b[33mПодключение к SSH серверу...\x1b[0m');
        terminal.writeln('Используйте: ssh username@' + target + ' -p ' + port);
        terminal.writeln('Или введите полную команду подключения');
        terminal.write('$ ');
    } else if (command.startsWith('ssh ') && command.includes('@')) {
        terminal.writeln('');
        terminal.writeln('\x1b[31mОшибка: Прямое SSH подключение через браузер не поддерживается\x1b[0m');
        terminal.writeln('\x1b[33mИспользуйте внешний SSH клиент\x1b[0m');
        terminal.write('$ ');
    } else if (command === 'help') {
        terminal.writeln('');
        terminal.writeln('\x1b[36mДоступные команды:\x1b[0m');
        terminal.writeln('  ssh - показать команду подключения');
        terminal.writeln('  help - показать эту справку');
        terminal.writeln('  clear - очистить терминал');
        terminal.write('$ ');
    } else if (command === 'clear') {
        terminal.clear();
        terminal.write('$ ');
    } else {
        terminal.writeln('');
        terminal.writeln(`\x1b[31mКоманда не найдена: ${command}\x1b[0m`);
        terminal.writeln('Введите "help" для справки');
        terminal.write('$ ');
    }
}

// Инициализация RDP клиента
function initRdpClient(target, port) {
    const canvas = document.getElementById('rdpCanvas');
    const status = document.getElementById('rdpStatus');
    
    status.innerHTML = `
        <i class="fas fa-exclamation-triangle fa-2x text-warning"></i>
        <p>RDP клиент в браузере не поддерживается</p>
        <p>Используйте Microsoft Remote Desktop</p>
        <p>Адрес: ${target}:${port}</p>
    `;
}

// Инициализация VNC клиента
function initVncClient(target, port) {
    const canvas = document.getElementById('vncCanvas');
    const status = document.getElementById('vncStatus');
    
    status.innerHTML = `
        <i class="fas fa-exclamation-triangle fa-2x text-warning"></i>
        <p>VNC клиент в браузере требует дополнительной настройки</p>
        <p>Используйте VNC клиент</p>
        <p>Адрес: ${target}:${port}</p>
    `;
}
