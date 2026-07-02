from telegram import ReplyKeyboardMarkup


def main_keyboard():
    keyboard = [
        ["➕ Добавить платёж"],
        ["📋 Мои платежи"],
        ["📅 Календарь"],
        ["✏️ Изменить платёж"],
        ["🗑 Удалить платёж"],
        ["⏰ Сегодня"],
        ["❗ Просроченные"],
    ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def category_keyboard():
    keyboard = [
        ["🏠 Дом", "💼 Бизнес"],
        ["📱 Подписки", "🚗 Авто"],
        ["➕ Другое"],
        ["❌ Отмена"],
    ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def cancel_keyboard():
    keyboard = [["❌ Отмена"]]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)