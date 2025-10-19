from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from utils.db import Database

router = Router()
db = Database()

# Список менеджеров
managers = [
    "Лена Ш",
    "Дмитрий Г",
    "Москва",
    "Дмитрий Ж",
    "Администратор"
]

# FSM состояния
class AddProtection(StatesGroup):
    manager = State()
    dealer = State()
    dealer_city = State()
    articles = State()
    quantity = State()
    client_name = State()
    phone_last4 = State()
    object_city = State()
    address = State()
    comment = State()

# Кнопка выбора менеджера
def manager_keyboard():
    kb = []
    row = []
    for i, m in enumerate(managers, 1):
        row.append(InlineKeyboardButton(text=m, callback_data=f"mgr_{m}"))
        if i % 2 == 0:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "add_protection")
async def start_protection(call: CallbackQuery, state: FSMContext):
    await call.message.answer("👤 Выберите менеджера:", reply_markup=manager_keyboard())
    await state.set_state(AddProtection.manager)

@router.callback_query(F.data.startswith("mgr_"))
async def set_manager(call: CallbackQuery, state: FSMContext):
    manager = call.data.replace("mgr_", "")
    await state.update_data(manager=manager)
    await call.message.answer(f"✅ Менеджер выбран: {manager}\nВведите дилера:")
    await state.set_state(AddProtection.dealer)

@router.message(AddProtection.dealer)
async def set_dealer(message: Message, state: FSMContext):
    await state.update_data(dealer=message.text)
    await message.answer("Введите город партнёра:")
    await state.set_state(AddProtection.dealer_city)

@router.message(AddProtection.dealer_city)
async def set_city(message: Message, state: FSMContext):
    await state.update_data(dealer_city=message.text)
    await message.answer("Введите артикул(ы):")
    await state.set_state(AddProtection.articles)

@router.message(AddProtection.articles)
async def set_articles(message: Message, state: FSMContext):
    await state.update_data(articles=message.text)
    await message.answer("Введите метраж защиты (в м²):")
    await state.set_state(AddProtection.quantity)

@router.message(AddProtection.quantity)
async def set_quantity(message: Message, state: FSMContext):
    try:
        quantity = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("⚠️ Введите числовое значение метража.")
        return

    data = await state.get_data()
    articles = data["articles"].strip().lower()

    # Проверка на похожие активные защиты
    protections = db.fetchall("SELECT * FROM protections WHERE status IN ('active', 'extended')")
    for p in protections:
        db_articles = (p["articles"] or "").strip().lower()
        db_quantity = float(p["quantity"] or 0)
        if db_articles == articles and abs(quantity - db_quantity) / db_quantity <= 0.15:
            similar_msg = (
                "⚠️ Похожая активная защита уже существует:\n"
                f"👤 Менеджер: {p['manager']}\n"
                f"🏢 Партнёр: {p['dealer']}\n"
                f"❗️Артикул: {p['articles']}\n"
                f"📏 Метраж: {p['quantity']} м²\n"
                f"⏰ Истекает: {p['ends']}\n\n"
                "💬 Обратись к коллеге, прежде чем ставить новую защиту."
            )
            await message.answer(similar_msg)
            await state.clear()
            return

    await state.update_data(quantity=quantity)
    await message.answer("Введите имя клиента или организации:")
    await state.set_state(AddProtection.client_name)

@router.message(AddProtection.client_name)
async def set_client_name(message: Message, state: FSMContext):
    await state.update_data(client_name=message.text)
    await message.answer("Введите последние 4 цифры телефона клиента:")
    await state.set_state(AddProtection.phone_last4)

@router.message(AddProtection.phone_last4)
async def set_phone(message: Message, state: FSMContext):
    await state.update_data(phone_last4=message.text)
    await message.answer("Введите город объекта:")
    await state.set_state(AddProtection.object_city)

@router.message(AddProtection.object_city)
async def set_object_city(message: Message, state: FSMContext):
    await state.update_data(object_city=message.text)
    await message.answer("Введите адрес объекта:")
    await state.set_state(AddProtection.address)

@router.message(AddProtection.address)
async def set_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("Добавьте комментарий (или '-' если нет):")
    await state.set_state(AddProtection.comment)

@router.message(AddProtection.comment)
async def finalize_protection(message: Message, state: FSMContext):
    data = await state.get_data()
    comment = message.text if message.text != "-" else "—"
    await state.update_data(comment=comment)
    data = await state.get_data()

    pid = db.add_protection(
        manager=data["manager"],
        dealer=data["dealer"],
        dealer_city=data["dealer_city"],
        articles=data["articles"],
        quantity=data["quantity"],
        client_name=data["client_name"],
        phone_last4=data["phone_last4"],
        object_city=data["object_city"],
        address=data["address"],
        comment=data["comment"],
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ends=(datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
        status="active",
    )

    created_at = datetime.now().strftime("%d.%m.%Y | %H:%M:%S")
    ends = (datetime.now() + timedelta(days=5)).strftime("%d.%m.%Y")

    card = (
        "👍 Защита успешно добавлена\n\n"
        f"👤 Ответственный менеджер: {data['manager']}\n"
        f"🏢 Партнёр: {data['dealer']}\n"
        f"📍 Город Партнёра: {data['dealer_city']}\n\n"
        f"❗️Артикул(ы): {data['articles']}\n"
        f"❗️Метраж защиты: {data['quantity']} м²\n\n"
        f"🧍‍♂️ Имя клиента/Организация: {data['client_name']}\n"
        f"📞 Контакты клиента: {data['phone_last4']}\n"
        f"📍 Местоположение объекта: {data['object_city']}\n"
        f"📍 Адрес объекта: {data['address']}\n"
        f"💬 Комментарий к защите: {data['comment']}\n\n"
        f"📅 Дата создания: {created_at}\n"
        f"📌 Правила размещения: минимальный объём защиты — 50 м², срок 5 дней.\n"
        f"⌛️ Срок окончания: {ends}\n"
        f"📝 Разместил: {data['manager']}\n"
        f"#ID: {pid}"
    )

    await message.answer(card)
    await state.clear()
