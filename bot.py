import telebot
import requests
import json
from config import TOKEN
from telebot import types
from telebot.types import Message

bot = telebot.TeleBot(TOKEN)

try:
    # Проверка наличия/Иницилизация json-файла который выполняет функцию бд

    file_init = open('users.json', 'r')
except FileNotFoundError:
    with open('users.json', 'w') as file_init:
        file_init.write('{}')


@bot.message_handler(commands=['start'])
def start(message: Message):
    '''Функция start реагирует на команду /start
    выводит описание бота, добавляет пользователя в бд, выводит меню кнопок'''

    with open('users.json', 'r') as file:
        data_from_json = json.load(file)

    user_id = message.from_user.id
    username = message.from_user.username

    if str(user_id) not in data_from_json:          # проверка наличия пользователя в бд
        data_from_json[user_id] = {'username': username}
        data_from_json[user_id]['history'] = []
        data_from_json[user_id]['cocktail'] = ''

    with open('users.json', 'w') as file:
        json.dump(data_from_json, file, indent=4)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)    # вывод меню
    search = types.KeyboardButton('🔍Search')
    history = types.KeyboardButton('🕓History')
    markup.add(search, history)
    bot.send_message(chat_id=message.chat.id, text=f'Hello {message.from_user.first_name}!\n'
                                                   f'This is cocktail recipes bot.\n'
                                                   f'Here you can find recipes for your favorite cocktails\n\n\n'
                                                   f'Bot based on https://www.thecocktaildb.com',
                     reply_markup=markup)


def pick_cocktail_handle(message: Message):
    '''Функция pick_cocktail_handle выводит название, ингридиенты, инструкцию и фото выбраного коктейля'''

    mess = ''
    count = 0
    cocktail = None

    # выгрузка кл. слова и кол-ва напитков из бд
    with open('users.json', 'r') as file:
        data_from_json = json.load(file)
        name, qty = data_from_json[str(message.from_user.id)]['cocktail'].split('-')
        qty = int(qty)

    if message.text.isdigit() and 1 <= int(message.text) <= qty:    # проверка сообщения
        # повторный  api запрос и создание списка коктейлей
        response = json.loads(requests.get('https://www.thecocktaildb.com/api/json/v1/1/search.php?s=' + name).text)
        cocktails = [response['drinks'][x] for x in range(0, len(response['drinks']))]
        # запись выбранного напитка
        cocktail = cocktails[int(message.text) - 1]
        mess += f'Name: {cocktail["strDrink"]} \U0001F379\n'
        mess += '\n\nIngredients \U0001F6D2\n\n'

        # запись ингридиентов
        for ingredient in cocktail:
            if cocktail[ingredient] and 'strIngredient' in ingredient:
                count += 1
                if cocktail["strMeasure" + str(count)]:
                    mess += f'    {cocktail[ingredient]}: {cocktail["strMeasure" + str(count)]}\n'
                else:
                    mess += f'    {cocktail[ingredient]}\n'
        # запись инструкции
        instruction = cocktail['strInstructions'].split('.')

        mess += '\n\nInstruction \U0001F4DC\n\n'
        for string in range(0, len(instruction) - 1):
            instruction[string] = instruction[string].strip() + '.'
        mess += '\n'.join(instruction)

        # запись в историю запросов
        with open('users.json', 'r') as file:
            data_from_json = json.load(file)
        history = data_from_json[str(message.from_user.id)]['history']

        if len(history) == 5:
            history.pop(0)
        history.append((mess, cocktail['strDrinkThumb']))

        with open('users.json', 'w') as file:
            json.dump(data_from_json, file, indent=4)

    else:   # обработка ошибки ввода
        mess = 'Input error'
        bot.register_next_step_handler(message, callback=pick_cocktail_handle)
    # вывод сообщения
    bot.send_message(chat_id=message.chat.id, text=mess)

    # вывод изображения
    if cocktail['strDrinkThumb']:
        image = cocktail['strDrinkThumb']
        bot.send_photo(message.chat.id, image)


def search_drink_handle(message: Message):
    '''Функция search_drink_handle выводит список коктейлей по ключевому слову'''

    mess = ''
    name = message.text

    # запрос к api
    response = json.loads(requests.get('https://www.thecocktaildb.com/api/json/v1/1/search.php?s=' + name).text)

    try:    # проверка наличия коктейля
        # создание списка коктейлей совпавших по ключ. слову
        cocktails = [response['drinks'][x] for x in range(0, len(response['drinks']))]
        count = 0
        # вывод списка
        for cocktail in cocktails:
            mess += f'{count + 1} - {cocktail["strDrink"]}\n'
            count += 1
        # загрузка поиска в бд
        with open('users.json', 'r') as file:
            data_from_json = json.load(file)
            data_from_json[str(message.from_user.id)]['cocktail'] = name + '-' + str(count)
        with open('users.json', 'w') as file:
            json.dump(data_from_json, file, indent=4, ensure_ascii=False)

        # вывод соощений
        bot.send_message(chat_id=message.chat.id, text=f'Pick cocktail number (1-{count}):')
        bot.send_message(chat_id=message.chat.id, text=mess)
        bot.register_next_step_handler(message, callback=pick_cocktail_handle)
    except TypeError:   # обработка ошибки
        mess = 'No drinks found'
        bot.reply_to(message, text=mess)


@bot.message_handler(content_types=['text'])
def search_drink(message: Message):
    '''Функция поиска/вывода истории'''

    if message.text == '🔍Search':
        bot.send_message(chat_id=message.chat.id, text='Enter the cocktail name:')
        bot.register_next_step_handler(message, callback=search_drink_handle)

    elif message.text == '🕓History':
        with open('users.json', 'r') as file:
            data_from_json = json.load(file)
        history = data_from_json[str(message.from_user.id)]['history']
        for elem in history:
            bot.send_message(chat_id=message.chat.id, text=elem[0])
            bot.send_photo(message.chat.id, elem[1])


bot.polling()
