import asyncio
import calendar
from datetime import date

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database import (
    get_all_payments,
    reminder_was_sent,
    save_reminder,
    is_paid,
)


REMIND_DAYS = [3, 1, 0]


def prepare_link(link):
    if not link:
        return ""

    link = str(link).strip()

    if not link:
        return ""

    if not link.startswith(("http://", "https://")):
        link = "https://" + link

    return link


def get_days_left(day):
    today = date.today()

    last_day = calendar.monthrange(today.year, today.month)[1]
    real_day = min(day, last_day)

    due_date = date(today.year, today.month, real_day)
    return (due_date - today).days


def make_reminder_text(name, amount, day, category, days_left):
    if days_left == 3:
        title = "🔔 Через 3 дня нужно оплатить:"
    elif days_left == 1:
        title = "🟡 Завтра нужно оплатить:"
    elif days_left == 0:
        title = "🚨 Сегодня нужно оплатить:"
    else:
        title = "🔔 Напоминание об оплате:"

    return (
        f"{title}\n\n"
        f"💳 {name}\n"
        f"💰 {amount} ₽\n"
        f"📅 {day} число\n"
        f"📂 {category}"
    )


def make_reminder_keyboard(payment_id, link):
    buttons = []

    payment_link = prepare_link(link)

    if payment_link:
        buttons.append([
            InlineKeyboardButton("🔗 Оплатить", url=payment_link)
        ])

    buttons.append([
        InlineKeyboardButton("✅ Оплачено", callback_data=f"paid:{payment_id}")
    ])

    return InlineKeyboardMarkup(buttons)


async def reminder_loop(app):
    while True:
        today = date.today()
        today_str = today.isoformat()
        current_month = today.strftime("%Y-%m")

        payments = get_all_payments()

        for payment in payments:
            payment_id, user_id, name, amount, day, category, link = payment

            if is_paid(payment_id, current_month):
                continue

            days_left = get_days_left(day)

            if days_left not in REMIND_DAYS:
                continue

            reminder_type = f"{days_left}_days"

            if reminder_was_sent(payment_id, today_str, reminder_type):
                continue

            message = make_reminder_text(
                name=name,
                amount=amount,
                day=day,
                category=category,
                days_left=days_left
            )

            keyboard = make_reminder_keyboard(payment_id, link)

            try:
                await app.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    reply_markup=keyboard,
                    disable_web_page_preview=True
                )

                save_reminder(payment_id, today_str, reminder_type)

            except Exception as e:
                print(f"Ошибка отправки напоминания: {e}")

        await asyncio.sleep(60 * 60)


async def post_init(app):
    app.create_task(reminder_loop(app))