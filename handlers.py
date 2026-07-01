from datetime import date
import calendar

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import add_payment, get_payments, mark_as_paid, is_paid, delete_payment
from keyboards import main_keyboard, category_keyboard, cancel_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет, Алексей!\n\n"
        "Я помогу не забывать оплачивать счета.\n\n"
        "Выберите действие:",
        reply_markup=main_keyboard()
    )


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


def format_payment(payment, days_left=None):
    payment_id, name, amount, day, category, link = payment

    text = f"• {name} — {amount} ₽ — {day} число — {category}\n"

    if days_left is not None and days_left < 0:
        text += f"  🚨 Просрочено на {abs(days_left)} дн.\n"

    if link:
        text += f"  🔗 {link}\n"

    return text + "\n"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    step = context.user_data.get("step")

    if text == "❌ Отмена":
        context.user_data.clear()
        await update.message.reply_text(
            "Добавление отменено.",
            reply_markup=main_keyboard()
        )
        return

    if step == "name":
        context.user_data["name"] = text
        context.user_data["step"] = "amount"
        await update.message.reply_text(
            "Введите сумму платежа:",
            reply_markup=cancel_keyboard()
        )
        return

    if step == "amount":
        if not text.isdigit():
            await update.message.reply_text("Сумма должна быть числом. Например: 1600")
            return

        context.user_data["amount"] = int(text)
        context.user_data["step"] = "day"
        await update.message.reply_text(
            "Введите число оплаты. Например: 30",
            reply_markup=cancel_keyboard()
        )
        return

    if step == "day":
        if not text.isdigit() or not 1 <= int(text) <= 31:
            await update.message.reply_text("Введите число от 1 до 31.")
            return

        context.user_data["day"] = int(text)
        context.user_data["step"] = "category"
        await update.message.reply_text(
            "Выберите категорию:",
            reply_markup=category_keyboard()
        )
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

        await update.message.reply_text(
            "✅ Платёж добавлен.",
            reply_markup=main_keyboard()
        )
        return

    if text == "➕ Добавить платёж":
        context.user_data.clear()
        context.user_data["step"] = "name"
        await update.message.reply_text(
            "Введите название платежа:",
            reply_markup=cancel_keyboard()
        )
        return

    if text == "📋 Мои платежи":
        payments = get_payments(user_id)

        if not payments:
            await update.message.reply_text("📋 У тебя пока нет платежей.")
            return

        message = "📋 Мои платежи:\n\n"

        for payment in payments:
            message += format_payment(payment)

        await update.message.reply_text(message)
        return

    if text == "🗑 Удалить платёж":
        payments = get_payments(user_id)

        if not payments:
            await update.message.reply_text("Удалять нечего — платежей пока нет.")
            return

        buttons = []

        for payment in payments:
            payment_id, name, amount, day, category, link = payment

            buttons.append([
                InlineKeyboardButton(
                    f"🗑 {name} — {amount} ₽",
                    callback_data=f"delete_{payment_id}"
                )
            ])

        keyboard = InlineKeyboardMarkup(buttons)

        await update.message.reply_text(
            "Выберите платёж, который нужно удалить:",
            reply_markup=keyboard
        )
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

        message = "⏰ Платежи на сегодня:\n\n"

        for payment in today_payments:
            message += format_payment(payment)

        await update.message.reply_text(message)
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

        message = "❗ Просроченные платежи:\n\n"

        for payment, days_left in overdue_payments:
            message += format_payment(payment, days_left)

        await update.message.reply_text(message)
        return

    await update.message.reply_text("Я пока не понял команду. Нажмите кнопку из меню.")