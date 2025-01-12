# Фрагментация HTML
## Касымхан Болат

## Обзор проекта
Проект состоит из трёх основных компонентов:
- `msg_split.py` - модуль с функцией разделения HTML
- `split_msg_script.py` - скрипт командной строки
- `app.py` - Flask-приложение с API lля 

## Установка

### Клонирование репозитория
```bash
git clone https://github.com/ваш_пользователь/ваш_репозиторий.git
cd ваш_репозиторий
```

### Создание виртуального окружения для локального запуска скрипта
```bash
python -m venv venv

# Linux/MacOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### Установка зависимостей

Установите пакеты:
```bash
pip install -r requirements.txt
```

## Использование

### Командный скрипт
```bash
python split_msg_script.py --max-len=300 source.html
```

### Flask-приложение
Запуск сервера:
```bash
python app.py
```

API будет доступно по адресу: `http://0.0.0.0:8002/api/split`

Также, Flask API доступен на деплоееном сервере railway.com

#### Пример API-запроса
```bash
curl -X POST -F "file=@source.html" -F "max_len=300" http://localhost:8002/api/split
```

#### Формат ответа
```json
{
  "fragments": [
    {
      "filename": "fragment_1.html",
      "content": "HTML-контент...",
      "raw_length": 300
    }
  ],
  "totalCharacters": 500
}
```