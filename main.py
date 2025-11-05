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

conn.commit()
conn.close()

@bot.message_handler(commands=['start'])
def start(message):
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

    bot.send_message(message.chat.id, 'Вопрос успешно отправлен, наш администратор ответит вам в ближайшее время!')

@bot.message_handler(commands=['answer'])
def answer(message):
    if message.chat.id == 5081151162:
        bot.send_message(message.chat.id, 'Выберите пользователя:')
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

bot.polling(none_stop=True)
