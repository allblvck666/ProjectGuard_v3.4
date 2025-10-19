from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from utils.db import Database
from datetime import datetime

router = Router()
db = Database()


# ====== ВСПОМОГАТЕЛЬНЫЕ КНОПКИ ======

def protection_actions(pid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 Открыть карточку", callback_data=f"open_{pid}")
        ],
        [
            InlineKeyboardButton(text="🔁 Продлить", callback_data=f"extend_{pid}"),
            InlineKeyboardButton(text="✅ Успешная защита", callback_data=f"success_{pid}")
        ],
        [
            InlineKeyboardButton(text="❌ Снять", callback_data=f"remove_{pid}")
        ]
    ])


def back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])


# ====== ВЫВОД АКТИВНЫХ И АРХИВНЫХ ЗАЩИТ ======

@router.callback_query(F.data == "my_protections")
async def show_my_protections(call: CallbackQuery):
    user_name = call.from_user.full_name
    protections = db.fetchall(
        "SELECT * FROM protections WHERE manager=? AND status IN ('active','extended','changed') ORDER BY created_at DESC",
        (user_name,)
    )
    if not protections:
        await call.message.answer("❌ У вас пока нет активных защит.")
        return

    msg = "📂 Ваши защиты:\n\n"
    for p in protections:
        msg += f"🏢 {p['dealer']} | {p['articles']} | {p['quantity']} м² | {p['status']}\n"
    await call.message.answer(msg)


@router.callback_query(F.data == "archive_protections")
async def show_archive(call: CallbackQuery):
    protections = db.fetchall(
        "SELECT * FROM protections WHERE status IN ('closed','success') ORDER BY updated_at DESC"
    )
    if not protections:
        await call.message.answer("📦 Архив пуст.")
        return

    msg = "📦 Архив завершённых защит:\n\n"
    for p in protections:
        msg += f"{p['dealer']} | {p['articles']} | {p['quantity']} м² | {p['status']}\n"
    await call.message.answer(msg)


# ====== ВСЕ ЗАЩИТЫ И ПРОСМОТР КОЛЛЕГ ======

@router.callback_query(F.data == "all_protections")
async def show_all_protections(call: CallbackQuery):
    protections = db.fetchall("SELECT * FROM protections ORDER BY created_at DESC")
    if not protections:
        await call.message.answer("📭 Пока нет защит в базе.")
        return

    msg = "🌍 Все защиты (по менеджерам):\n\n"
    for p in protections:
        msg += f"👤 {p['manager']} | {p['dealer']} | {p['articles']} | {p['quantity']} м² | {p['status']}\n"
    await call.message.answer(msg)


# ====== НАЙТИ ПО ПАРТНЁРУ ======

@router.callback_query(F.data == "search_partner")
async def search_partner_start(call: CallbackQuery):
    managers = db.fetchall("SELECT DISTINCT dealer FROM protections")
    if not managers:
        await call.message.answer("❌ Нет партнёров с защитами.")
        return

    kb = []
    row = []
    for i, m in enumerate(managers, 1):
        row.append(InlineKeyboardButton(text=m["dealer"], callback_data=f"partner_{m['dealer']}"))
        if i % 2 == 0:
            kb.append(row)
            row = []
    if row:
        kb.append(row)

    await call.message.answer("📋 Ваши партнёры (нажимайте):", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))


@router.callback_query(F.data.startswith("partner_"))
async def show_partner_protections(call: CallbackQuery):
    dealer = call.data.replace("partner_", "")
    protections = db.fetchall("SELECT * FROM protections WHERE dealer=?", (dealer,))
    if not protections:
        await call.message.answer("❌ Защиты для этого партнёра не найдены.")
        return

    msg = f"📦 Защиты по партнёру: {dealer}\n\n"
    for p in protections:
        msg += f"{p['dealer']} | {p['articles']} | {p['quantity']} м² | {p['status']}\n"
    await call.message.answer(msg)


# ====== ПРОСМОТР ПОЛНОЙ КАРТОЧКИ ======

@router.callback_query(F.data.startswith("open_"))
async def open_protection(call: CallbackQuery):
    pid = call.data.replace("open_", "")
    p = db.fetchone("SELECT * FROM protections WHERE id=?", (pid,))
    if not p:
        await call.message.answer("❌ Защита не найдена.")
        return

    text = (
        f"👍 Защита #{p['id']}\n\n"
        f"👤 Ответственный менеджер: {p['manager']}\n"
        f"🏢 Партнёр: {p['dealer']}\n"
        f"📍 Город Партнёра: {p['dealer_city']}\n\n"
        f"❗️Артикул(ы): {p['articles']}\n"
        f"📦 Метраж защиты: {p['quantity']} м²\n\n"
        f"📅 Создано: {p['created_at']}\n"
        f"⌛ Истекает: {p['ends']}\n"
        f"📊 Статус: {p['status']}\n"
        f"👨‍💼 Менеджер: {p['manager']}\n"
    )

    await call.message.answer(text, reply_markup=protection_actions(pid))


# ====== УСПЕШНАЯ ЗАЩИТА ======

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

class SuccessProtection(StatesGroup):
    waiting_number = State()


@router.callback_query(F.data.startswith("success_"))
async def success_protection(call: CallbackQuery, state: FSMContext):
    pid = call.data.replace("success_", "")
    await state.update_data(pid=pid)
    await call.message.answer(f"Введите номер заказа из 1С для защиты #{pid}:")
    await state.set_state(SuccessProtection.waiting_number)


@router.message(SuccessProtection.waiting_number)
async def success_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["pid"]
    order_number = message.text.strip()

    db.query(
        "UPDATE protections SET status='success', order_number=?, updated_at=? WHERE id=?",
        (order_number, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pid)
    )

    await message.answer(f"✅ Защита #{pid} помечена как успешная (№ {order_number}).")
    await state.clear()


# ====== ПРОДЛЕНИЕ И СНЯТИЕ ======

@router.callback_query(F.data.startswith("extend_"))
async def extend_protection(call: CallbackQuery):
    pid = call.data.replace("extend_", "")
    protection = db.fetchone("SELECT * FROM protections WHERE id=?", (pid,))
    if not protection:
        await call.message.answer("❌ Защита не найдена.")
        return

    new_date = (datetime.strptime(protection["ends"], "%Y-%m-%d") + timedelta(days=5)).strftime("%Y-%m-%d")
    db.query(
        "UPDATE protections SET ends=?, status='extended', updated_at=? WHERE id=?",
        (new_date, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pid)
    )

    await call.message.answer(f"🔁 Защита #{pid} продлена до {new_date}.")


@router.callback_query(F.data.startswith("remove_"))
async def remove_protection(call: CallbackQuery):
    pid = call.data.replace("remove_", "")
    db.query(
        "UPDATE protections SET status='closed', updated_at=? WHERE id=?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pid)
    )
    await call.message.answer(f"❌ Защита #{pid} снята и перенесена в архив.")
