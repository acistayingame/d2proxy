#!/bin/bash

# Скрипт для запуска веб-панели сканера портов

echo "🌐 Запуск веб-панели сканера портов..."
echo

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Ошибка: Python 3 не найден. Установите Python 3.6 или выше."
    exit 1
fi

# Проверка наличия pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ Ошибка: pip3 не найден. Установите pip3."
    exit 1
fi

# Установка зависимостей если нужно
if [ ! -f "web_requirements_installed" ]; then
    echo "📦 Установка зависимостей для веб-приложения..."
    pip3 install -r requirements_web.txt
    if [ $? -eq 0 ]; then
        touch web_requirements_installed
        echo "✅ Зависимости установлены успешно."
    else
        echo "❌ Ошибка при установке зависимостей."
        exit 1
    fi
fi

# Проверка nmap
if command -v nmap &> /dev/null; then
    echo "✅ Nmap найден, будет использовано быстрое сканирование"
else
    echo "⚠️  Nmap не найден, установите nmap для быстрого сканирования:"
    echo "   Ubuntu/Debian: sudo apt install nmap"
    echo "   macOS: brew install nmap"
    echo "   CentOS/RHEL: sudo yum install nmap"
    echo
fi

echo "🚀 Запуск веб-сервера..."
echo "📱 Откройте браузер и перейдите по адресу: http://localhost:8080"
echo "🛑 Для остановки нажмите Ctrl+C"
echo

# Запуск веб-приложения
python3 web_scanner.py
