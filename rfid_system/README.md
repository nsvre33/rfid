# RFID Система учёта меток

Production-ready система для считывания RFID-карт через Arduino Uno + RC522 с десктопным UI (PyQt6) и веб-дашбордом (FastAPI).

## 📁 Структура проекта

```
rfid_system/
├── main.py                     # Точка входа
├── config.json                 # Настройки системы
├── requirements.txt            # Зависимости Python
├── backend/
│   ├── __init__.py
│   ├── config.py               # Загрузчик конфигурации
│   ├── event_broker.py         # Потокобезопасная шина событий
│   ├── serial_handler.py       # Обработка COM-порта (QThread)
│   └── data_manager.py         # Работа с Excel и фото
├── ui/
│   ├── __init__.py
│   └── main_window.py          # PyQt6 интерфейс
├── web/
│   ├── __init__.py
│   ├── app.py                  # FastAPI сервер
│   └── static/
│       └── index.html          # Веб-дашборд
├── assets/                     # Звуковые файлы (ok.wav, err.wav)
└── data/
    ├── registry.xlsx           # База карт
    ├── logs/                   # Ежедневные логи
    └── photos/                 # Фото сотрудников
```

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
cd rfid_system
pip install -r requirements.txt
```

### 2. Запуск приложения

**С консолью (для отладки):**
```bash
python main.py
```

**Без консоли (фоновый режим, Windows):**
```bash
pythonw main.py
```

### 3. Доступ к веб-дашборду

Откройте в браузере: **http://localhost:8000**

Дашборд автоматически обновляется каждые 3 секунды.

## 🔧 Настройка

### config.json

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `serial.baudrate` | Скорость COM-порта | 9600 |
| `serial.timeout` | Таймаут чтения (сек) | 1.0 |
| `serial.port_keywords` | Ключевые слова для поиска порта | arduino, ch340, ... |
| `paths.registry` | Путь к файлу реестра | data/registry.xlsx |
| `paths.logs_dir` | Папка логов | data/logs |
| `paths.photos_dir` | Папка фото | data/photos |
| `ui.max_log_rows` | Макс. строк в таблице UI | 150 |
| `web.host` | Хост веб-сервера | 0.0.0.0 |
| `web.port` | Порт веб-сервера | 8000 |
| `sounds.enable` | Включить звуки | true |
| `sounds.ok` | Файл звука успеха | assets/ok.wav |
| `sounds.err` | Файл звука ошибки | assets/err.wav |

## 📡 Формат данных от Arduino

Arduino должен отправлять строки формата:
```
RFID:1A2B3C4D
```

Где `1A2B3C4D` — HEX UID карты (регистр не важен, приводится к upper-case).

### Пример скетча для Arduino Uno + RC522:

```cpp
#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9

MFRC522 mfrc522(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();
}

void loop() {
  if (!mfrc522.PICC_IsNewCardPresent()) return;
  if (!mfrc522.PICC_ReadCardSerial()) return;
  
  String uid = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    uid += String(mfrc522.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();
  
  Serial.println("RFID:" + uid);
  delay(500); // Debounce
}
```

## 🪟 Автозапуск при старте ОС

### Windows

**Способ 1: Планировщик заданий**
1. Откройте `taskschd.msc`
2. Создайте задачу → Триггер: "При входе в систему"
3. Действие: `pythonw.exe` с аргументом `C:\path\to\rfid_system\main.py`
4. Опции: "Запускать без пользователя", "Высший уровень прав"

**Способ 2: Ярлык в автозагрузке**
1. Создайте ярлык: `pythonw.exe C:\path\to\rfid_system\main.py`
2. Поместите в `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`

### Linux

**Systemd сервис:**

```ini
# /etc/systemd/system/rfid-system.service
[Unit]
Description=RFID Access Control System
After=graphical.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/home/your_user/rfid_system
ExecStart=/usr/bin/python3 /home/your_user/rfid_system/main.py
Restart=on-failure

[Install]
WantedBy=graphical.target
```

```bash
sudo systemctl enable rfid-system.service
sudo systemctl start rfid-system.service
```

## 🔍 Диагностика

### Проверка COM-порта

```python
from serial.tools.list_ports import comports
for p in comports():
    print(f"{p.device}: {p.description}")
```

### Просмотр логов

Логи сканирований сохраняются в `data/logs/YYYY-MM-DD.xlsx`

### API эндпоинты

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/` | Веб-дашборд |
| GET | `/api/stats` | Статистика сканирований |
| GET | `/api/scans?limit=50` | Последние сканы |
| GET | `/api/registry` | Все записи реестра |

## ⚠️ Обработка ошибок

### Excel файл заблокирован
Если `registry.xlsx` или лог открыт в Excel вручную — система пропускает запись, но продолжает работу. Закройте файл для записи.

### USB отключён
UI показывает статус "🔍 Поиск порта..." и автоматически переподключается каждые 3 секунды.

### Неизвестный UID
- Статус: `❌ Неизвестная карта`
- Звук ошибки (если включено)
- Запись в лог
- Можно добавить через форму UI

## 🎯 Критерии приёмки

✅ Arduino шлёт `RFID:1A2B3C4D` → UI показывает ФИО + фото, пишет в лог, Web обновляется  
✅ Отключение USB → автоподключение при возврате  
✅ Открыт `registry.xlsx` в Excel → запись пропускается, система не падает  
✅ Неизвестный UID → статус `❌`, звук ошибки, запись в лог  
✅ Запуск `pythonw main.py` → без консоли, веб-дашборд на `http://localhost:8000`  
✅ Все потоки завершаются корректно при закрытии окна  

## 📄 Лицензия

MIT License
