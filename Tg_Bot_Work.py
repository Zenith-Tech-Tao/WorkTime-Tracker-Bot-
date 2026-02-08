# Импорт необходимых библиотек
import telebot
import sqlite3
from config import TOKEN  # Импорт токена бота из отдельного файла config.py
from telebot import types  # Для создания кнопок и разметки
from datetime import datetime  # Для работы с датой и временем
from config import ADMIN_ID  # ID администратора для специальных команд

# Создание объекта бота с использованием токена
bot = telebot.TeleBot(TOKEN)

# Подключение к базе данных SQLite
# check_same_thread=False позволяет использовать соединение из разных потоков
dp = sqlite3.connect('ZenithTechTao.db', check_same_thread=False)

# Создание курсора для выполнения SQL-запросов
cursor = dp.cursor()

# Создание таблицы для хранения данных о рабочих сменах
# IF NOT EXISTS - создаем таблицу только если она еще не существует
cursor.execute("""CREATE TABLE IF NOT EXISTS work (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  
    user_id INTEGER,                       
    name TEXT,                            
    start_time TEXT,                      
    end_time TEXT,                       
    hours REAL,                         
    many REAL,                            
    workout_date TEXT DEFAULT (DATETIME('now', 'localtime')) 
)""")

# Сохраняем изменения в базе данных
dp.commit()


# Обработчик команды /start - запуск бота
@bot.message_handler(commands=["start"])
def start(message):
    # Получаем имя пользователя: сначала username, если нет - first_name
    name = message.from_user.username or message.from_user.first_name

    # Создаем инлайн-клавиатуру с кнопками
    markup = types.InlineKeyboardMarkup()
    btn_1_start = types.InlineKeyboardButton("Начать работу", callback_data='start')
    btn_2_end = types.InlineKeyboardButton("Закончить работу", callback_data='end')
    btn_3_info = types.InlineKeyboardButton("Статистика", callback_data='stats')

    # Располагаем кнопки в рядах
    markup.row(btn_1_start, btn_2_end)
    markup.row(btn_3_info)

    # Отправляем приветственное сообщение с клавиатурой
    bot.send_message(message.chat.id,
                     f"Здравствуйте, <b>{name}</b>.👋 \n\n"
                     f"Это бот для счета отработанных часов и зарплаты.\n\n"
                     f"Выберите действие:",
                     reply_markup=markup,
                     parse_mode='HTML')  # HTML для жирного текста


# Обработчик команды очистки всей базы данных (только для админа)
@bot.message_handler(commands=["sekret"])
def clear(message):
    # Проверяем, является ли отправитель администратором
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет прав для этой команды!")
        return

    # Создаем клавиатуру с подтверждением удаления
    markup = types.InlineKeyboardMarkup()
    btn_yes = types.InlineKeyboardButton('✅ Да, очистить', callback_data='clear_yes')
    btn_no = types.InlineKeyboardButton('❌ Нет, отмена', callback_data='clear_no')
    markup.row(btn_yes, btn_no)

    # Запрос подтверждения на удаление всех данных
    bot.reply_to(message,
                 "⚠️ <b>Внимание! Вы собираетесь удалить ВСЕ данные из базы.</b>\n\n"
                 "Это действие нельзя отменить!\n\n"
                 "Вы уверены?",
                 reply_markup=markup,
                 parse_mode='HTML')


# Обработчик команды удаления конкретного пользователя (только для админа)
@bot.message_handler(commands=["dell"])
def dell(message):
    # Проверяем права администратора
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ У вас нет прав для этой команды!")
        return

    # Создаем клавиатуру с кнопкой отмены
    markup = types.InlineKeyboardMarkup()
    btn_no = types.InlineKeyboardButton('❌ Отмена', callback_data='dell_no')
    markup.row(btn_no)

    # Получаем список всех уникальных пользователей из базы
    cursor.execute("""SELECT DISTINCT user_id, name FROM work""")
    all_users = cursor.fetchall()

    # Если пользователей нет - показываем сообщение
    if not all_users:
        bot.reply_to(message, "📊 <b>Общая статистика:</b>\n\nНет данных о пользователях", parse_mode='HTML')
        return

    # Формируем сообщение со статистикой всех пользователей
    message_info = "📋 <b>Список пользователей:</b>\n\n"

    # Для каждого пользователя рассчитываем его статистику
    for user_id, user_name in all_users:
        # Получаем все записи конкретного пользователя
        cursor.execute("""SELECT * FROM work WHERE user_id = ?""", (user_id,))
        user_records = cursor.fetchall()

        # Инициализируем счетчики для пользователя
        summa_sessions = 0
        summa_hors = 0
        summa_money = 0

        # Считаем общую статистику по всем сессиям пользователя
        for record in user_records:
            if record[5] is not None:  # record[5] - это поле hours
                summa_sessions += 1
                summa_hors += round(record[5] or 0, 2)  # или 0 если значение None
                summa_money += round(record[6] or 0, 2)  # record[6] - это поле many

        # Округляем значения для красивого вывода
        summa_hors = round(summa_hors, 2)
        summa_money = round(summa_money, 2)

        # Форматируем информацию о пользователе
        message_info += (
            f"👤 <b>{user_name}</b>\n"
            f"   🔢 ID: <code>{user_id}</code>\n"
            f"   📊 Сессий: {summa_sessions}\n"
            f"   ⏱️ Часов: {summa_hors:.2f}\n"
            f"   💰 Заработано: {summa_money:.2f} руб.\n\n"
        )

    # Добавляем инструкцию для администратора
    message_info += "\n👇 <b>Введите ID пользователя для удаления:</b>"

    # Отправляем список пользователей и ждем ввода ID
    msg = bot.reply_to(message, message_info, parse_mode='HTML', reply_markup=markup)

    # Регистрируем следующий шаг обработки - функцию для обработки введенного ID
    bot.register_next_step_handler(msg, process_user_id_for_deletion)


# Функция обработки введенного ID пользователя для удаления
def process_user_id_for_deletion(message):
    # Проверяем права администратора
    if message.from_user.id != ADMIN_ID:
        return

    # Получаем и очищаем введенный текст
    id = message.text.strip()

    # Проверяем, что введено число
    if not id.isdigit():
        bot.reply_to(message, "❌ ID должен быть числом!\nПопробуйте снова: /dell")
        return

    # Преобразуем строку в число
    user_id = int(id)

    # Проверяем, существует ли пользователь с таким ID в базе
    cursor.execute("""SELECT name FROM work WHERE user_id = ?""", (user_id,))
    user_exists = cursor.fetchall()

    if user_exists:
        # Получаем имя пользователя (первая запись)
        user_name = user_exists[0][0] if user_exists[0][0] else "Без имени"

        # Создаем клавиатуру подтверждения удаления
        markup = types.InlineKeyboardMarkup()
        btn_yes = types.InlineKeyboardButton('✅ Да, удалить', callback_data=f'remove_yes_{user_id}')
        btn_no = types.InlineKeyboardButton('❌ Нет, отмена', callback_data='cancel_remove')
        markup.row(btn_yes, btn_no)

        # Запрос подтверждения удаления конкретного пользователя
        bot.send_message(message.chat.id,
                         f"⚠️ <b>Подтвердите удаление:</b>\n\n"
                         f"👤 Имя: {user_name}\n"
                         f"🔢 ID: {id}\n\n"
                         f"Удалить этого пользователя?",
                         reply_markup=markup,
                         parse_mode='HTML')
    else:
        # Если пользователь не найден
        bot.send_message(message.chat.id,
                         f"❌ Пользователь с ID {id} не найден.\n"
                         f"Попробуйте снова: /dell")


# Основной обработчик callback-запросов от кнопок
@bot.callback_query_handler(func=lambda callback: True)
def btn(callback):
    # Подтверждаем получение callback (убирает часики на кнопке)
    bot.answer_callback_query(callback.id)

    # === НАЧАТЬ РАБОТУ ===
    if callback.data == "start":
        # Получаем данные пользователя
        user_id = callback.from_user.id
        name = callback.from_user.username or callback.from_user.first_name
        # Текущее время в формате "день-месяц-год, час:минута"
        start_time = datetime.now().strftime("%d-%m-%Y, %H:%M")

        # Сохраняем начало работы в базу данных
        cursor.execute("""INSERT INTO work (user_id, name, start_time) VALUES (?,?,?) """,
                       (user_id, name, start_time))
        dp.commit()

        # Меняем сообщение на подтверждение начала работы
        markup = types.InlineKeyboardMarkup()
        btn_2_end = types.InlineKeyboardButton("Закончить работу", callback_data='end')
        markup.row(btn_2_end)

        bot.edit_message_text(f"✅ <b>Работа начата!</b>\n\n"
                              f"🕐 {start_time}\n\n"
                              f"Не забудь нажать 'Закончить' когда закончите!",
                              chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              parse_mode="HTML",
                              reply_markup=markup)

    # === ЗАКОНЧИТЬ РАБОТУ ===
    elif callback.data == "end":
        user_id = callback.from_user.id
        name = callback.from_user.username or callback.from_user.first_name
        # Запоминаем время окончания работы
        end_time = datetime.now()

        # Ищем последнюю незавершенную смену пользователя
        cursor.execute("""
            SELECT id, start_time 
            FROM work
            WHERE user_id = ? AND end_time IS NULL
            ORDER BY id DESC
            LIMIT 1
        """, (user_id,))
        last_work = cursor.fetchone()

        if last_work:
            # Подготовка меню для возврата
            markup = types.InlineKeyboardMarkup()
            btn_menu = types.InlineKeyboardButton('Главное меню', callback_data='menu')
            markup.row(btn_menu)

            work_id, start_time_str = last_work

            # Преобразуем строку времени в объект datetime для расчетов
            start_time_obj = datetime.strptime(start_time_str, "%d-%m-%Y, %H:%M")

            # Вычисляем разницу во времени
            time_difference = end_time - start_time_obj

            # Переводим секунды в часы
            info_time = time_difference.total_seconds()
            hours = round(info_time / 3600, 2)  # Округляем до 2 знаков

            # Рассчитываем зарплату: 400 руб/час
            many = round(hours * 400, 2)
            end_time_str = end_time.strftime("%d-%m-%Y, %H:%M")

            # Обновляем запись в базе данных
            cursor.execute("""UPDATE work SET end_time = ?, hours = ?, many = ? WHERE id = ?""",
                           (end_time_str, hours, many, work_id))
            dp.commit()

            # Отправляем результат пользователю
            bot.send_message(callback.message.chat.id,
                             f"✅ <b>Работа завершена</b> в {end_time_str}!\n\n"
                             f"👤 Пользователь: <b>{name}</b>\n"
                             f"⏱️ Отработано: {hours} часов\n"
                             f"💰 Заработано: {many} руб.",
                             reply_markup=markup,
                             parse_mode="HTML")
        else:
            # Если нет активной смены
            bot.send_message(
                callback.message.chat.id,
                f"❌ <b>{name}</b>, у вас <b>нет активных смен!</b>\n"
                "Нажми 'Начать' чтобы начать новую.",
                parse_mode="HTML"
            )

    # === ГЛАВНОЕ МЕНЮ ===
    elif callback.data == "menu":
        markup = types.InlineKeyboardMarkup()
        btn1_start = types.InlineKeyboardButton('Начать', callback_data='start')
        btn2_end = types.InlineKeyboardButton('Закончить', callback_data='end')
        btn3_stats = types.InlineKeyboardButton('Статистика', callback_data='stats')

        markup.row(btn1_start, btn2_end)
        markup.row(btn3_stats)

        # Подробное описание функций бота
        bot.send_message(callback.message.chat.id,
                         "👷 <b>ГББ: Центр управления работой</b> 👷\n\n"
                         '"<b>Начать</b>" — Начинает новую рабочую смену.\n'
                         '"<b>Закончить</b>" — Завершает текущую активную смену.\n'
                         '"<b>Статистика</b>" — Показывает вашу персональную или общую статистику.\n\n'
                         'Выберите действия:',
                         reply_markup=markup,
                         parse_mode="HTML")

    # === МЕНЮ СТАТИСТИКИ ===
    elif callback.data == "stats":
        markup = types.InlineKeyboardMarkup()
        btn1_me_stats = types.InlineKeyboardButton('Моя статистика', callback_data='me_stats')
        btn2_global_stats = types.InlineKeyboardButton('Общая статистика', callback_data='global_stats')

        markup.row(btn1_me_stats, btn2_global_stats)

        bot.edit_message_text("Выбери подходящую статистику:",
                              chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              reply_markup=markup)

    # === МОЯ СТАТИСТИКА ===
    elif callback.data == "me_stats":
        user_id = callback.from_user.id
        name = callback.from_user.username or callback.from_user.first_name

        # Получаем ВСЕ записи пользователя из базы
        cursor.execute("""SELECT * FROM work WHERE user_id = ?""", (user_id,))
        all_records = cursor.fetchall()

        # Инициализируем счетчики
        summa_sessions = 0
        summa_hors = 0
        summa_money = 0

        # Считаем статистику вручную
        for record in all_records:
            # record[5] = hours, record[6] = many
            if record[5] is not None:  # Если есть часы - значит сессия завершена
                summa_sessions += 1
                summa_hors += round(record[5] or 0, 2)  # or 0 на случай если значение None
                summa_money += round(record[6] or 0, 2)

        # Округляем итоговые значения
        summa_hors = round(summa_hors, 2)
        summa_money = round(summa_money, 2)

        # Формируем сообщение в зависимости от наличия данных
        if summa_sessions > 0:
            message_text = (
                f'Статистика пользователя: <b>{name}</b>\n\n'
                f'📅 Всего: {summa_hors:.2f} часов\n'
                f'💰 Заработано: {summa_money:.2f} руб\n\n'
                f'📋 Всего рабочих сессий: {summa_sessions}\n'
                f'💵 Ставка: 400 руб./час'
            )
        else:
            message_text = (
                f'📊 Статистика пользователя: {name}\n\n'
                f'📅 Всего: 0 часов\n'
                f'💰 Заработано: 0 руб\n\n'
                f'📋 Всего рабочих сессий: 0\n'
                f'💵 Ставка: 400 руб./час'
            )

        bot.edit_message_text(
            message_text,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            parse_mode="HTML"
        )

    # === ОБЩАЯ СТАТИСТИКА ===
    elif callback.data == "global_stats":
        # Получаем уникальных пользователей из базы
        cursor.execute("""SELECT DISTINCT user_id, name FROM work""")
        all_users = cursor.fetchall()

        if not all_users:
            bot.edit_message_text("📊 <b>Общая статистика:</b>\n\nНет данных о пользователях",
                                  chat_id=callback.message.chat.id,
                                  message_id=callback.message.message_id)
            return

        message_info = "📊 <b>Общая статистика:</b>\n\n"

        # Для каждого пользователя считаем статистику отдельно
        for user_id, user_name in all_users:
            cursor.execute("""SELECT * FROM work WHERE user_id = ?""", (user_id,))
            user_records = cursor.fetchall()

            summa_sessions = 0
            summa_hors = 0
            summa_money = 0

            for record in user_records:
                if record[5] is not None:
                    summa_sessions += 1
                    summa_hors += round(record[5] or 0, 2)
                    summa_money += round(record[6] or 0, 2)

            # Округляем значения
            summa_hors = round(summa_hors, 2)
            summa_money = round(summa_money, 2)

            # Добавляем статистику пользователя в общее сообщение
            message_info += (
                f"👤 <b>{user_name}</b>:\n"
                f"   📅 Всего: {summa_hors:.2f} ч.\n"
                f"   💰 Зарплата: {summa_money:.2f} руб.\n"
                f"   📋 Всего рабочих сессий: {summa_sessions}\n"
                f"   💵 Ставка: 400 руб./час\n\n"
            )

        bot.edit_message_text(
            message_info,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            parse_mode="HTML"
        )

    # === ПОДТВЕРЖДЕНИЕ ОЧИСТКИ ВСЕЙ БАЗЫ ===
    elif callback.data == "clear_yes":
        # 1. Удаляем все записи из таблицы
        cursor.execute("DELETE FROM work")
        dp.commit()

        # 2. Удаляем саму таблицу
        cursor.execute("DROP TABLE IF EXISTS work")

        # 3. Создаем таблицу заново
        cursor.execute("""CREATE TABLE IF NOT EXISTS work (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            start_time TEXT,
            end_time TEXT,
            hours REAL,
            many REAL,
            workout_date TEXT DEFAULT (DATETIME('now', 'localtime'))
        )""")
        dp.commit()

        # Сообщаем об успешной очистке
        bot.edit_message_text("✅ <b>База данных полностью очищена!</b> Все данные удалены.",
                              chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              parse_mode="HTML")

    # === ОТМЕНА ОЧИСТКИ БАЗЫ ===
    elif callback.data == 'clear_no':
        bot.edit_message_text("❌ <b>Очистка базы данных отменена.</b>",
                              chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              parse_mode="HTML")

    # === ОТМЕНА УДАЛЕНИЯ ПОЛЬЗОВАТЕЛЯ (КНОПКА ОТМЕНЫ) ===
    elif callback.data == 'dell_no':
        bot.edit_message_text("❌ <b>Действие отменено.</b>",
                              chat_id=callback.message.chat.id,
                              message_id=callback.message.message_id,
                              parse_mode="HTML")

    # === ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ КОНКРЕТНОГО ПОЛЬЗОВАТЕЛЯ ===
    elif callback.data.startswith('remove_yes_'):
        # Извлекаем ID пользователя из callback_data (формат: remove_yes_123456)
        user_id = int(callback.data.split('_')[2])

        # Удаляем все записи пользователя из базы
        cursor.execute("""DELETE FROM work WHERE user_id = ?""", (user_id,))
        dp.commit()

        # Сообщаем об успешном удалении
        bot.edit_message_text(
            f"✅ <b>Пользователь удален!</b>\n\n"
            f"ID: {user_id}\n"
            f"Все данные удалены из базы.",
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            parse_mode="HTML"
        )

    # === ОТМЕНА УДАЛЕНИЯ ПОЛЬЗОВАТЕЛЯ (КОНКРЕТНОГО) ===
    elif callback.data == 'cancel_remove':
        bot.edit_message_text(
            "❌ <b>Удаление отменено.</b>",
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            parse_mode="HTML"
        )


# Запуск бота в режиме опроса сервера Telegram
bot.polling()
