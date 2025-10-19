from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# === Главное меню (reply-клавиатура) ===
# Оставляем все основные пункты и приводим тексты к тем, что ловят хендлеры:
# - 🧾 Поставить защиту  -> старт постановки
# - 📂 Мои защиты        -> только активные/extended/changed (см. protection_view.py)
# - 🌍 Все защиты        -> общий список (см. protection_view.py)
# - ⚙️ Админ-панель       -> открывает инлайн-админку
# - 🔍 Найти по партнёру  -> поиск по партнёру (новое название)
# - 📦 Архив             -> success/closed
#
# Дополнительно оставляем кнопку "🔍 Найти по клиенту" на случай если где-то ещё используется
# (ни на что не влияет — просто дублирует ввод в поиск по партнёру).
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🧾 Поставить защиту"),
            KeyboardButton(text="📂 Мои защиты"),
        ],
        [
            KeyboardButton(text="🌍 Все защиты"),
            KeyboardButton(text="⚙️ Админ-панель"),
        ],
        [
            KeyboardButton(text="🔍 Найти по партнёру"),
            KeyboardButton(text="📦 Архив"),
        ],
        # Если нужно оставить как синоним — раскомментируй:
        # [KeyboardButton(text="🔍 Найти по клиенту")]
    ],
    resize_keyboard=True
)

# === Инлайн-меню Админ-панели ===
# Составлено в соответствии со скринами: "Менеджеры", "Партнёры по менеджеру",
# "Отчёт по защитам", "Статистика менеджеров", "Архив", "Найти по партнёру".
# Callbacks оставлены короткими и нейтральными — подключай их в handlers/admin_panel.py.
def admin_panel_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📋 Менеджеры", callback_data="admin:managers")],
        [InlineKeyboardButton(text="🏢 Партнёры по менеджеру", callback_data="admin:partners_by_manager")],
        [InlineKeyboardButton(text="📈 Отчёт по защитам", callback_data="admin:report")],
        [InlineKeyboardButton(text="📊 Статистика менеджеров", callback_data="admin:stats")],
        [InlineKeyboardButton(text="📦 Архив", callback_data="admin:archive")],
        [InlineKeyboardButton(text="🔍 Найти по партнёру", callback_data="admin:find_partner")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

# === Подтверждение/назад (универсальная) ===
def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm:ok"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="confirm:back"),
        ]
    ])
