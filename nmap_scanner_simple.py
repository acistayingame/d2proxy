#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Упрощенный сканер портов с nmap функциональностью
Только основные зависимости: paramiko, requests
"""

import socket
import time
import sys
import argparse
import getpass
import paramiko
import requests
import logging
import subprocess
import xml.etree.ElementTree as ET
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nmap_scanner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NmapScanner:
    def __init__(self, target_host, nmap_args=None):
        self.target_host = target_host
        self.nmap_args = nmap_args or []
        self.open_ports = []
        self.service_info = {}
        
    def check_nmap_installed(self):
        """Проверяет, установлен ли nmap"""
        try:
            result = subprocess.run(['nmap', '--version'], 
                                 capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def run_nmap_scan(self, port_range=None, scan_type='fast'):
        """Запускает nmap сканирование с оптимизацией"""
        if not self.check_nmap_installed():
            logger.error("Nmap не установлен. Установите nmap для быстрого сканирования.")
            return []
        
        # Если сканируем все порты, используем многопоточный подход
        if port_range is None or (isinstance(port_range, tuple) and port_range[0] == 1 and port_range[1] == 65535):
            return self.run_parallel_nmap_scan(scan_type)
        
        # Обычное сканирование для небольших диапазонов
        return self.run_single_nmap_scan(port_range, scan_type)
    
    def run_parallel_nmap_scan(self, scan_type='fast'):
        """Многопоточное сканирование всех портов"""
        logger.info("Запуск многопоточного сканирования всех портов")
        
        # Разбиваем порты на части для параллельного сканирования
        port_ranges = [
            (1, 20000),
            (20001, 40000), 
            (40001, 65535)
        ]
        
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        all_open_ports = []
        all_service_info = {}
        threads = []
        results = {}
        
        def scan_range(port_range, thread_id):
            """Сканирует диапазон портов в отдельном потоке"""
            try:
                logger.info(f"Поток {thread_id}: Сканирование портов {port_range[0]}-{port_range[1]}")
                result = self.run_single_nmap_scan(port_range, scan_type)
                results[thread_id] = {
                    'ports': result,
                    'services': getattr(self, 'service_info', {}),
                    'thread_id': thread_id
                }
                logger.info(f"Поток {thread_id}: Найдено {len(result)} портов")
            except Exception as e:
                logger.error(f"Ошибка в потоке {thread_id}: {e}")
                results[thread_id] = {'ports': [], 'services': {}, 'thread_id': thread_id}
        
        # Запускаем потоки
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(scan_range, port_range, i): i 
                for i, port_range in enumerate(port_ranges)
            }
            
            for future in as_completed(futures):
                thread_id = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Ошибка в потоке {thread_id}: {e}")
        
        # Собираем результаты
        for thread_id in range(len(port_ranges)):
            if thread_id in results:
                all_open_ports.extend(results[thread_id]['ports'])
                all_service_info.update(results[thread_id]['services'])
        
        scan_time = time.time() - start_time
        logger.info(f"Многопоточное сканирование завершено за {scan_time:.2f} секунд")
        logger.info(f"Всего найдено {len(all_open_ports)} открытых портов")
        
        self.open_ports = all_open_ports
        self.service_info = all_service_info
        
        return all_open_ports
    
    def run_single_nmap_scan(self, port_range, scan_type='fast'):
        """Обычное сканирование nmap для одного диапазона"""
        # Базовые аргументы nmap
        nmap_cmd = ['nmap']
        
        if scan_type == 'fast':
            # Быстрое сканирование - используем TCP если нет root
            nmap_cmd.extend(['-sT', '-sV', '--open', '-T4'])
        elif scan_type == 'stealth':
            # Скрытое сканирование - используем TCP если нет root
            nmap_cmd.extend(['-sT', '-sV', '--open', '-T2'])
        elif scan_type == 'aggressive':
            # Агрессивное сканирование - используем TCP если нет root
            nmap_cmd.extend(['-sT', '-sV', '--open', '-T5'])
        
        # Диапазон портов
        if port_range:
            if isinstance(port_range, tuple):
                nmap_cmd.extend(['-p', f"{port_range[0]}-{port_range[1]}"])
            else:
                nmap_cmd.extend(['-p', str(port_range)])
        else:
            nmap_cmd.extend(['-p-'])  # Все порты
        
        # Дополнительные аргументы
        nmap_cmd.extend(self.nmap_args)
        
        # Целевой хост
        nmap_cmd.append(self.target_host)
        
        # Выходной файл в временной директории
        import tempfile
        temp_dir = tempfile.gettempdir()
        output_file = os.path.join(temp_dir, f"nmap_scan_{self.target_host.replace('.', '_')}_{port_range[0]}_{port_range[1]}")
        nmap_cmd.extend(['-oA', output_file])
        
        logger.info(f"Запуск nmap: {' '.join(nmap_cmd)}")
        
        try:
            # Запуск nmap
            result = subprocess.run(nmap_cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                # Парсинг XML результата
                xml_file = f"{output_file}.xml"
                if os.path.exists(xml_file):
                    return self.parse_nmap_xml(xml_file)
                else:
                    # Парсинг текстового вывода
                    return self.parse_nmap_output(result.stdout)
            else:
                logger.error(f"Ошибка nmap: {result.stderr}")
                return []
                
        except subprocess.TimeoutExpired:
            logger.error("Nmap сканирование превысило таймаут")
            return []
        except Exception as e:
            logger.error(f"Ошибка при запуске nmap: {e}")
            return []
    
    def parse_nmap_xml(self, xml_file):
        """Парсит XML результат nmap"""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            open_ports = []
            service_info = {}
            
            for host in root.findall('host'):
                for port in host.find('ports').findall('port'):
                    port_id = int(port.get('portid'))
                    state = port.find('state')
                    
                    if state is not None and state.get('state') == 'open':
                        open_ports.append(port_id)
                        
                        # Информация о сервисе
                        service = port.find('service')
                        if service is not None:
                            service_name = service.get('name', 'unknown')
                            service_version = service.get('version', '')
                            service_info[port_id] = {
                                'name': service_name,
                                'version': service_version,
                                'product': service.get('product', ''),
                                'extrainfo': service.get('extrainfo', '')
                            }
            
            self.open_ports = open_ports
            self.service_info = service_info
            
            logger.info(f"Nmap нашел {len(open_ports)} открытых портов")
            return open_ports
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге XML nmap: {e}")
            return []
    
    def parse_nmap_output(self, output):
        """Парсит текстовый вывод nmap"""
        open_ports = []
        service_info = {}
        
        lines = output.split('\n')
        in_port_section = False
        
        logger.info(f"Парсинг вывода nmap: {len(lines)} строк")
        
        for line in lines:
            line = line.strip()
            logger.debug(f"Обработка строки: {line}")
            
            # Начало секции портов
            if 'PORT' in line and 'STATE' in line and 'SERVICE' in line:
                in_port_section = True
                logger.info("Найдена секция портов")
                continue
            
            # Конец секции портов
            if in_port_section and (line == '' or line.startswith('Nmap scan report') or line.startswith('MAC Address')):
                in_port_section = False
                continue
            
            # Парсинг строки порта
            if in_port_section and '/' in line and 'open' in line:
                logger.info(f"Найдена строка порта: {line}")
                parts = line.split()
                if len(parts) >= 3:
                    port_info = parts[0].split('/')
                    if len(port_info) == 2:
                        try:
                            port = int(port_info[0])
                            protocol = port_info[1]
                            state = parts[1]
                            
                            if state == 'open':
                                open_ports.append(port)
                                logger.info(f"Найден открытый порт: {port}")
                                
                                # Информация о сервисе
                                service_name = parts[2] if len(parts) >= 3 else 'unknown'
                                service_version = ' '.join(parts[3:]) if len(parts) > 3 else ''
                                
                                # Правильное определение RDP и VNC
                                if port == 3389:
                                    service_name = 'ms-wbt-server'  # RDP
                                elif port in [5900, 5901, 5902, 5903, 5904, 5905]:
                                    service_name = 'vnc'  # VNC
                                elif port == 22:
                                    service_name = 'ssh'
                                elif port == 80:
                                    service_name = 'http'
                                elif port == 443:
                                    service_name = 'https'
                                elif port == 21:
                                    service_name = 'ftp'
                                elif port == 23:
                                    service_name = 'telnet'
                                
                                service_info[port] = {
                                    'name': service_name,
                                    'version': service_version,
                                    'product': '',
                                    'extrainfo': ''
                                }
                                
                                logger.info(f"Сервис на порту {port}: {service_name} {service_version}")
                        except (ValueError, IndexError) as e:
                            logger.debug(f"Ошибка парсинга строки порта: {e}")
                            continue
        
        self.open_ports = open_ports
        self.service_info = service_info
        
        logger.info(f"Nmap нашел {len(open_ports)} открытых портов: {open_ports}")
        return open_ports

class SimplePortScanner:
    def __init__(self, target_host, username=None, password=None, use_nmap=True, nmap_scan_type='fast'):
        self.target_host = target_host
        self.username = username
        self.password = password
        self.use_nmap = use_nmap
        self.nmap_scan_type = nmap_scan_type
        self.open_ports = []
        self.successful_connections = []
        self.service_info = {}
        self.nmap_scanner = NmapScanner(target_host) if use_nmap else None
        
    def scan_ports_fast(self, port_range=None):
        """Быстрое сканирование с использованием nmap"""
        if not self.use_nmap or not self.nmap_scanner:
            logger.warning("Nmap не доступен")
            return []
        
        logger.info(f"Запуск быстрого nmap сканирования на {self.target_host}")
        start_time = time.time()
        
        # Запуск nmap сканирования
        open_ports = self.nmap_scanner.run_nmap_scan(port_range, self.nmap_scan_type)
        
        scan_time = time.time() - start_time
        logger.info(f"Nmap сканирование завершено за {scan_time:.2f} секунд")
        
        self.open_ports = open_ports
        
        # Копируем информацию о сервисах из nmap_scanner
        if hasattr(self.nmap_scanner, 'service_info') and self.nmap_scanner.service_info:
            self.service_info = self.nmap_scanner.service_info.copy()
            logger.info("Обнаруженные сервисы:")
            for port in sorted(open_ports):
                if port in self.service_info:
                    service = self.service_info[port]
                    logger.info(f"  Порт {port}: {service['name']} {service['version']}")
                else:
                    logger.info(f"  Порт {port}: неизвестный сервис")
        
        # Дополнительная проверка для RDP портов
        logger.info("Проверка стандартных RDP портов...")
        rdp_ports = [3389, 3390, 3391]  # Стандартные RDP порты
        for port in rdp_ports:
            if port not in open_ports:
                logger.info(f"Проверяю RDP порт {port}...")
                if self.connect_rdp(port):
                    logger.info(f"✓ Найден RDP на порту {port}")
                    open_ports.append(port)
                    self.service_info[port] = {
                        'name': 'rdp',
                        'version': 'RDP',
                        'product': 'Microsoft Terminal Services',
                        'extrainfo': ''
                    }
        
        return self.open_ports
    
    def connect_ssh(self, port):
        """Подключение по SSH"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Отключаем все методы аутентификации кроме пароля
            ssh.connect(
                self.target_host, 
                port=port, 
                username=self.username, 
                password=self.password,
                timeout=10,
                allow_agent=False,      # Отключаем SSH агент
                look_for_keys=False,    # Не ищем ключи
                gss_auth=False,         # Отключаем GSSAPI
                gss_kex=False,          # Отключаем GSSAPI KEX
                banner_timeout=5,       # Таймаут для баннера
                auth_timeout=10         # Таймаут для аутентификации
            )
            ssh.close()
            return True
        except paramiko.AuthenticationException as e:
            logger.debug(f"SSH аутентификация не удалась на порту {port}: {e}")
            return False
        except paramiko.SSHException as e:
            logger.debug(f"SSH ошибка на порту {port}: {e}")
            return False
        except Exception as e:
            logger.debug(f"SSH подключение к порту {port} не удалось: {e}")
            return False
    
    def connect_http(self, port):
        """Проверка HTTP/HTTPS"""
        try:
            protocol = 'https' if port == 443 else 'http'
            url = f"{protocol}://{self.target_host}:{port}"
            
            # Попытка базовой аутентификации
            response = requests.get(url, auth=(self.username, self.password), timeout=10)
            if response.status_code == 200:
                return True
        except Exception as e:
            logger.debug(f"HTTP подключение к порту {port} не удалось: {e}")
        return False
    
    def connect_ftp(self, port):
        """Подключение по FTP"""
        try:
            import ftplib
            ftp = ftplib.FTP()
            ftp.connect(self.target_host, port, timeout=10)
            ftp.login(self.username, self.password)
            ftp.quit()
            return True
        except Exception as e:
            logger.debug(f"FTP подключение к порту {port} не удалось: {e}")
            return False
    
    def connect_telnet(self, port):
        """Подключение по Telnet"""
        try:
            import telnetlib
            tn = telnetlib.Telnet(self.target_host, port, timeout=10)
            tn.read_until(b"login: ", timeout=5)
            tn.write(self.username.encode('ascii') + b"\n")
            tn.read_until(b"Password: ", timeout=5)
            tn.write(self.password.encode('ascii') + b"\n")
            tn.read_some()
            tn.close()
            return True
        except Exception as e:
            logger.debug(f"Telnet подключение к порту {port} не удалось: {e}")
            return False
    
    def connect_smtp(self, port):
        """Подключение к SMTP"""
        try:
            import smtplib
            server = smtplib.SMTP(self.target_host, port, timeout=10)
            server.starttls()
            server.login(self.username, self.password)
            server.quit()
            return True
        except Exception as e:
            logger.debug(f"SMTP подключение к порту {port} не удалось: {e}")
            return False
    
    def connect_imap(self, port):
        """Подключение к IMAP"""
        try:
            import imaplib
            mail = imaplib.IMAP4_SSL(self.target_host, port)
            mail.login(self.username, self.password)
            mail.logout()
            return True
        except Exception as e:
            logger.debug(f"IMAP подключение к порту {port} не удалось: {e}")
            return False
    
    def connect_pop3(self, port):
        """Подключение к POP3"""
        try:
            import poplib
            server = poplib.POP3_SSL(self.target_host, port)
            server.user(self.username)
            server.pass_(self.password)
            server.quit()
            return True
        except Exception as e:
            logger.debug(f"POP3 подключение к порту {port} не удалось: {e}")
            return False
    
    def connect_mysql(self, port):
        """Подключение к MySQL"""
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=self.target_host,
                port=port,
                user=self.username,
                password=self.password,
                connection_timeout=5
            )
            conn.close()
            return True
        except Exception as e:
            logger.debug(f"MySQL подключение к порту {port} не удалось: {e}")
            return False
    
    def connect_postgresql(self, port):
        """Подключение к PostgreSQL"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.target_host,
                port=port,
                user=self.username,
                password=self.password,
                connect_timeout=5
            )
            conn.close()
            return True
        except Exception as e:
            logger.debug(f"PostgreSQL подключение к порту {port} не удалось: {e}")
            return False
    
    def connect_redis(self, port):
        """Подключение к Redis"""
        try:
            import redis
            r = redis.Redis(host=self.target_host, port=port, password=self.password, socket_timeout=5)
            r.ping()
            return True
        except Exception as e:
            logger.debug(f"Redis подключение к порту {port} не удалось: {e}")
            return False
    
    def connect_mongodb(self, port):
        """Подключение к MongoDB"""
        try:
            import pymongo
            client = pymongo.MongoClient(
                f"mongodb://{self.username}:{self.password}@{self.target_host}:{port}/",
                serverSelectionTimeoutMS=5000
            )
            client.server_info()
            client.close()
            return True
        except Exception as e:
            logger.debug(f"MongoDB подключение к порту {port} не удалось: {e}")
            return False
    
    def connect_rdp(self, port):
        """Подключение к RDP (Remote Desktop Protocol)"""
        try:
            import socket
            
            # RDP использует TCP
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)  # Увеличиваем таймаут
            
            # Пытаемся подключиться
            result = sock.connect_ex((self.target_host, port))
            
            if result == 0:
                logger.info(f"TCP подключение к порту {port} успешно")
                try:
                    # Отправляем RDP connection request
                    rdp_request = b'\x03\x00\x00\x13\x0e\xe0\x00\x00\x00\x00\x00\x01\x00\x08\x00\x03\x00\x00\x00'
                    sock.send(rdp_request)
                    
                    # Читаем ответ
                    response = sock.recv(1024)
                    
                    # Проверяем, что это RDP ответ
                    if len(response) > 0 and response[0] == 0x03:
                        logger.info(f"Получен RDP ответ на порту {port}")
                        sock.close()
                        return True
                    else:
                        # Даже если нет RDP ответа, но порт открыт - возможно это RDP
                        logger.info(f"Порт {port} открыт, возможно RDP сервис")
                        sock.close()
                        return True
                        
                except Exception as e:
                    logger.debug(f"Ошибка при проверке RDP на порту {port}: {e}")
                    # Даже если ошибка, но порт открыт - возможно это RDP
                    sock.close()
                    return True
            else:
                sock.close()
                return False
                
        except Exception as e:
            logger.debug(f"RDP подключение к порту {port} не удалось: {e}")
            return False
    
    def connect_vnc(self, port):
        """Подключение к VNC (Virtual Network Computing)"""
        try:
            import socket
            
            # VNC использует TCP
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            
            # Пытаемся подключиться
            result = sock.connect_ex((self.target_host, port))
            
            if result == 0:
                try:
                    # Читаем VNC banner
                    banner = sock.recv(1024)
                    
                    # VNC серверы обычно отправляют версию в формате "RFB x.x.x"
                    if b'RFB' in banner:
                        sock.close()
                        return True
                    # Или просто проверяем, что порт отвечает
                    sock.close()
                    return True
                    
                except Exception:
                    sock.close()
                    return True
            else:
                sock.close()
                return False
                
        except Exception as e:
            logger.debug(f"VNC подключение к порту {port} не удалось: {e}")
            return False
    
    def attempt_connection(self, port):
        """Пытается подключиться к порту различными способами"""
        logger.info(f"Попытка подключения к порту {port}")
        
        # Получаем информацию о сервисе от nmap
        service_info = self.service_info.get(port, {})
        service_name = service_info.get('name', 'unknown').lower()
        
        logger.info(f"Сервис определен nmap как: {service_name}")
        
        # Подключаемся только к тому сервису, который определил nmap
        if 'rdp' in service_name or 'ms-wbt-server' in service_name or service_name == 'rdp':
            # RDP сервис
            logger.info(f"Пытаюсь подключиться к RDP на порту {port}")
            try:
                if self.connect_rdp(port):
                    self.successful_connections.append((port, "RDP"))
                    logger.info(f"✓ Успешное подключение к RDP на порту {port}")
                    return True
            except Exception as e:
                logger.debug(f"Ошибка подключения к RDP на порту {port}: {e}")
            return False
            
        elif 'vnc' in service_name or service_name == 'vnc':
            # VNC сервис
            logger.info(f"Пытаюсь подключиться к VNC на порту {port}")
            try:
                if self.connect_vnc(port):
                    self.successful_connections.append((port, "VNC"))
                    logger.info(f"✓ Успешное подключение к VNC на порту {port}")
                    return True
            except Exception as e:
                logger.debug(f"Ошибка подключения к VNC на порту {port}: {e}")
            return False
            
        elif 'ssh' in service_name or service_name == 'ssh':
            # SSH сервис
            logger.info(f"Пытаюсь подключиться к SSH на порту {port}")
            try:
                if self.connect_ssh(port):
                    self.successful_connections.append((port, "SSH"))
                    logger.info(f"✓ Успешное подключение к SSH на порту {port}")
                    return True
            except Exception as e:
                logger.debug(f"Ошибка подключения к SSH на порту {port}: {e}")
            return False
            
        elif 'telnet' in service_name or service_name == 'telnet':
            # Telnet сервис
            logger.info(f"Пытаюсь подключиться к Telnet на порту {port}")
            try:
                if self.connect_telnet(port):
                    self.successful_connections.append((port, "Telnet"))
                    logger.info(f"✓ Успешное подключение к Telnet на порту {port}")
                    return True
            except Exception as e:
                logger.debug(f"Ошибка подключения к Telnet на порту {port}: {e}")
            return False
            
        elif 'http' in service_name or service_name == 'http':
            # HTTP сервис
            logger.info(f"Пытаюсь подключиться к HTTP на порту {port}")
            try:
                if self.connect_http(port):
                    self.successful_connections.append((port, "HTTP"))
                    logger.info(f"✓ Успешное подключение к HTTP на порту {port}")
                    return True
            except Exception as e:
                logger.debug(f"Ошибка подключения к HTTP на порту {port}: {e}")
            return False
            
        elif 'https' in service_name or service_name == 'https':
            # HTTPS сервис
            logger.info(f"Пытаюсь подключиться к HTTPS на порту {port}")
            try:
                if self.connect_http(port):
                    self.successful_connections.append((port, "HTTPS"))
                    logger.info(f"✓ Успешное подключение к HTTPS на порту {port}")
                    return True
            except Exception as e:
                logger.debug(f"Ошибка подключения к HTTPS на порту {port}: {e}")
            return False
            
        elif 'ftp' in service_name or service_name == 'ftp':
            # FTP сервис
            logger.info(f"Пытаюсь подключиться к FTP на порту {port}")
            try:
                if self.connect_ftp(port):
                    self.successful_connections.append((port, "FTP"))
                    logger.info(f"✓ Успешное подключение к FTP на порту {port}")
                    return True
            except Exception as e:
                logger.debug(f"Ошибка подключения к FTP на порту {port}: {e}")
            return False
        
        # Если nmap не определил конкретный сервис, пробуем общие методы
        logger.info(f"Сервис не определен nmap, пробуем общие методы для порта {port}")
        
        # Пробуем HTTP (работает на многих портах)
        try:
            if self.connect_http(port):
                self.successful_connections.append((port, "HTTP/HTTPS"))
                logger.info(f"✓ Успешное HTTP подключение к порту {port}")
                return True
        except Exception as e:
            logger.debug(f"HTTP подключение к порту {port} не удалось: {e}")
        
        # Пробуем SSH (может работать на нестандартных портах)
        try:
            if self.connect_ssh(port):
                self.successful_connections.append((port, "SSH"))
                logger.info(f"✓ Успешное SSH подключение к порту {port}")
                return True
        except Exception as e:
            logger.debug(f"SSH подключение к порту {port} не удалось: {e}")
        
        # Пробуем FTP
        try:
            if self.connect_ftp(port):
                self.successful_connections.append((port, "FTP"))
                logger.info(f"✓ Успешное FTP подключение к порту {port}")
                return True
        except Exception as e:
            logger.debug(f"FTP подключение к порту {port} не удалось: {e}")
        
        logger.info(f"✗ Не удалось подключиться к порту {port}")
        return False
    
    def connect_to_ports(self):
        """Подключается ко всем найденным портам"""
        if not self.open_ports:
            logger.warning("Нет открытых портов для подключения")
            return
        
        logger.info(f"Начинаю попытки подключения к {len(self.open_ports)} портам")
        
        for port in self.open_ports:
            logger.info(f"Попытка подключения к порту {port}")
            success = self.attempt_connection(port)
            if success:
                logger.info(f"✅ Успешное подключение к порту {port}")
            else:
                logger.info(f"❌ Не удалось подключиться к порту {port}")
            time.sleep(0.5)  # Небольшая задержка между попытками
        
        logger.info(f"Успешных подключений: {len(self.successful_connections)}")
        if self.successful_connections:
            logger.info("Успешные подключения:")
            for port, service in self.successful_connections:
                logger.info(f"  ✅ Порт {port}: {service}")
        else:
            logger.warning("Успешных подключений не найдено")

def main():
    parser = argparse.ArgumentParser(description='Упрощенный сканер портов с nmap')
    parser.add_argument('target', help='Целевой хост для сканирования')
    parser.add_argument('-u', '--username', help='Имя пользователя для подключения')
    parser.add_argument('-p', '--password', help='Пароль для подключения')
    parser.add_argument('--port-range', default='1-1000', help='Диапазон портов для сканирования (по умолчанию: 1-1000)')
    parser.add_argument('--nmap-scan-type', choices=['fast', 'stealth', 'aggressive'], default='fast', 
                       help='Тип nmap сканирования (по умолчанию: fast)')
    parser.add_argument('--nmap-args', nargs='*', default=[], help='Дополнительные аргументы для nmap (например: --nmap-args -sT -sV)')
    
    args = parser.parse_args()
    
    # Парсинг диапазона портов
    if '-' in args.port_range:
        start_port, end_port = map(int, args.port_range.split('-'))
        port_range = (start_port, end_port)
    else:
        start_port = end_port = int(args.port_range)
        port_range = (start_port, end_port)
    
    # Получение учетных данных
    username = args.username
    password = args.password
    
    if not username:
        username = input("Введите имя пользователя: ")
    
    if not password:
        password = getpass.getpass("Введите пароль: ")
    
    # Создание сканера
    scanner = SimplePortScanner(
        args.target, 
        username, 
        password, 
        use_nmap=True,
        nmap_scan_type=args.nmap_scan_type
    )
    
    # Настройка дополнительных аргументов nmap
    if args.nmap_args:
        scanner.nmap_scanner.nmap_args = args.nmap_args
    
    try:
        # Сканирование портов
        logger.info("Используется быстрое nmap сканирование")
        open_ports = scanner.scan_ports_fast(port_range)
        
        if open_ports:
            print(f"\nНайдено {len(open_ports)} открытых портов:")
            for port in sorted(open_ports):
                print(f"  - Порт {port}")
            
            # Попытки подключения
            print(f"\nПытаюсь подключиться к найденным портам...")
            scanner.connect_to_ports()
            
            if scanner.successful_connections:
                print(f"\n✓ Успешные подключения:")
                for port, service in scanner.successful_connections:
                    print(f"  - Порт {port}: {service}")
            else:
                print("\n✗ Не удалось подключиться ни к одному порту")
        else:
            print("Открытые порты не найдены")
            
    except KeyboardInterrupt:
        print("\nСканирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
