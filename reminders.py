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


def make_payment_buttons(payment_id, link):
    buttons = []

    if link:
        buttons.append([
            InlineKeyboardButton("🔗 Открыть ссылку", url=link)
        ])

    buttons.append([
        InlineKeyboardButton("✅ Оплачено", callback_data=f"paid:{payment_id}")
    ])

    return InlineKeyboardMarkup(buttons)


async def reminder_loop(app):
    while True:
        today = date.today()
        current_month = today.strftime("%Y-%m")

        payments = get_all_payments()

        for payment in payments:
            payment_id, user_id, name, amount, day, category, link = payment

            if is_paid(payment_id, current_month):
                continue

            last_day = calendar.monthrange(today.year, today.month)[1]
            real_day = min(day, last_day)

            due_date = date(today.year, today.month, real_day)
            days_left = (due_date - today).days

            reminder_type = None
            text = None

            if days_left == 7:
                reminder_type = "before_7_days"
                text = (
                    "🔔 Скоро платёж\n\n"
                    f"💳 {name}\n"
                    f"💰 {amount} ₽\n"
                    f"📅 Оплатить через 7 дней\n"
                    f"📂 {category}"
                )

            elif days_left == 3:
                reminder_type = "before_3_days"
                text = (
                    "🔔 Напоминание о платеже\n\n"
                    f"💳 {name}\n"
                    f"💰 {amount} ₽\n"
                    f"📅 Оплатить через 3 дня\n"
                    f"📂 {category}"
                )

            elif days_left == 1:
                reminder_type = "before_1_day"
                text = (
                    "⚠️ Завтра платёж\n\n"
                    f"💳 {name}\n"
                    f"💰 {amount} ₽\n"
                    f"📂 {category}"
                )

            elif days_left == 0:
                reminder_type = "today"
                text = (
                    "🚨 Сегодня нужно оплатить\n\n"
                    f"💳 {name}\n"
                    f"💰 {amount} ₽\n"
                    f"📂 {category}"
                )

            elif days_left < 0:
                reminder_type = "overdue"
                text = (
                    f"🔴 Платёж просрочен на {abs(days_left)} дн.\n\n"
                    f"💳 {name}\n"
                    f"💰 {amount} ₽\n"
                    f"📂 {category}"
                )

            if reminder_type:
                reminder_date = today.isoformat()

                if not reminder_was_sent(payment_id, reminder_date, reminder_type):
                    await app.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        reply_markup=make_payment_buttons(payment_id, link)
                    )

                    save_reminder(payment_id, reminder_date, reminder_type)

        await asyncio.sleep(3600)


async def post_init(app):
    asyncio.create_task(reminder_loop(app))