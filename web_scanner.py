#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Веб-панель для сканера портов
Flask приложение с современным интерфейсом
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import subprocess
import xml.etree.ElementTree as ET
import logging

# Добавляем текущую директорию в путь для импорта сканера
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем наш сканер
from nmap_scanner_simple import NmapScanner, SimplePortScanner

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Глобальные переменные для хранения состояния сканирования
scan_status = {
    'is_running': False,
    'progress': 0,
    'current_target': '',
    'start_time': None,
    'results': None,
    'error': None
}

def run_scan_async(target, username, password, port_range, scan_type):
    """Асинхронное выполнение сканирования"""
    global scan_status
    
    try:
        scan_status['is_running'] = True
        scan_status['progress'] = 0
        scan_status['current_target'] = target
        scan_status['start_time'] = datetime.now()
        scan_status['results'] = None
        scan_status['error'] = None
        
        logger.info(f"Начинаю сканирование {target}")
        
        # Создаем сканер с агрессивным методом
        scanner = SimplePortScanner(
            target, 
            username, 
            password, 
            use_nmap=True,
            nmap_scan_type='aggressive'  # Всегда агрессивный метод
        )
        
        # Всегда используем многопоточное сканирование всех портов
        port_range_tuple = None
        logger.info("Используется многопоточное агрессивное сканирование всех портов (1-65535)")
        
        scan_status['progress'] = 25
        
        # Запускаем сканирование
        open_ports = scanner.scan_ports_fast(port_range_tuple)
        
        scan_status['progress'] = 75
        
        # Попытки подключения
        scanner.connect_to_ports()
        
        scan_status['progress'] = 100
        
        # Сохраняем результаты
        scan_status['results'] = {
            'target': target,
            'username': username,
            'scan_type': scan_type,
            'port_range': port_range,
            'open_ports': open_ports,
            'successful_connections': scanner.successful_connections,
            'service_info': scanner.nmap_scanner.service_info if scanner.nmap_scanner else {},
            'scan_time': (datetime.now() - scan_status['start_time']).total_seconds(),
            'timestamp': datetime.now().isoformat()
        }
        
        scan_status['is_running'] = False
        
        logger.info(f"Сканирование {target} завершено успешно")
        
    except Exception as e:
        scan_status['is_running'] = False
        scan_status['error'] = str(e)
        logger.error(f"Ошибка при сканировании {target}: {e}")

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/scan', methods=['POST'])
def start_scan():
    """Запуск сканирования"""
    global scan_status
    
    if scan_status['is_running']:
        return jsonify({'error': 'Сканирование уже выполняется'}), 400
    
    data = request.get_json()
    target = data.get('target', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    port_range = data.get('port_range', '1-1000').strip()
    scan_type = data.get('scan_type', 'fast').strip()
    
    if not target:
        return jsonify({'error': 'Укажите целевой хост'}), 400
    
    # Логин и пароль теперь необязательны
    # if not username:
    #     return jsonify({'error': 'Укажите имя пользователя'}), 400
    
    # if not password:
    #     return jsonify({'error': 'Укажите пароль'}), 400
    
    # Запускаем сканирование в отдельном потоке
    thread = threading.Thread(
        target=run_scan_async,
        args=(target, username, password, port_range, scan_type)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Сканирование запущено'})

@app.route('/status')
def get_status():
    """Получение статуса сканирования"""
    return jsonify(scan_status)

@app.route('/results')
def get_results():
    """Получение результатов сканирования"""
    if scan_status['results']:
        return jsonify(scan_status['results'])
    else:
        return jsonify({'error': 'Результаты недоступны'}), 404

@app.route('/stop', methods=['POST'])
def stop_scan():
    """Остановка сканирования"""
    global scan_status
    
    if scan_status['is_running']:
        scan_status['is_running'] = False
        scan_status['error'] = 'Сканирование остановлено пользователем'
        return jsonify({'message': 'Сканирование остановлено'})
    else:
        return jsonify({'error': 'Сканирование не выполняется'}), 400

@app.route('/history')
def history():
    """Страница истории сканирований"""
    return render_template('history.html')

@app.route('/api/history')
def get_history():
    """API для получения истории сканирований"""
    # В реальном приложении здесь была бы база данных
    # Пока возвращаем текущие результаты
    if scan_status['results']:
        return jsonify([scan_status['results']])
    else:
        return jsonify([])

if __name__ == '__main__':
    # Создаем директорию для шаблонов если её нет
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
    
    # Создаем директорию для статических файлов если её нет
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    print("🚀 Запуск веб-панели сканера портов...")
    print("📱 Откройте браузер и перейдите по адресу: http://localhost:8080")
    print("🛑 Для остановки нажмите Ctrl+C")
    
    app.run(debug=True, host='0.0.0.0', port=8080)
