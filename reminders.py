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

            if days_left == 3:
                reminder_type = "before_3_days"
                text = f"🔔 Через 3 дня нужно оплатить:\n\n{name}\n💰 {amount} ₽\n📅 {real_day} число"

            elif days_left == 1:
                reminder_type = "before_1_day"
                text = f"🔔 Завтра нужно оплатить:\n\n{name}\n💰 {amount} ₽"

            elif days_left == 0:
                reminder_type = "today"
                text = f"⚠️ Сегодня нужно оплатить:\n\n{name}\n💰 {amount} ₽"

            elif days_left < 0:
                reminder_type = "overdue"
                text = f"🚨 Просрочено на {abs(days_left)} дн.\n\n{name}\n💰 {amount} ₽"

            if reminder_type:
                reminder_date = today.isoformat()

                if not reminder_was_sent(payment_id, reminder_date, reminder_type):
                    buttons = []

                    if link:
                        buttons.append([
                            InlineKeyboardButton(
                                "🌐 Открыть личный кабинет",
                                url=link
                            )
                        ])

                    buttons.append([
                        InlineKeyboardButton(
                            "✅ Оплачено",
                            callback_data=f"paid:{payment_id}"
                        )
                    ])

                    reply_markup = InlineKeyboardMarkup(buttons)

                    await app.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        reply_markup=reply_markup
                    )

                    save_reminder(payment_id, reminder_date, reminder_type)

        await asyncio.sleep(3600)


async def post_init(app):
    asyncio.create_task(reminder_loop(app))