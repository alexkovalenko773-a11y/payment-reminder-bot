from telegram import ReplyKeyboardMarkup


def main_keyboard():
    keyboard = [
        ["➕ Добавить платёж"],
        ["📋 Мои платежи"],
        ["📅 Календарь"],
        ["📂 Категории"],
        ["✏️ Изменить платёж"],
        ["🗑 Удалить платёж"],
        ["⏰ Сегодня"],
        ["❗ Просроченные"],
    ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def category_keyboard(categories=None):
    if categories is None:
        categories = []

    keyboard = []

    for category_id, name in categories:
        keyboard.append([name])

    keyboard.append(["❌ Отмена"])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def categories_manage_keyboard():
    keyboard = [
        ["➕ Добавить категорию"],
        ["🗑 Удалить категорию"],
        ["⬅️ Назад"],
    ]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def cancel_keyboard():
    keyboard = [["❌ Отмена"]]

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)