# handlers/admin_panel.py
import asyncio
from pathlib import Path
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

# === ВАЖНО: эти утилиты уже есть у тебя в проекте, оставляем как было ===
from database.db import fetchall, fetchone, execute
from utils.export import export_protections_to_xlsx, export_stats_to_xlsx
from utils.filters import IsAdmin

router = Router()

# ---------------- Мягкие миграции недостающих полей ----------------
def _ensure_columns():
    info = fetchall("PRAGMA table_info(protections)")
    names = {r["name"] for r in info}
    if "order_number" not in names:
        try: execute("ALTER TABLE protections ADD COLUMN order_number TEXT")
        except Exception: pass
    if "close_reason" not in names:
        try: execute("ALTER TABLE protections ADD COLUMN close_reason TEXT")
        except Exception: pass
_ensure_columns()
# -------------------------------------------------------------------

# ========================= МЕНЮ АДМИН-ПАНЕЛИ =========================
def admin_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Менеджеры", callback_data="adm_users")],
        [InlineKeyboardButton(text="🏢 Партнёры по менеджеру", callback_data="adm_dealers")],
        [InlineKeyboardButton(text="📈 Отчёт по защитам", callback_data="adm_reports")],
        [InlineKeyboardButton(text="📊 Статистика менеджеров", callback_data="adm_stats")],
        [InlineKeyboardButton(text="📦 Архив", callback_data="adm_archive")],
        [InlineKeyboardButton(text="🔍 Найти по партнёру", callback_data="adm_find_partner")]
    ])

@router.message(IsAdmin(), F.text == "⚙️ Админ-панель")
async def admin_panel(message: Message):
    await message.answer("⚙️ Админ-панель:", reply_markup=admin_menu_kb())


# ========================= БЛОК: МЕНЕДЖЕРЫ =========================
class AddMgr(StatesGroup):
    fullname = State()
    tg_id = State()

class DelMgr(StatesGroup):
    tg_id = State()

def managers_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить менеджера", callback_data="mgr_add")],
        [InlineKeyboardButton(text="🗑 Удалить менеджера", callback_data="mgr_del")],
        [InlineKeyboardButton(text="📋 Показать всех", callback_data="mgr_list")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_admin")]
    ])

@router.callback_query(IsAdmin(), F.data == "adm_users")
async def adm_users(call: CallbackQuery):
    await call.message.edit_text("👤 Управление менеджерами:", reply_markup=managers_menu_kb())

@router.callback_query(IsAdmin(), F.data == "mgr_list")
async def mgr_list(call: CallbackQuery):
    rows = fetchall("SELECT id, full_name, telegram_id, role, created_at FROM users ORDER BY created_at DESC")
    if not rows:
        return await call.answer("Пользователей нет.", show_alert=True)
    lines = ["📋 Список пользователей:"]
    for r in rows:
        lines.append(f"• {r['full_name'] or '-'} | 🆔 {r['telegram_id']} | роль: {r['role']}")
    await call.message.edit_text("\n".join(lines), reply_markup=managers_menu_kb())

@router.callback_query(IsAdmin(), F.data == "mgr_add")
async def mgr_add_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddMgr.fullname)
    await call.message.edit_text("Введите полное имя менеджера (как в карточке, напр. «Дмитрий Ж»):")

@router.message(IsAdmin(), AddMgr.fullname)
async def mgr_add_get_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        return await message.answer("Имя не должно быть пустым. Введите ещё раз:")
    await state.update_data(fullname=name)
    await state.set_state(AddMgr.tg_id)
    await message.answer("Теперь отправьте Telegram ID менеджера (узнать можно через @userinfobot):")

@router.message(IsAdmin(), AddMgr.tg_id)
async def mgr_add_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data["fullname"]
    try:
        tg_id = int(message.text.strip())
    except ValueError:
        return await message.answer("ID должен быть числом. Введите заново:")

    execute("INSERT INTO users (telegram_id, full_name, role, created_at) VALUES (?, ?, 'manager', datetime('now'))",
            (tg_id, name))
    await message.answer(f"✅ Менеджер добавлен:\n👤 {name}\n🆔 {tg_id}")

    # Приветствие менеджеру — не критично, завернём в try
    try:
        await message.bot.send_message(tg_id,
            "Привет, 👋!\nВас добавили как менеджера в систему ProjectGuard. Теперь ваши защиты будут отображаться как «ваши».")
    except Exception:
        pass
    await state.clear()

@router.callback_query(IsAdmin(), F.data == "mgr_del")
async def mgr_del_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(DelMgr.tg_id)
    await call.message.edit_text("Введите Telegram ID менеджера, которого нужно удалить:")

@router.message(IsAdmin(), DelMgr.tg_id)
async def mgr_del_finish(message: Message, state: FSMContext):
    tg = message.text.strip()
    execute("DELETE FROM users WHERE telegram_id=?", (tg,))
    await message.answer(f"✅ Пользователь с Telegram ID {tg} удалён.\nЕго существующие защиты останутся в истории.")
    await state.clear()


# ================= ПАРТНЁРЫ ПО МЕНЕДЖЕРУ (список из users) =================
def pick_manager_kb(users):
    rows, buf = [], []
    for i, u in enumerate(users, 1):
        title = u["full_name"] or (u["telegram_id"] and f"tg:{u['telegram_id']}") or f"id:{u['id']}"
        buf.append(InlineKeyboardButton(text=title, callback_data=f"ad_mgr:{u['id']}"))
        if i % 2 == 0:
            rows.append(buf); buf = []
    if buf:
        rows.append(buf)
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@router.callback_query(IsAdmin(), F.data == "adm_dealers")
async def adm_dealers(call: CallbackQuery):
    users = fetchall("SELECT id, full_name, telegram_id, role FROM users WHERE role IN ('manager','admin') ORDER BY created_at DESC")
    if not users:
        return await call.answer("Менеджеров в системе нет. Добавьте через раздел «Менеджеры».", show_alert=True)
    await call.message.edit_text("Выберите менеджера:", reply_markup=pick_manager_kb(users))

def dealers_kb(manager_id, names):
    rows, buf = [], []
    for i, name in enumerate(names, 1):
        buf.append(InlineKeyboardButton(text=name, callback_data=f"ad_dl:{manager_id}:{name}"))
        if i % 2 == 0:
            rows.append(buf); buf = []
    if buf:
        rows.append(buf)
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm_dealers")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@router.callback_query(IsAdmin(), F.data.startswith("ad_mgr:"))
async def ad_mgr(call: CallbackQuery):
    mid = int(call.data.split(":")[1])
    names = [r["dealer"] for r in fetchall(
        "SELECT DISTINCT dealer FROM protections WHERE created_by=(SELECT full_name FROM users WHERE id=?) ORDER BY dealer LIMIT 200", (mid,)
    )]
    if not names:
        mgr = fetchone("SELECT full_name FROM users WHERE id=?", (mid,))
        title = (mgr and mgr["full_name"]) or f"id:{mid}"
        return await call.message.edit_text(f"У менеджера {title} пока нет партнёров.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_dealers")]
        ]))
    await call.message.edit_text("Выберите партнёра:", reply_markup=dealers_kb(mid, names))

def protections_kb(rows):
    buttons = []
    for r in rows:
        st = r["status"]
        if st == "success" and r["order_number"]:
            st += f" (№{r['order_number']})"
        text = f"#{r['id']} | {r['article']} | {r['quantity']}м² | {st}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"ad_view:{r['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm_dealers")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.callback_query(IsAdmin(), F.data.startswith("ad_dl:"))
async def ad_dl(call: CallbackQuery):
    _, mid, dealer = call.data.split(":", 2)
    rows = fetchall(
        """SELECT p.id, p.article, p.quantity, p.status, p.order_number, p.created_at, u.full_name as mgr
           FROM protections p
           LEFT JOIN users u ON u.full_name=p.created_by
           WHERE p.created_by=(SELECT full_name FROM users WHERE id=?) AND p.dealer=?
           ORDER BY datetime(p.created_at) DESC LIMIT 100""",
        (int(mid), dealer),
    )
    if not rows:
        return await call.message.edit_text("Записей нет.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_dealers")]
        ]))
    header = f"👤 Менеджер: {rows[0]['mgr'] or '-'}\n🏢 Партнёр: {dealer}\n\nВыберите защиту для просмотра:"
    await call.message.edit_text(header, reply_markup=protections_kb(rows))

def protection_action_kb(pid, status):
    if status in ("active", "extended", "changed"):
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔁 Продлить", callback_data=f"adm_extend:{pid}"),
                InlineKeyboardButton(text="❌ Снять (с причиной)", callback_data=f"adm_close:{pid}")
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_dealers")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="adm_dealers")]
        ])

@router.callback_query(IsAdmin(), F.data.startswith("ad_view:"))
async def ad_view(call: CallbackQuery):
    pid = int(call.data.split(":")[1])
    r = fetchone(
        """SELECT p.*, u.full_name as mgr_name, u.telegram_id as mgr_tg
           FROM protections p LEFT JOIN users u ON u.full_name=p.created_by
           WHERE p.id=?""",
        (pid,)
    )
    if not r:
        return await call.answer("Защита не найдена.", show_alert=True)

    st = r["status"]
    if st == "success" and r["order_number"]:
        st += f" (№ {r['order_number']})"

    card = (
        f"👍 Защита #{pid}\n\n"
        f"👤 Ответственный менеджер: {r['mgr_name'] or '-'}\n"
        f"🏢 Партнёр: {r['dealer']}\n"
        f"📍 Город Партнёра: {r['city']}\n\n"
        f"❗️Артикул(ы): {r['article']}\n"
        f"❗️Метраж защиты: {r['quantity']} м²\n\n"
        f"🧍‍♂️ Имя клиента/Организация: {r['client_name']}\n"
        f"📞 Контакты клиента: {r['phone_last4']}\n"
        f"📍 Местоположение объекта: {r['object_city']}\n"
        f"📍 Адрес объекта: {r['address']}\n"
        f"💬 Комментарий к защите: {r['comment'] or '—'}\n\n"
        f"📅 Дата создания: {r['created_at']}\n"
        f"⌛️ Срок окончания: {r['expires_at']}\n"
        f"🧾 Статус: {st}\n"
        f"📝 Причина снятия: {r['close_reason'] or '—'}\n"
        f"#ID: {pid}"
    )
    await call.message.edit_text(card, reply_markup=protection_action_kb(pid, r["status"]))


# ============ Закрытие админом (с причиной) ============
class AdmCloseForm(StatesGroup):
    pid = State()
    reason = State()

@router.callback_query(IsAdmin(), F.data.startswith("adm_close:"))
async def adm_close_start(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split(":")[1])
    await state.update_data(pid=pid)
    await state.set_state(AdmCloseForm.reason)
    await call.message.answer(f"Укажите причину закрытия защиты #{pid}:")

@router.message(IsAdmin(), AdmCloseForm.reason)
async def adm_close_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["pid"]
    reason = message.text.strip()
    if not reason:
        return await message.answer("Причина обязательна.")
    row = fetchone("SELECT created_by FROM protections WHERE id=?", (pid,))
    execute("UPDATE protections SET status='closed', close_reason=?, updated_at=datetime('now') WHERE id=?", (reason, pid))
    if row:
        mgr = fetchone("SELECT telegram_id FROM users WHERE full_name=?", (row["created_by"],))
        if mgr and mgr["telegram_id"]:
            try:
                await message.bot.send_message(mgr["telegram_id"], f"⚠️ Ваша защита #{pid} была снята администратором. Причина: {reason}")
            except Exception:
                pass
    await message.answer(f"Защита #{pid} закрыта.")
    await state.clear()


# ===================== ОТЧЁТЫ / ЭКСПОРТ =====================
def report_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 Показать последние 50", callback_data="rep_all")],
        [InlineKeyboardButton(text="📤 Экспорт Excel", callback_data="rep_export")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_admin")]
    ])

@router.callback_query(IsAdmin(), F.data == "adm_reports")
async def adm_reports(call: CallbackQuery):
    await call.message.edit_text("📈 Отчёт по защитам:", reply_markup=report_menu_kb())

@router.callback_query(IsAdmin(), F.data == "rep_all")
async def rep_all(call: CallbackQuery):
    rows = fetchall(
        """SELECT p.*, u.full_name as mgr_name, u.telegram_id as mgr_tg
           FROM protections p LEFT JOIN users u ON u.full_name=p.created_by
           ORDER BY datetime(p.created_at) DESC LIMIT 50"""
    )
    if not rows:
        return await call.answer("Защит нет.", show_alert=True)
    for r in rows:
        st = r["status"]
        if st == "success" and r["order_number"]:
            st += f" (№ {r['order_number']})"
        txt = (
            f"👤 Ответственный менеджер: {r['mgr_name'] or '-'}\n"
            f"🏢 Партнёр: {r['dealer']}\n"
            f"📍 Город партнёра: {r['city']}\n\n"
            f"❗️Артикул(ы): {r['article']}\n"
            f"❗️Метраж защиты: {r['quantity']} м²\n\n"
            f"🧍‍♂️ Клиент: {r['client_name']}\n"
            f"📞 Телефон: {r['phone_last4']}\n"
            f"📍 Объект: {r['object_city'] or '-'}\n"
            f"📍 Адрес: {r['address'] or '-'}\n"
            f"💬 Комментарий: {r['comment'] or '—'}\n\n"
            f"📅 Создано: {r['created_at']}\n"
            f"⌛️ Истекает: {r['expires_at']}\n"
            f"🧾 Статус: {st}\n"
            f"📝 Причина снятия: {r['close_reason'] or '—'}\n"
            f"#ID: {r['id']}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔁 Продлить (админ)", callback_data=f"adm_extend:{r['id']}"),
            InlineKeyboardButton(text="❌ Снять (с причиной)", callback_data=f"adm_close:{r['id']}")
        ]])
        await call.message.answer(txt, reply_markup=kb)

@router.callback_query(IsAdmin(), F.data == "rep_export")
async def rep_export(call: CallbackQuery):
    await call.message.answer("📤 Формирую Excel-отчёт…")
    Path("exports").mkdir(exist_ok=True)
    p = "exports/protections.xlsx"
    try:
        export_protections_to_xlsx(p)
        await asyncio.sleep(1)
        file = FSInputFile(p)
        await call.message.answer_document(document=file, caption="📊 Отчёт по всем защитам (.xlsx)")
    except Exception as e:
        await call.message.answer(f"❌ Ошибка при формировании отчёта: {e}")

# ===================== СТАТИСТИКА =====================
@router.callback_query(IsAdmin(), F.data == "adm_stats")
async def adm_stats(call: CallbackQuery):
    rows = fetchall(
        """SELECT u.full_name as name, u.telegram_id as tg,
                  SUM(1) total,
                  SUM(CASE WHEN p.status IN ('active','extended','changed') THEN 1 ELSE 0 END) active_cnt,
                  SUM(CASE WHEN p.status='success' THEN 1 ELSE 0 END) success_cnt,
                  SUM(CASE WHEN p.status='closed'  THEN 1 ELSE 0 END) closed_cnt,
                  SUM(CASE WHEN p.status='closed' AND COALESCE(p.close_reason,'')<>'' THEN 1 ELSE 0 END) closed_with_reason
           FROM protections p LEFT JOIN users u ON u.full_name=p.created_by
           GROUP BY p.created_by ORDER BY total DESC"""
    )
    if not rows:
        return await call.message.answer("Статистики пока нет.", reply_markup=admin_menu_kb())
    lines = ["📊 Статистика менеджеров:"]
    for r in rows:
        total = r["total"] or 0
        success = r["success_cnt"] or 0
        conv = (success / total * 100) if total else 0
        lines.append(
            f"🧑‍💼 {r['name'] or '-'} (tg:{r['tg']}) — Всего: {total} | Активных: {r['active_cnt']} | "
            f"Успешных: {success} | Снятых: {r['closed_cnt']} | С причиной: {r['closed_with_reason']} | "
            f"Конверсия: {conv:.1f}%"
        )
    await call.message.answer("\n".join(lines), reply_markup=admin_menu_kb())

# ===================== АРХИВ И ПОИСК =====================
@router.callback_query(IsAdmin(), F.data == "adm_archive")
async def adm_archive(call: CallbackQuery):
    rows = fetchall("""SELECT id, dealer, article, quantity, status, created_by
                       FROM protections WHERE status IN ('closed','success')
                       ORDER BY datetime(created_at) DESC LIMIT 150""")
    if not rows:
        return await call.message.edit_text("📦 В архиве пока нет завершённых защит.", reply_markup=admin_menu_kb())
    buttons = [[InlineKeyboardButton(text=f"{r['dealer']} | {r['article']} | {r['quantity']}м² | {r['status']}",
                                     callback_data=f"ad_view:{r['id']}")] for r in rows]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_admin")])
    await call.message.edit_text("📦 Архив завершённых защит:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(IsAdmin(), F.data == "adm_find_partner")
async def adm_find_partner(call: CallbackQuery):
    dealers = [r["dealer"] for r in fetchall("SELECT DISTINCT dealer FROM protections ORDER BY dealer")]
    if not dealers:
        return await call.answer("Партнёров не найдено.", show_alert=True)
    rows, buf = [], []
    for i, d in enumerate(dealers, 1):
        buf.append(InlineKeyboardButton(text=d, callback_data=f"ad_find_d:{d}"))
        if i % 2 == 0:
            rows.append(buf); buf = []
    if buf: rows.append(buf)
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_admin")])
    await call.message.edit_text("Выберите партнёра:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))

@router.callback_query(IsAdmin(), F.data.startswith("ad_find_d:"))
async def ad_find_dealer(call: CallbackQuery):
    dealer = call.data.split(":", 1)[1]
    rows = fetchall("""SELECT id, dealer, article, quantity, status
                       FROM protections WHERE dealer=? ORDER BY datetime(created_at) DESC LIMIT 100""", (dealer,))
    if not rows:
        return await call.message.edit_text("❌ Защиты для этого партнёра не найдены.", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="adm_find_partner")]]
        ))
    buttons = [[InlineKeyboardButton(text=f"#{r['id']} | {r['article']} | {r['quantity']}м² | {r['status']}",
                                     callback_data=f"ad_view:{r['id']}")] for r in rows]
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm_find_partner")])
    await call.message.edit_text(f"📋 Защиты по партнёру: {dealer}", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# ===================== НАЗАД =====================
@router.callback_query(IsAdmin(), F.data == "back_admin")
async def back_admin(call: CallbackQuery):
    await call.message.edit_text("⚙️ Админ-панель:", reply_markup=admin_menu_kb())
