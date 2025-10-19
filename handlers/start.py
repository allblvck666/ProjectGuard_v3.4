from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.common import main_menu, admin_panel_kb

# Импортируем из постановки защиты, чтобы уметь запустить сценарий сразу из кнопки:
# - клавиатуру выбора менеджера
# - состояние AddProtection.manager, чтобы корректно продолжить FSM
from handlers.protection_add import manager_keyboard, AddProtection

router = Router()

# /start — приветствие и показ главного меню
@router.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer("Привет, 😉!\nВы вошли в систему ProjectGuard.", reply_markup=main_menu)

# ===== Маршруты главного меню (reply-кнопки) =====
# Эти хендлеры связаны с уже существующими обработчиками в других модулях.
# Мы не дублируем логику — только стартуем сценарии там, где нужно.

# 🧾 Поставить защиту — сразу показываем выбор менеджера и переводим FSM на AddProtection.manager
@router.message(F.text == "🧾 Поставить защиту")
async def start_add_protection(message: Message, state: FSMContext):
    await message.answer("👤 Выберите менеджера:", reply_markup=manager_keyboard())
    await state.set_state(AddProtection.manager)

# 📂 Мои защиты — полностью обрабатывается в handlers/protection_view.py
@router.message(F.text == "📂 Мои защиты")
async def my_protections_passthrough(message: Message):
    # Ничего не делаем: этот текст уже ловит protection_view.py (@router.message(F.text == "📂 Мои защиты"))
    # Дублируем сообщение, чтобы гарантированно сработал тот роутер
    pass

# 🌍 Все защиты — обрабатывается в handlers/protection_view.py
@router.message(F.text == "🌍 Все защиты")
async def all_protections_passthrough(message: Message):
    pass

# 🔍 Найти по партнёру — обрабатывается в handlers/protection_view.py
@router.message(F.text == "🔍 Найти по партнёру")
async def find_partner_passthrough(message: Message):
    pass

# 📦 Архив — обрабатывается в handlers/protection_view.py
@router.message(F.text == "📦 Архив")
async def archive_passthrough(message: Message):
    pass

# ⚙️ Админ-панель — отдаём инлайн-меню (callbacks обрабатываются в handlers/admin_panel.py)
@router.message(F.text == "⚙️ Админ-панель")
async def open_admin_panel(message: Message):
    await message.answer("⚙️ Админ-панель:", reply_markup=admin_panel_kb())

# На случай, если где-то осталось старое название «Найти по клиенту» — прозрачно переадресуем
@router.message(F.text == "🔍 Найти по клиенту")
async def alias_find_client_to_partner(message: Message):
    await message.answer("Переключаю на поиск по партнёру…")
    # Здесь protection_view.py уже слушает текст "🔍 Найти по партнёру"
    await message.answer("🔍 Найти по партнёру")
