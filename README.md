# DocGen — Веб-сервіс для автоматичної генерації документів

## Зміст
1. [Огляд проекту](#1-огляд-проекту)
2. [Архітектура системи](#2-архітектура-системи)
3. [Структура проекту](#3-структура-проекту)
4. [Встановлення та запуск](#4-встановлення-та-запуск)
5. [API документація](#5-api-документація)
6. [Шаблони документів](#6-шаблони-документів)
7. [Додавання нових шаблонів](#7-додавання-нових-шаблонів)
8. [Розширення та розгортання](#8-розширення-та-розгортання)

---

## 1. Огляд проекту

**DocGen** — веб-сервіс, що дозволяє генерувати стандартизовані ділові документи у форматах **PDF** та **DOCX** через зручний браузерний інтерфейс або REST API.

### Підтримувані типи документів

| Тип | Ідентифікатор | Призначення |
|-----|--------------|-------------|
| Договір надання послуг | `contract` | Двосторонній договір між виконавцем та замовником |
| Акт виконаних робіт | `act` | Підтвердження факту надання послуг із переліком і вартістю |
| GDPR-запит | `gdpr` | Запит на реалізацію прав суб'єкта персональних даних |

### Технічний стек

| Шар | Технологія |
|-----|-----------|
| Веб-фреймворк | **Flask** 3.x |
| Генерація PDF | **ReportLab** 4.x |
| Генерація DOCX | **python-docx** 1.x |
| Фронтенд | Vanilla HTML/CSS/JS (без фреймворків) |
| Шрифти PDF | Helvetica (вбудовані в ReportLab) |

---

## 2. Архітектура системи

```
┌─────────────────────────────────────────────────┐
│                   БРАУЗЕР                        │
│  ┌───────────────────────────────────────────┐  │
│  │  index.html  –  форма вводу + JS-логіка   │  │
│  │  • switchTab()  • collectFields()          │  │
│  │  • generate()   • showNotif()              │  │
│  └──────────────┬────────────────────────────┘  │
└─────────────────┼───────────────────────────────┘
                  │  POST /api/generate (JSON)
                  ▼
┌─────────────────────────────────────────────────┐
│              FLASK БЕКЕНД (app.py)               │
│                                                  │
│  Route: /           → render index.html          │
│  Route: /api/generate → обробка запиту           │
│       │                                          │
│       ├─► get_contract_data(fields)  ─────────┐  │
│       ├─► get_act_data(fields)       ─────────┤  │
│       └─► get_gdpr_data(fields)      ─────────┤  │
│                                               │  │
│       ┌───────────────────────────────────────┘  │
│       │  doc_data (dict з секціями)               │
│       │                                           │
│       ├─► generate_pdf(doc_data)  → bytes        │
│       └─► generate_docx(doc_data) → bytes        │
│                                                  │
│  Відповідь: send_file(bytes, as_attachment=True) │
└─────────────────────────────────────────────────┘
```

### Потік даних

1. Користувач заповнює форму в браузері
2. JavaScript збирає поля через `collectFields(prefix)` та надсилає `POST /api/generate`
3. Flask отримує JSON: `{ doc_type, format, fields }`
4. Відповідна функція-білдер (`get_*_data`) перетворює поля на структуру `doc_data`
5. Генератор (ReportLab або python-docx) рендерить документ у байти
6. `send_file()` повертає файл браузеру — починається автоматичне завантаження

---

## 3. Структура проекту

```
docgen/
├── app.py                  # Головний файл — Flask-застосунок
├── requirements.txt        # Python-залежності
├── templates/
│   └── index.html          # Єдиний HTML-шаблон (SPA-підхід)
├── generated_docs/         # Автоматично генерується; зберігає файли
└── README.md               # Ця документація
```

---

## 4. Встановлення та запуск

### Вимоги

- Python 3.10+
- pip

### Кроки

```bash
# 1. Клонуйте / розпакуйте проект
cd docgen

# 2. (Рекомендовано) Створіть та активуйте ввіртуальне середовище
python -m venv venv
source venv/bin/activate        # Linux/macOS
# або:
venv\Scripts\activate           # Windows

# 3. Встановіть залежності
pip install -r requirements.txt

# 4. Запустіть сервер
python app.py
```

Відкрийте браузер: **http://localhost:5000**

### Продакшн-запуск (Gunicorn)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

---

## 5. API документація

### `POST /api/generate`

Генерує документ і повертає файл для завантаження.

**Заголовки запиту:**
```
Content-Type: application/json
```

**Тіло запиту:**
```json
{
  "doc_type": "contract",
  "format":   "pdf",
  "fields": {
    "doc_number":          "2024-001",
    "date":                "2024-12-01",
    "city":                "Київ",
    "provider_name":       "ТОВ «Виконавець»",
    "provider_code":       "12345678",
    "provider_address":    "м. Київ, вул. Хрещатик, 1",
    "client_name":         "ТОВ «Замовник»",
    "client_code":         "87654321",
    "client_address":      "м. Львів, пр. Свободи, 5",
    "service_description": "Розробка веб-застосунку",
    "amount":              "50000",
    "payment_days":        "5",
    "deadline":            "2024-12-31"
  }
}
```

**Відповідь (200 OK):**
Бінарний файл із заголовком `Content-Disposition: attachment; filename="contract_2024-001.pdf"`.

**Коди помилок:**

| Код | Опис |
|-----|------|
| 400 | Невідомий `doc_type` або `format` |
| 500 | Внутрішня помилка генерації |

**Приклад запиту через curl:**
```bash
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"doc_type":"contract","format":"pdf","fields":{"provider_name":"ТОВ Тест","client_name":"ФОП Іваненко","amount":"10000","service_description":"Консалтинг"}}' \
  --output contract.pdf
```

---

## 6. Шаблони документів

### Структура `doc_data`

Кожна функція-білдер повертає словник такого формату:

```python
{
    "title":    str,              # Заголовок документа
    "subtitle": str | None,       # Підзаголовок (необов'язково)
    "number":   str,              # Номер документа
    "city":     str,              # Місто
    "date":     str,              # Дата (DD.MM.YYYY)
    "sections": [
        {
            "heading": str,       # Заголовок секції
            "body":    str,       # Текст (рядки розділені \n)
            # АБО:
            "table": {
                "headers": list[str],
                "rows":    list[list[str]],
                "total":   str,
            }
        },
        ...
    ]
}
```

Обидва генератори (`generate_pdf` і `generate_docx`) приймають саме цю структуру — тому шаблон визначається **один раз**, а рендеринг відбувається в обох форматах автоматично.

### Поля документів

#### Договір (`contract`)

| Поле | Обов'язкове | Опис |
|------|:-----------:|------|
| `doc_number` | ✓ | Номер договору |
| `date` | ✓ | Дата |
| `city` | | Місто |
| `provider_name` | ✓ | Виконавець |
| `provider_code` | | ЄДРПОУ/ІПН виконавця |
| `provider_address` | | Адреса виконавця |
| `client_name` | ✓ | Замовник |
| `client_code` | | ЄДРПОУ/ІПН замовника |
| `client_address` | | Адреса замовника |
| `service_description` | ✓ | Опис послуг |
| `amount` | ✓ | Сума договору (грн) |
| `payment_days` | | Строк оплати (дні) |
| `deadline` | | Дедлайн виконання |

#### Акт виконаних робіт (`act`)

| Поле | Обов'язкове | Опис |
|------|:-----------:|------|
| `doc_number` | ✓ | Номер акта |
| `date` | ✓ | Дата |
| `provider_name` | ✓ | Виконавець |
| `client_name` | ✓ | Замовник |
| `contract_number` | | Номер договору-підстави |
| `contract_date` | | Дата договору |
| `service_description` | ✓ | Найменування послуги |
| `unit` | | Одиниця виміру |
| `quantity` | | Кількість |
| `amount` | ✓ | Загальна сума (грн) |
| `amount_words` | | Сума прописом |

#### GDPR-запит (`gdpr`)

| Поле | Обов'язкове | Опис |
|------|:-----------:|------|
| `doc_number` | | Номер запиту |
| `date` | ✓ | Дата подачі |
| `client_name` | ✓ | ПІБ заявника |
| `birth_date` | | Дата народження |
| `email` | ✓ | Email заявника |
| `phone` | | Телефон |
| `provider_name` | ✓ | Назва організації |
| `provider_address` | | Адреса організації |
| `dpo_email` | | Email DPO |
| `request_type` | ✓ | Тип права |
| `request_details` | | Деталі запиту |

---

## 7. Додавання нових шаблонів

Щоб додати новий тип документа (наприклад, рахунок-фактуру), потрібно **3 кроки**:

### Крок 1 — Визначити білдер у `app.py`

```python
def get_invoice_data(fields: dict) -> dict:
    return {
        "title": "РАХУНОК-ФАКТУРА",
        "number": fields.get("doc_number", "001"),
        "city": fields.get("city", "Київ"),
        "date": fields.get("date", datetime.today().strftime("%d.%m.%Y")),
        "sections": [
            {
                "heading": "РЕКВІЗИТИ",
                "body": f"Постачальник: {fields.get('provider_name', '___')}\n"
                        f"Покупець: {fields.get('client_name', '___')}",
            },
            # ... інші секції
        ],
    }
```

### Крок 2 — Зареєструвати білдер

```python
DOCUMENT_BUILDERS = {
    "contract": get_contract_data,
    "act":      get_act_data,
    "gdpr":     get_gdpr_data,
    "invoice":  get_invoice_data,   # ← новий рядок
}
```

### Крок 3 — Додати вкладку і форму в `index.html`

Скопіюйте одну з існуючих вкладок (`<div class="doc-panel">`) та змініть:
- `id="panel-invoice"`
- Префікс полів на `i-`
- Виклик кнопки: `onclick="generate('invoice')"`

Генератори PDF і DOCX працюватимуть **автоматично** — без змін.

---

## 8. Розширення та розгортання

### Можливі покращення

| Функція | Реалізація |
|---------|-----------|
| Збереження документів в БД | SQLite / PostgreSQL + SQLAlchemy |
| Аутентифікація | Flask-Login або JWT |
| Нумерація документів | Лічильник у БД |
| Черга генерації | Celery + Redis |
| Хмарне сховище | AWS S3 / Google Cloud Storage |
| Кирилиця в PDF (TTF) | `pdfmetrics.registerFont(TTFont(...))` |
| Email-відправка | Flask-Mail |
| Кілька мов | Jinja2 шаблони + i18n |

### Docker (приклад)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```

```bash
docker build -t docgen .
docker run -p 8000:8000 docgen
```

---

*Документацію складено для DocGen v1.0*
