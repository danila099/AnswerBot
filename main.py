import telebot
from telebot import types
from telebot.types import Message
import sqlite3

bot = telebot.TeleBot("")

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY,
        question TEXT,
        answer TEXT,
        username TEXT,
        first_name TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        chatid INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        second_name TEXT,
        isadmin BOOLEAN
    )
''')

conn.commit()
conn.close()

@bot.message_handler(commands=['start'])
def start(message):
    with sqlite3.connect('users.db') as conn:
        conn.execute('INSERT INTO users (chatid, username, first_name,second_name, isadmin) VALUES (?, ?, ?, ?, ?)', (message.chat.id, message.from_user.username, message.from_user.first_name, message.from_user.last_name, False))
    bot.send_message(message.chat.id, 'Добро пожаловать пользователь в бота по задаванию вопросов. Напишите /help, чтобы узнать, что я умею!')

@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, f'Я умею задавать вопросы. Напишите /question, чтобы задать вопрос \n /show, чтобы увидеть ваши вопросы и ответ на него')

@bot.message_handler(commands=['question'])
def question(message):
    bot.send_message(message.chat.id, 'Какой вопрос вы хотите задать?')
    bot.register_next_step_handler(message, ask_question)

def ask_question(message):
    question_text = message.text
    id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO questions (id, question, username, first_name) VALUES (?, ?, ?, ?)', (id, question_text, username, first_name))
    conn.commit()
    conn.close()
    adminchatids = getadminchatids()
    for adminchatid in adminchatids:
        bot.send_message(adminchatid, f'Новый вопрос от пользователя {username}: {question_text}')
    bot.send_message(message.chat.id, 'Вопрос успешно отправлен, наш администратор ответит вам в ближайшее время!')

@bot.message_handler(commands=['answer'])
def answer(message):
    if message.chat.id in getadminchatids():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM questions')
        user_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        buttons = [types.KeyboardButton(str(user_id)) for user_id in user_ids]
        markup.add(*buttons)
        bot.send_message(message.chat.id, 'Выберите пользователя:', reply_markup=markup)
        bot.register_next_step_handler(message, answer_question)
    else:
        bot.send_message(message.chat.id, 'У вас нет прав на выполнение этой команды')

def answer_question(message, markup=None):
    user_id = message.text
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT question, answer FROM questions WHERE id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        question, answer = result
        bot.send_message(message.chat.id, f'Вопрос: {question}\nОтвет: {answer}')
    else:
        bot.send_message(message.chat.id, 'Вопрос не найден.')

    bot.send_message(message.chat.id, 'Введите ответ на вопрос:')
    bot.register_next_step_handler(message, lambda msg: send_answer(msg, user_id))
    
def send_answer(message, id):
    answer_text = message.text
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE questions SET answer = ? WHERE id = ?', (answer_text, id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, 'Ответ успешно отправлен!')
    
def getadminchatids() -> list:
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT chatid FROM users WHERE isadmin = 1')
        adminchatids = [row[0] for row in cursor.fetchall()]
    return adminchatids

@bot.message_handler(commands=['show'])
def show(message):
    try:
        id = message.from_user.id
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM questions WHERE id = ?', (id,))
        questions = cursor.fetchall()
        if questions:
            for question in questions:
                bot.send_message(
                    message.chat.id, 
                    f'Вопрос: {question[1]}\nОтвет: {question[2]}'
                )
        else:
            bot.send_message(message.chat.id, 'У вас нет сохранённых вопросов')
        conn.close()
    except Exception as e:
        bot.send_message(message.chat.id, f'Произошла ошибка: {e}')

def add_admin(message):
    username = message.text[1:]
    with sqlite3.connect('users.db') as conn:
        cur = conn.execute("SELECT chatid FROM users WHERE username = ?", (username,))
        if (cur.fetchone() is None):
            bot.send_message(message.chat.id, 'Пользователь не найден')
        else:
            conn.execute('UPDATE users SET isadmin = 1 WHERE username = ?', (username,))
            bot.send_message(message.chat.id, 'Пользователь успешно назначен администратором!')
        
@bot.message_handler(commands=['admins'])
def admins(message):
    if message.chat.id in getadminchatids():
        markup = types.InlineKeyboardMarkup(row_width=2)
        with sqlite3.connect('users.db') as conn:
            for chatid in getadminchatids():
                username = conn.execute('SELECT username FROM users WHERE chatid = ?', (chatid,)).fetchone()[0]
                buttons = types.InlineKeyboardButton(username, callback_data=f'admin_{chatid}')
                markup.add(buttons)
        bot.send_message(message.chat.id, 'Список администраторов:', reply_markup=markup)
    else:
        bot.send_message(message.chat.id, 'У вас нет прав на выполнение этой команды')
@bot.message_handler(commands=['addadmin'])
def addadmin(message):
    if message.chat.id in getadminchatids():
        bot.send_message(message.chat.id, 'Введите username пользователя, которого хотите назначить администратором:')
        bot.register_next_step_handler(message, add_admin)
    else:
        bot.send_message(message.chat.id, 'У вас нет прав на выполнение этой команды')
        
@bot.message_handler(commands=['givemeadmin'])
def givemeadmin(message):
    with sqlite3.connect('users.db') as conn:
        conn.execute('UPDATE users SET isadmin = 1 WHERE chatid = ?', (message.chat.id,))
    bot.send_message(message.chat.id, 'Вы получили права администратора!')
    
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callback(call):
    chatid = call.data.split('_')[1]
    markup = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton('Да', callback_data=f'delete_{chatid}_Y'),
        types.InlineKeyboardButton('Нет', callback_data=f'delete_{chatid}_N')
    ]
    markup.add(*buttons)
    bot.send_message(call.message.chat.id, 'Вы уверены, что хотите удалить этого администратора?', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_'))
def delete_admin_callback(call):
    text = call.data.split('_')
    if text[2] == 'N':
        bot.send_message(call.message.chat.id, 'Отменено.')
    else:
        chatid = text[1]
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute(f'UPDATE users SET isadmin = 0 WHERE chatid = {chatid}')
        conn.commit()
        conn.close()
        bot.send_message(call.message.chat.id, 'Администратор успешно удалён!')
        
bot.polling(none_stop=True)
