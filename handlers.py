from datetime import date
import calendar
import html

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import (
    add_payment,
    get_payments,
    get_payments_by_category,
    mark_as_paid,
    is_paid,
    delete_payment,
    get_payment_by_id,
    update_payment_field,
    ensure_default_categories,
    get_categories,
    add_category,
    delete_category,
)

from keyboards import (
    main_keyboard,
    category_keyboard,
    categories_manage_keyboard,
    cancel_keyboard,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    ensure_default_categories(user_id)

    payments = get_payments(user_id)

    total = len(payments)
    today_count = 0
    overdue_count = 0
    nearest_payment = None
    nearest_days = None

    for payment in payments:
        status, days_left = get_payment_status(payment)

        if status == "today":
            today_count += 1

        if status == "overdue":
            overdue_count += 1

        if status != "paid":
            if nearest_days is None or days_left < nearest_days:
                nearest_days = days_left
                nearest_payment = payment

    message = (
        "👋 Привет, Алексей!\n\n"
        "Я помогу не забывать оплачивать счета.\n\n"
        "📊 Сводка:\n"
        f"💳 Всего платежей: {total}\n"
        f"🚨 Сегодня: {today_count}\n"
        f"🔴 Просрочено: {overdue_count}\n"
    )

    if nearest_payment:
        payment_id, name, amount, day, category, link = nearest_payment

        if nearest_days < 0:
            nearest_text = f"{name} — просрочено на {abs(nearest_days)} дн."
        elif nearest_days == 0:
            nearest_text = f"{name} — сегодня"
        elif nearest_days == 1:
            nearest_text = f"{name} — завтра"
        else:
            nearest_text = f"{name} — через {nearest_days} дн."

        message += f"📅 Ближайший: {nearest_text}\n"

    message += "\nВыберите действие:"

    await update.message.reply_text(message, reply_markup=main_keyboard())


async def handle_paid_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    payment_id = int(query.data.split(":")[1])
    current_month = date.today().strftime("%Y-%m")

    mark_as_paid(payment_id, current_month)

    await query.edit_message_text(
        "✅ Платёж отмечен как оплаченный.\n\n"
        "В этом месяце я больше не буду по нему напоминать."
    )


async def handle_delete_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    payment_id = int(query.data.split("_")[1])
    user_id = query.from_user.id

    delete_payment(payment_id, user_id)

    await query.edit_message_text("🗑 Платёж удалён.")


async def handle_category_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    category = query.data.replace("category_", "")

    payments = get_payments_by_category(user_id, category)

    if not payments:
        await query.edit_message_text(f"📂 В категории {category} платежей нет.")
        return

    payments = sorted(payments, key=sort_by_nearest_payment)

    message = f"📂 Категория: {html.escape(category)}\n\n"

    for payment in payments:
        message += format_payment(payment)

    await query.edit_message_text(message, parse_mode="HTML")


async def handle_delete_category_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category_id = int(query.data.split("_")[1])
    user_id = query.from_user.id

    delete_category(category_id, user_id)

    await query.edit_message_text("🗑 Категория удалена.")


async def handle_edit_select_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    payment_id = int(query.data.split("_")[1])
    user_id = query.from_user.id

    payment = get_payment_by_id(payment_id, user_id)

    if not payment:
        await query.edit_message_text("Платёж не найден.")
        return

    payment_id, name, amount, day, category, link = payment

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Название", callback_data=f"editfield_{payment_id}_name")],
        [InlineKeyboardButton("💰 Сумма", callback_data=f"editfield_{payment_id}_amount")],
        [InlineKeyboardButton("📅 День оплаты", callback_data=f"editfield_{payment_id}_day")],
        [InlineKeyboardButton("📂 Категория", callback_data=f"editfield_{payment_id}_category")],
        [InlineKeyboardButton("🔗 Ссылка", callback_data=f"editfield_{payment_id}_link")],
    ])

    await query.edit_message_text(
        f"✏️ Что изменить?\n\n"
        f"💳 {name}\n"
        f"💰 {amount} ₽\n"
        f"📅 {day} число\n"
        f"📂 {category}",
        reply_markup=keyboard
    )


async def handle_edit_field_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, payment_id, field = query.data.split("_")

    context.user_data["step"] = "edit_value"
    context.user_data["edit_payment_id"] = int(payment_id)
    context.user_data["edit_field"] = field

    field_names = {
        "name": "новое название",
        "amount": "новую сумму",
        "day": "новое число оплаты",
        "category": "новую категорию",
        "link": "новую ссылку",
    }

    await query.edit_message_text(f"Введите {field_names[field]}:")


def get_payment_status(payment):
    payment_id, name, amount, day, category, link = payment

    today = date.today()
    current_month = today.strftime("%Y-%m")

    if is_paid(payment_id, current_month):
        return "paid", 0

    last_day = calendar.monthrange(today.year, today.month)[1]
    real_day = min(day, last_day)

    due_date = date(today.year, today.month, real_day)
    days_left = (due_date - today).days

    if days_left == 0:
        return "today", days_left

    if days_left < 0:
        return "overdue", days_left

    return "future", days_left


def sort_by_nearest_payment(payment):
    status, days_left = get_payment_status(payment)

    if status == "overdue":
        return days_left

    if status == "today":
        return 0

    if status == "paid":
        return 999

    return days_left


def prepare_link(link):
    if not link:
        return ""

    link = str(link).strip()

    if not link:
        return ""

    if not link.startswith(("http://", "https://")):
        link = "https://" + link

    return html.escape(link, quote=True)


def format_payment(payment, days_left=None):
    payment_id, name, amount, day, category, link = payment

    status, real_days_left = get_payment_status(payment)

    if status == "paid":
        status_text = "🟢 оплачено"
    elif status == "overdue":
        status_text = f"🔴 просрочено на {abs(real_days_left)} дн."
    elif status == "today":
        status_text = "🚨 сегодня"
    elif real_days_left == 1:
        status_text = "🟡 завтра"
    else:
        status_text = f"⚪ через {real_days_left} дн."

    safe_name = html.escape(str(name))
    safe_category = html.escape(str(category))
    safe_link = prepare_link(link)

    text = (
        f"• {safe_name} — {amount} ₽\n"
        f"  📅 {day} число — {safe_category}\n"
        f"  {status_text}\n"
    )

    if safe_link:
        text += f'  🔗 <a href="{safe_link}">Оплатить</a>\n'

    return text + "\n"


def format_calendar_payment(payment):
    payment_id, name, amount, day, category, link = payment

    today = date.today()
    current_month = today.strftime("%Y-%m")
    status, days_left = get_payment_status(payment)

    if is_paid(payment_id, current_month):
        emoji = "🟢"
        status_text = "оплачено"
    elif status == "overdue":
        emoji = "🔴"
        status_text = f"просрочено {abs(days_left)} дн."
    elif status == "today":
        emoji = "🚨"
        status_text = "сегодня"
    elif days_left == 1:
        emoji = "🟡"
        status_text = "завтра"
    else:
        emoji = "⚪"
        status_text = f"через {days_left} дн."

    return f"{emoji} {day:02d} — {name} — {amount} ₽ — {status_text}\n"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    step = context.user_data.get("step")

    ensure_default_categories(user_id)

    if text == "❌ Отмена":
        context.user_data.clear()
        await update.message.reply_text("Действие отменено.", reply_markup=main_keyboard())
        return

    if text == "⬅️ Назад":
        context.user_data.clear()
        await update.message.reply_text("Главное меню.", reply_markup=main_keyboard())
        return

    if step == "add_category":
        add_category(user_id, text)
        context.user_data.clear()
        await update.message.reply_text(f"✅ Категория добавлена: {text}", reply_markup=main_keyboard())
        return

    if step == "edit_value":
        payment_id = context.user_data["edit_payment_id"]
        field = context.user_data["edit_field"]
        value = text

        if field == "amount":
            if not text.isdigit():
                await update.message.reply_text("Сумма должна быть числом. Например: 1600")
                return
            value = int(text)

        if field == "day":
            if not text.isdigit() or not 1 <= int(text) <= 31:
                await update.message.reply_text("Введите число от 1 до 31.")
                return
            value = int(text)

        if field == "link" and text.lower() == "нет":
            value = ""

        update_payment_field(payment_id, user_id, field, value)
        context.user_data.clear()

        await update.message.reply_text("✅ Платёж обновлён.", reply_markup=main_keyboard())
        return

    if step == "name":
        context.user_data["name"] = text
        context.user_data["step"] = "amount"
        await update.message.reply_text("Введите сумму платежа:", reply_markup=cancel_keyboard())
        return

    if step == "amount":
        if not text.isdigit():
            await update.message.reply_text("Сумма должна быть числом. Например: 1600")
            return

        context.user_data["amount"] = int(text)
        context.user_data["step"] = "day"
        await update.message.reply_text("Введите число оплаты. Например: 30", reply_markup=cancel_keyboard())
        return

    if step == "day":
        if not text.isdigit() or not 1 <= int(text) <= 31:
            await update.message.reply_text("Введите число от 1 до 31.")
            return

        context.user_data["day"] = int(text)
        context.user_data["step"] = "category"

        categories = get_categories(user_id)

        await update.message.reply_text("Выберите категорию:", reply_markup=category_keyboard(categories))
        return

    if step == "category":
        context.user_data["category"] = text
        context.user_data["step"] = "link"

        await update.message.reply_text(
            "Пришлите ссылку на личный кабинет.\n\n"
            "Если ссылки нет, напишите: нет",
            reply_markup=cancel_keyboard()
        )
        return

    if step == "link":
        link = "" if text.lower() == "нет" else text

        add_payment(
            user_id=user_id,
            name=context.user_data["name"],
            amount=context.user_data["amount"],
            day=context.user_data["day"],
            category=context.user_data["category"],
            link=link
        )

        context.user_data.clear()

        await update.message.reply_text("✅ Платёж добавлен.", reply_markup=main_keyboard())
        return

    if text == "➕ Добавить платёж":
        context.user_data.clear()
        context.user_data["step"] = "name"

        await update.message.reply_text("Введите название платежа:", reply_markup=cancel_keyboard())
        return

    if text == "📋 Мои платежи":
        payments = get_payments(user_id)

        if not payments:
            await update.message.reply_text("📋 У тебя пока нет платежей.")
            return

        payments = sorted(payments, key=sort_by_nearest_payment)

        message = "📋 Мои платежи:\n\n"

        for payment in payments:
            message += format_payment(payment)

        await update.message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)
        return

    if text == "📅 Календарь":
        payments = get_payments(user_id)

        if not payments:
            await update.message.reply_text("📅 В календаре пока нет платежей.")
            return

        month_names = {
            1: "Январь",
            2: "Февраль",
            3: "Март",
            4: "Апрель",
            5: "Май",
            6: "Июнь",
            7: "Июль",
            8: "Август",
            9: "Сентябрь",
            10: "Октябрь",
            11: "Ноябрь",
            12: "Декабрь",
        }

        today = date.today()
        message = f"📅 {month_names[today.month]} {today.year}\n\n"

        payments = sorted(payments, key=lambda p: p[3])

        for payment in payments:
            message += format_calendar_payment(payment)

        await update.message.reply_text(message)
        return

    if text == "📂 Категории":
        categories = get_categories(user_id)

        buttons = []

        for category_id, name in categories:
            buttons.append([
                InlineKeyboardButton(name, callback_data=f"category_{name}")
            ])

        await update.message.reply_text("📂 Выберите категорию:", reply_markup=InlineKeyboardMarkup(buttons))
        await update.message.reply_text("Управление категориями:", reply_markup=categories_manage_keyboard())
        return

    if text == "➕ Добавить категорию":
        context.user_data.clear()
        context.user_data["step"] = "add_category"

        await update.message.reply_text("Введите название новой категории:", reply_markup=cancel_keyboard())
        return

    if text == "🗑 Удалить категорию":
        categories = get_categories(user_id)

        if not categories:
            await update.message.reply_text("Категорий пока нет.")
            return

        buttons = []

        for category_id, name in categories:
            buttons.append([
                InlineKeyboardButton(f"🗑 {name}", callback_data=f"deletecategory_{category_id}")
            ])

        await update.message.reply_text("Выберите категорию для удаления:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if "Изменить платёж" in text:
        payments = get_payments(user_id)

        if not payments:
            await update.message.reply_text("Изменять нечего — платежей пока нет.")
            return

        payments = sorted(payments, key=sort_by_nearest_payment)

        buttons = []

        for payment in payments:
            payment_id, name, amount, day, category, link = payment

            buttons.append([
                InlineKeyboardButton(f"✏️ {name} — {amount} ₽", callback_data=f"edit_{payment_id}")
            ])

        await update.message.reply_text("Выберите платёж, который нужно изменить:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if "Удалить платёж" in text:
        payments = get_payments(user_id)

        if not payments:
            await update.message.reply_text("Удалять нечего — платежей пока нет.")
            return

        payments = sorted(payments, key=sort_by_nearest_payment)

        buttons = []

        for payment in payments:
            payment_id, name, amount, day, category, link = payment

            buttons.append([
                InlineKeyboardButton(f"🗑 {name} — {amount} ₽", callback_data=f"delete_{payment_id}")
            ])

        await update.message.reply_text("Выберите платёж, который нужно удалить:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if text == "⏰ Сегодня":
        payments = get_payments(user_id)
        today_payments = []

        for payment in payments:
            status, days_left = get_payment_status(payment)

            if status == "today":
                today_payments.append(payment)

        if not today_payments:
            await update.message.reply_text("⏰ На сегодня платежей нет.")
            return

        today_payments = sorted(today_payments, key=sort_by_nearest_payment)

        message = "⏰ Платежи на сегодня:\n\n"

        for payment in today_payments:
            message += format_payment(payment)

        await update.message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)
        return

    if text == "❗ Просроченные":
        payments = get_payments(user_id)
        overdue_payments = []

        for payment in payments:
            status, days_left = get_payment_status(payment)

            if status == "overdue":
                overdue_payments.append((payment, days_left))

        if not overdue_payments:
            await update.message.reply_text("✅ Просроченных платежей нет.")
            return

        overdue_payments = sorted(overdue_payments, key=lambda item: item[1])

        message = "❗ Просроченные платежи:\n\n"

        for payment, days_left in overdue_payments:
            message += format_payment(payment)

        await update.message.reply_text(message, parse_mode="HTML", disable_web_page_preview=True)
        return

    await update.message.reply_text("Я пока не понял команду. Нажмите кнопку из меню.")
