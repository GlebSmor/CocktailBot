import telebot
import requests
import json
from config import TOKEN
from telebot import types
from telebot.types import Message
from json.decoder import JSONDecodeError

bot = telebot.TeleBot(TOKEN)

try:
    # Проверка наличия/Иницилизация json-файла который выполняет функцию бд

    file_init = open('users.json', 'r')
except FileNotFoundError:
    with open('users.json', 'w', encoding='utf-8') as file_init:
        file_init.write('{}')


@bot.message_handler(commands=['start'])
def start(message: Message):
    # Функция start реагирует на команду /start
    # выводит описание бота, добавляет пользователя в бд, выводит меню кнопок.

    with open('users.json', 'r', encoding='utf-8') as file:
        data_from_json = json.load(file)

    user_id = message.from_user.id
    username = message.from_user.username

    if str(user_id) not in data_from_json:          # проверка наличия пользователя в бд
        data_from_json[user_id] = {'username': username}
        data_from_json[user_id]['history'] = []
        data_from_json[user_id]['cocktail'] = ''
        data_from_json[user_id]['ingredient_search'] = {}

    with open('users.json', 'w', encoding='utf-8') as file:
        json.dump(data_from_json, file, indent=4)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)    # вывод меню
    search = types.KeyboardButton('\U0001F50D Search')
    ingredient_search = types.KeyboardButton('\U0001F50D Search by ingredient')
    history = types.KeyboardButton('\U0001F553 History')
    random = types.KeyboardButton('\U0001F3B2 Random drink')
    markup.add(search, ingredient_search)
    markup.add(random, history)
    bot.send_message(chat_id=message.chat.id, text=f'Hello {message.from_user.first_name}!\n'
                                                   f'This is cocktail recipes bot.\n'
                                                   f'Here you can find recipes for your favorite cocktails\n\n\n'
                                                   f'Bot based on https://www.thecocktaildb.com',
                     reply_markup=markup)


@bot.message_handler(commands=['clear'])
def clear_history(message: Message):
    with open('users.json', 'r', encoding='utf-8') as file:
        data_from_json = json.load(file)
        data_from_json[str(message.from_user.id)]['history'] = []
    with open('users.json', 'w', encoding='utf-8') as file:
        json.dump(data_from_json, file, indent=4)

    bot.send_message(chat_id=message.chat.id, text='Search history cleared')


@bot.message_handler(commands=['help'])
def help_bot(message: Message):
    mess = 'Buttons:\n\n\n' \
           '\U0001F50D Search - Displays a list of cocktails matching the keyword\n\n' \
           '\U0001F50D Search by ingredient - Displays a list of cocktails matching the ingredient\n\n' \
           '\U0001F3B2 Random drink - Displays a random drink\n\n' \
           '\U0001F553 History - Displays the last five requests\n\n\n' \
           'Commands:\n\n\n' \
           '/start - Start bot and add your data to DataBase\n\n' \
           '/clear - Cleans search history\n\n' \
           '/help - Displays this message'
    bot.send_message(chat_id=message.chat.id, text=mess)


@bot.message_handler(content_types=['text'])
def search_drink(message: Message):
    # Функция поиска/вывода истории

    if message.text == '\U0001F50D Search':
        bot.send_message(chat_id=message.chat.id, text='Enter the cocktail name:')
        bot.register_next_step_handler(message, callback=search_drink_handle)

    elif message.text == '\U0001F50D Search by ingredient':
        bot.send_message(chat_id=message.chat.id, text='Enter the ingredient name:')
        bot.register_next_step_handler(message, callback=search_by_ingredient_handle)

    elif message.text == '\U0001F3B2 Random drink':
        response = json.loads(requests.get('https://www.thecocktaildb.com/api/json/v1/1/random.php').text)
        data = information_output(response['drinks'][0], message.from_user.id)

        bot.send_photo(message.chat.id, data[1], data[0])

    elif message.text == '\U0001F553 History':
        with open('users.json', 'r', encoding='utf-8') as file:
            data_from_json = json.load(file)
        history = data_from_json[str(message.from_user.id)]['history']
        if len(history) == 0:
            bot.send_message(chat_id=message.chat.id, text='History is empty')
        else:
            for elem in history:
                bot.send_photo(message.chat.id, elem[1], elem[0])


def search_by_ingredient_handle(message: Message):
    if message.text == '\U0001F50D Search' or message.text == '\U0001F553 History' \
            or message.text == '\U0001F3B2 Random drink' or message.text == '\U0001F50D Search by ingredient':
        search_drink(message)
    elif message.text.startswith('/'):
        commands_pick(message)
    else:
        mess = ''
        name = message.text

        try:    # проверка наличия коктейля
            response = json.loads(requests.get('https://www.thecocktaildb.com/api/json/v1/1/filter.php?i=' + name).text)
            with open('users.json', 'r', encoding='utf-8') as file:
                data_from_json = json.load(file)
            # создание списка коктейлей совпавших по ключ слову
            cocktails = [response['drinks'][x] for x in range(0, len(response['drinks']))]
            count = 0
            # вывод списка
            if data_from_json[str(message.from_user.id)]['ingredient_search'] != '':
                data_from_json[str(message.from_user.id)]['ingredient_search'].clear()
            for cocktail in cocktails:
                mess += f'{count + 1} - {cocktail["strDrink"]}\n'
                data_from_json[str(message.from_user.id)]['ingredient_search'][count] = cocktail["strDrink"]
                count += 1

            with open('users.json', 'w', encoding='utf-8') as file:
                json.dump(data_from_json, file, indent=4)

            bot.send_message(chat_id=message.chat.id, text=f'Pick cocktail number (1-{count}):')
            bot.send_message(chat_id=message.chat.id, text=mess)
            bot.register_next_step_handler(message, callback=pick_cocktail_by_ingredient_handle)

        except (TypeError, JSONDecodeError):  # обработка ошибок
            mess = 'No drinks found'
            bot.reply_to(message, text=mess)
            bot.register_next_step_handler(message, callback=search_by_ingredient_handle)


def pick_cocktail_by_ingredient_handle(message: Message):
    if message.text == '\U0001F50D Search' or message.text == '\U0001F553 History' \
            or message.text == '\U0001F3B2 Random drink' or message.text == '\U0001F50D Search by ingredient':
        search_drink(message)
    elif message.text.startswith('/'):
        commands_pick(message)
    else:
        with open('users.json', 'r', encoding='utf-8') as file:
            data_from_json = json.load(file)
            qty = len(data_from_json[str(message.from_user.id)]['ingredient_search'])
        # проверка ввода
        if message.text.isdigit() and 1 <= int(message.text) <= qty:
            name = data_from_json[str(message.from_user.id)]['ingredient_search'][str(int(message.text) - 1)]
            cocktail = json.loads(requests.get('https://www.thecocktaildb.com/api/json/v1/1/search.php?s=' + name).text)
            data = information_output(cocktail['drinks'][0], message.from_user.id)
            data_from_json[str(message.from_user.id)]['ingredient_search'].clear()
            # вывод изображения
            bot.send_photo(message.chat.id, data[1], data[0])
            bot.register_next_step_handler(message, callback=pick_cocktail_by_ingredient_handle)

        else:  # обработка ошибки ввода
            mess = 'Input error'
            bot.send_message(chat_id=message.chat.id, text=mess)
            bot.register_next_step_handler(message, callback=pick_cocktail_by_ingredient_handle)


def search_drink_handle(message: Message):
    # Функция search_drink_handle выводит список коктейлей по ключевому слову
    if message.text == '\U0001F50D Search' or message.text == '\U0001F553 History' \
            or message.text == '\U0001F3B2 Random drink' or message.text == '\U0001F50D Search by ingredient':
        search_drink(message)
    elif message.text.startswith('/'):
        commands_pick(message)
    else:
        mess = ''
        name = message.text
        # запрос к api
        response = json.loads(requests.get('https://www.thecocktaildb.com/api/json/v1/1/search.php?s=' + name).text)
        try:    # проверка наличия коктейля

            # создание списка коктейлей совпавших по ключ слову
            cocktails = [response['drinks'][x] for x in range(0, len(response['drinks']))]
            count = 0
            # вывод списка
            for cocktail in cocktails:
                mess += f'{count + 1} - {cocktail["strDrink"]}\n'
                count += 1
            # загрузка поиска в бд
            with open('users.json', 'r', encoding='utf-8') as file:
                data_from_json = json.load(file)
                data_from_json[str(message.from_user.id)]['cocktail'] = name + '-' + str(count)
            with open('users.json', 'w', encoding='utf-8') as file:
                json.dump(data_from_json, file, indent=4)

            # вывод сообщений
            bot.send_message(chat_id=message.chat.id, text=f'Pick cocktail number (1-{count}):')
            bot.send_message(chat_id=message.chat.id, text=mess)
            bot.register_next_step_handler(message, callback=pick_cocktail_handle)
        except TypeError:   # обработка ошибки
            mess = 'No drinks found'
            bot.reply_to(message, text=mess)
            bot.register_next_step_handler(message, callback=search_drink_handle)


def pick_cocktail_handle(message: Message):
    # Функция pick_cocktail_handle выводит название, ингредиенты, инструкцию и фото выбранного коктейля

    if message.text == '\U0001F50D Search' or message.text == '\U0001F553 History' \
            or message.text == '\U0001F3B2 Random drink' or message.text == '\U0001F50D Search by ingredient':
        search_drink(message)

    elif message.text.startswith('/'):
        commands_pick(message)

    else:
        # выгрузка ключ слова и кол-ва напитков из бд
        with open('users.json', 'r', encoding='utf-8') as file:
            data_from_json = json.load(file)
            name, qty = data_from_json[str(message.from_user.id)]['cocktail'].split('-')
            qty = int(qty)

        if message.text.isdigit() and 1 <= int(message.text) <= qty:    # проверка сообщения
            # повторный api запрос и создание списка коктейлей
            response = json.loads(requests.get('https://www.thecocktaildb.com/api/json/v1/1/search.php?s=' + name).text)
            cocktails = [response['drinks'][x] for x in range(0, len(response['drinks']))]
            # запись выбранного напитка
            cocktail = cocktails[int(message.text) - 1]
            data = information_output(cocktail, message.from_user.id)
            # вывод изображения
            bot.send_photo(message.chat.id, data[1], data[0])
            bot.register_next_step_handler(message, callback=pick_cocktail_handle)

        else:   # обработка ошибки ввода
            mess = 'Input error'
            bot.send_message(chat_id=message.chat.id, text=mess)
            bot.register_next_step_handler(message, callback=pick_cocktail_handle)


def information_output(cocktail: dict, user_id: int):
    mess = ''
    count = 0
    mess += f'Name: {cocktail["strDrink"]} \U0001F379\n'
    if cocktail["strAlcoholic"] == 'Alcoholic':
        mess += '\nAlcoholic: Yes'
    else:
        mess += '\nAlcoholic: No'
    mess += '\n\nIngredients \U0001F6D2\n\n'

    # запись ингредиентов
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
    with open('users.json', 'r', encoding='utf-8') as file:
        data_from_json = json.load(file)
    history = data_from_json[str(user_id)]['history']

    if len(history) == 5:
        history.pop(0)
    history.append((mess, cocktail['strDrinkThumb']))

    with open('users.json', 'w', encoding='utf-8') as file:
        json.dump(data_from_json, file, indent=4)
    image = cocktail['strDrinkThumb']
    return mess, image


def commands_pick(message: Message):
    if message.text == '/clear':
        clear_history(message)
    elif message.text == '/help':
        help_bot(message)
    else:
        bot.send_message(chat_id=message.chat.id, text='Input error')


bot.polling()
