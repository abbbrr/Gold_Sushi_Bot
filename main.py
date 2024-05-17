import telebot, datetime
from sets_data import sets, rest
from PIL import Image, ImageDraw, ImageFont
from telebot import types
import sqlite3
from requests.exceptions import ReadTimeout, ConnectionError
import time

TOKEN = '7058378528:AAFk9MP7hAclT34-JAz29ewI-icYntRzeqU'

sqlite_conn = sqlite3.connect('drinks.db')
sqlite_cursor = sqlite_conn.cursor()


bot = telebot.TeleBot(TOKEN)

selected_drink = {}
selected_product = {}

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    markup = types.ReplyKeyboardMarkup(row_width=3)
    item1 = types.KeyboardButton("Пробить заказ 🍕")
    item2 = types.KeyboardButton("Количество товаров и их наименование 📝")
    item3 = types.KeyboardButton("Добавить товар 📦")
    item4 = types.KeyboardButton("Общий счет за день 📈")
    item5 = types.KeyboardButton("Общий счет за месяц 🗓")
    item6 = types.KeyboardButton("Закрыть день 🚫")
    markup.add(item1, item2,item3,item4, item5,item6)

    today = datetime.date.today().strftime("%d.%m.%Y")
    bot.send_message(message.chat.id, f"Служба обслуживание для Gold Sushi🍣\n -----Сегодняшняя дата: {today} ----- \n Выберите действие:", reply_markup=markup)

# Component
@bot.message_handler(func=lambda message: message.text == "⬅️Назад")
def handle_back(message):
    handle_start(message)


@bot.message_handler(func=lambda message: message.text == "Общий счет за месяц 🗓")
def handle_total_month_sales(message):
    current_month_year = datetime.datetime.now().strftime("%B %Y")

    # Создание пустой белой фотографии
    width, height = 500, 1000  # Размеры фотографии
    color = (255, 255, 255)  # Белый цвет
    image = Image.new("RGB", (width, height), color)

    # Инициализация объекта рисования
    draw = ImageDraw.Draw(image)

    # Загрузка шрифта
    font = ImageFont.truetype("Roboto-Bold.ttf", size=10)

    # Добавление текста о текущем месяце и годе
    draw.text((10, 10), f"---------------------------------------------------Отчет за {current_month_year}------------------------------------------------", fill="black", font=font)

    # Получение данных из базы данных month.db
    conn = sqlite3.connect('month.db')
    cursor = conn.cursor()
    cursor.execute("SELECT date, earnings, costs, net_earnings FROM month_sales")
    sales_data = cursor.fetchall()
    conn.close()

    # Добавление текста о продажах за месяц на фотографию
    y_position = 30
    for sale in sales_data:
        sale_text = f"{sale[0]}: Прибыль: {sale[1]}, Себестоимость: {sale[2]}, Чистая прибыль: {sale[3]}"
        draw.text((10, y_position), sale_text, fill="black", font=font)
        y_position += 20

    # Сохранение фотографии с информацией о проданных товарах за месяц
    image.save("sales_month_report.png")

    # Отправка фотографии пользователю
    bot.send_photo(message.chat.id, open("sales_month_report.png", "rb"))

@bot.message_handler(commands=['clear_month'])
def handle_clear_month_data(message):
    conn = sqlite3.connect('month.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM month_sales")
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "Данные за текущий месяц успешно удалены.")

# Обработчик команды "Закрыть день 🚫"
@bot.message_handler(func=lambda message: message.text == "Закрыть день 🚫")
def close_day(message):
    # Подключение к базе данных SQLite для продаж
    sales_conn = sqlite3.connect('sales.db')
    sales_cursor = sales_conn.cursor()

    # Проверка наличия продаж
    sales_cursor.execute("SELECT COUNT(*) FROM sales")
    sales_count = sales_cursor.fetchone()[0]
    if sales_count == 0:
        bot.reply_to(message, "Пробейте заказ или вы уже закрыли день.")
        sales_conn.close()
        return

    total_earnings = 0
    total_costs = 0

    # Получение информации о проданных товарах за день из базы данных
    sales_cursor.execute("SELECT item_name, type, quantity, total_price FROM sales")
    sales = sales_cursor.fetchall()
    for sale in sales:
        item_name, type, quantity, total_price = sale
        if type == "set":
            set_info = next((s for s in sets if s["name"] == item_name), None)
            if set_info:
                total_earnings += total_price  # Учитываем выручку от продажи сета
                total_costs += set_info["cost_price"]  # Учитываем себестоимость сета
        elif type == "rest":
            rest_info = next((r for r in rest if r["name"] == item_name), None)
            if rest_info:
                total_earnings += total_price  # Учитываем выручку от продажи остального товара
                total_costs += rest_info["cost_price"]  # Учитываем себестоимость остального товара
        elif type == "drink":
            # Подключение к базе данных SQLite для напитков
            drinks_conn = sqlite3.connect('drinks.db')
            drinks_cursor = drinks_conn.cursor()
            drinks_cursor.execute("SELECT cost FROM drinks WHERE drink=?", (item_name,))
            drink_info = drinks_cursor.fetchone()
            drinks_conn.close()

            if drink_info:
                drink_cost = drink_info[0]  # Получаем стоимость напитка из базы данных
                total_costs += drink_cost * quantity  # Рассчитываем себестоимость напитка
                total_earnings += 690 * quantity  # Рассчитываем прибыль от продажи напитка
            else:
                # Если информация о напитке не найдена в базе данных, используем дефолтную стоимость
                total_costs += quantity * 400  # Дефолтная себестоимость напитка
                total_earnings += quantity * 690  # Рассчитываем прибыль от продажи напитка

    # Вычисление чистой прибыли за день
    net_earnings = total_earnings - total_costs

    # Текущая дата
    current_date = datetime.datetime.now().strftime("%d.%m.%Y")

    # Формирование строки для записи в базу данных и вывода пользователю
    sales_summary = f"{current_date}, Прибыль: {total_earnings} тг, Себестоимость: {total_costs} тг, Чистая: {net_earnings} тг"

    # Создание записи для сохранения в таблицу month_sales
    day_summary = (current_date, total_earnings, total_costs, net_earnings)

    # Подключение к базе данных SQLite для month_sales
    month_conn = sqlite3.connect('month.db')
    month_cursor = month_conn.cursor()
    month_cursor.execute("INSERT INTO month_sales (date, earnings, costs, net_earnings) VALUES (?, ?, ?, ?)", day_summary)
    month_conn.commit()
    month_conn.close()

    # Удаление всех записей о продажах за день
    sales_cursor.execute("DELETE FROM sales")
    sales_conn.commit()

    sales_conn.close()

    bot.reply_to(message, f"День успешно закрыт. Сохранена информация: \n{sales_summary}")

@bot.message_handler(func=lambda message: message.text == "Общий счет за день 📈")
def handle_total_sales(message):
    total_price = 0
    total_cost = 0
    current_date = datetime.datetime.now().strftime("----------------------------%d.%m.%Y--------------------------")
    sales_text = f"{current_date}\n-----------------------Общий чек за день---------------------\n\n"

    # Подключение к базам данных SQLite
    sales_conn = sqlite3.connect('sales.db')
    drinks_conn = sqlite3.connect('drinks.db')
    products_conn = sqlite3.connect('products.db')

    sales_cursor = sales_conn.cursor()
    drinks_cursor = drinks_conn.cursor()
    products_cursor = products_conn.cursor()

    sold_sets = {}
    sold_rests = {}

    # Получение информации о проданных товарах из базы данных
    sales_cursor.execute("SELECT item_name, type, quantity FROM sales")
    sales = sales_cursor.fetchall()

    for sale in sales:
        item_name, sale_type, quantity = sale
        if sale_type == "set":
            set_info = next((s for s in sets if s["name"] == item_name), None)
            if set_info:
                # total_price += set_info["price"]
                # total_cost += set_info["cost_price"]
                total_price += set_info["price"] * quantity
                total_cost += set_info["cost_price"] * quantity
                if item_name in sold_sets:
                    sold_sets[item_name] += quantity
                else:
                    sold_sets[item_name] = quantity
                sales_text += f"{item_name} (Сет): {set_info['price']} тг. (Себестоимость: {set_info['cost_price']} тг.) x{quantity}\n"
        elif sale_type == "rest":
            rest_info = next((r for r in rest if r["name"] == item_name), None)
            if rest_info:
                # total_price += rest_info["price"]
                # total_cost += rest_info["cost_price"]
                total_price += rest_info["price"] * quantity
                total_cost += rest_info["cost_price"] * quantity
                if item_name in sold_rests:
                    sold_rests[item_name] += quantity
                else:
                    sold_rests[item_name] = quantity
                sales_text += f"{item_name} (Остальное): {rest_info['price']} тг. (Себестоимость: {rest_info['cost_price']} тг.) x{quantity}\n"
        elif sale_type == "drink":
            drinks_cursor.execute("SELECT cost FROM drinks WHERE drink=?", (item_name,))
            drink_info = drinks_cursor.fetchone()
            if drink_info:
                drink_cost = drink_info[0]
                total_cost += drink_cost * quantity
                total_price += 690 * quantity
                sales_text += f"{item_name} (Напиток x{quantity}): {690 * quantity} тг.\n"
            else:
                total_cost += 500 * quantity
                total_price += 690 * quantity
                sales_text += f"{item_name} (Напиток x{quantity}): {690 * quantity} тг.\n"
        elif sale_type == "product":
            products_cursor.execute("SELECT cost FROM products WHERE product=?", (item_name,))
            product_info = products_cursor.fetchone()
            if product_info:
                product_cost = product_info[0]
                total_cost += product_cost * quantity
                total_price += 500 * quantity  # Можно установить фиксированную цену или добавить цену продукта в базу данных
                sales_text += f"{item_name} (Продукт x{quantity}): {500 * quantity} тг.\n"

    sales_conn.close()
    drinks_conn.close()
    products_conn.close()

    profit = total_price - total_cost
    sales_text += f"-----------------------------------------------------------\n"
    sales_text += f"Общая сумма всех проданных товаров: {total_price} тг.\n"
    sales_text += f"Общая себестоимость всех проданных товаров: {total_cost} тг.\n"
    sales_text += f"Прибыль: {profit} тг.\n"

    # Создание пустой белой фотографии
    width, height = 500, 1000  # Размеры фотографии
    color = (255, 255, 255)  # Белый цвет
    image = Image.new("RGB", (width, height), color)

    # Инициализация объекта рисования
    draw = ImageDraw.Draw(image)

    # Загрузка шрифта
    font = ImageFont.truetype("Roboto-Bold.ttf", size=15)

    # Добавление текста о проданных товарах на фотографию
    draw.text((10, 10), sales_text, fill="black", font=font)

    # Сохранение фотографии с информацией о проданных товарах
    image.save("sales_report.png")

    # Отправка фотографии пользователю
    bot.send_photo(message.chat.id, open("sales_report.png", "rb"))

# Пробитие заказов
@bot.message_handler(func=lambda message: message.text == "Пробить заказ 🍕")
def punch_order_product(message):
    markup = types.ReplyKeyboardMarkup(row_width=3)
    item1 = types.KeyboardButton("⬅️Назад")
    item2 = types.KeyboardButton("Бар ☕️")
    item3 = types.KeyboardButton("Кухня 🍔")
    markup.add(item1, item2, item3)
    bot.send_message(message.chat.id, "Выберите категорию для пробитие заказа:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Кухня 🍔")
def handle_order_category(message):
    markup = types.ReplyKeyboardMarkup(row_width=3)

    item1 = types.KeyboardButton("⬅️Назад")
    item2 = types.KeyboardButton("Сеты️ 🍱")
    item3 = types.KeyboardButton("Остальное 🍟")
    markup.add(item1, item2, item3)
    bot.send_message(message.chat.id, "Выберите категорию:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "Сеты️ 🍱")
def handle_sets_category(message):
    category = message.text

    markup = types.InlineKeyboardMarkup(row_width=1)

    for set_data in sets:
        button_text = f"{set_data['name']} - {set_data['price']} тг"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"quantity_{set_data['name']}"))

    bot.send_message(message.chat.id, f"Выберите сет из категории '{category}':", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "Остальное 🍟")
def handle_sets_category(message):
    category = message.text

    markup = types.InlineKeyboardMarkup(row_width=1)

    for rest_data in rest:
        button_text = f"{rest_data['name']} - {rest_data['price']} тг"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"quantity_{rest_data['name']}"))

    bot.send_message(message.chat.id, f"Выберите что-то из категории '{category}':", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text in ["Бар ☕️"])
def handle_order_category(message):
    category = message.text

    # Подключение к базе данных SQLite для напитков
    drinks_conn = sqlite3.connect('drinks.db')
    drinks_cursor = drinks_conn.cursor()

    # Получаем все напитки из таблицы drinks
    drinks_cursor.execute("SELECT drink FROM drinks")
    drinks = drinks_cursor.fetchall()

    # Создание разметки для кнопок
    markup = types.InlineKeyboardMarkup(row_width=2)
    for drink in drinks:
        # drink - это кортеж, содержащий только один элемент (название напитка)
        markup.add(types.InlineKeyboardButton(drink[0], callback_data=f"quantity_{drink[0]}"))

    # Закрываем соединение с базой данных для напитков
    drinks_conn.close()

    bot.send_message(message.chat.id, f"Выберите напиток из категории '{category}':", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("quantity_"))
def handle_quantity(call):
    item_name = call.data.split("_")[1]

    # Подключение к базе данных SQLite для напитков
    drinks_conn = sqlite3.connect('drinks.db')
    drinks_cursor = drinks_conn.cursor()

    # Проверяем, является ли товар напитком
    drinks_cursor.execute("SELECT * FROM drinks WHERE drink=?", (item_name,))
    existing_drink = drinks_cursor.fetchone()

    if existing_drink:
        bot.send_message(call.message.chat.id, f"Напишите количество {item_name} в цифрах:")
        bot.register_next_step_handler(call.message, lambda message: update_quantity(message, item_name, is_drink=True))
        drinks_conn.close()
        return

    drinks_conn.close()

    # Подключение к базе данных SQLite для продуктов
    products_conn = sqlite3.connect('products.db')
    products_cursor = products_conn.cursor()

    # Проверяем, является ли товар продуктом
    products_cursor.execute("SELECT * FROM products WHERE product=?", (item_name,))
    existing_product = products_cursor.fetchone()

    if existing_product:
        bot.send_message(call.message.chat.id, f"Напишите количество {item_name} в цифрах:")
        bot.register_next_step_handler(call.message,
                                       lambda message: update_quantity(message, item_name, is_drink=False))
        products_conn.close()
        return

    products_conn.close()

    # Проверка на наличие сета
    selected_set = next((s for s in sets if s["name"] == item_name), None)
    if selected_set:
        bot.send_message(call.message.chat.id, f"Напишите количество {item_name} в цифрах:")
        bot.register_next_step_handler(call.message, lambda message: update_quantity(message, item_name, is_set=True))
        return

    selected_rest = next((r for r in rest if r["name"] == item_name), None)
    if selected_rest:
        bot.send_message(call.message.chat.id, f"Напишите количество {item_name} в цифрах:")
        bot.register_next_step_handler(call.message, lambda message: update_quantity(message, item_name, is_rest = True))

    # Если товар не является напитком, продуктом или сетом, обработка ошибки
    bot.send_message(call.message.chat.id, "Произошла ошибка. Пожалуйста, попробуйте еще раз.")


def update_quantity(message, item_name, is_drink=False, is_set=False, is_rest=False):
    try:
        quantity = int(message.text)
        if is_drink:
            # Подключение к базе данных SQLite для напитков
            drinks_conn = sqlite3.connect('drinks.db')
            drinks_cursor = drinks_conn.cursor()

            # Проверяем, существует ли такой напиток в базе данных
            drinks_cursor.execute("SELECT quantity, cost FROM drinks WHERE drink=?", (item_name,))
            drink = drinks_cursor.fetchone()
            if drink:
                current_quantity, unit_price = drink
                if current_quantity >= quantity:
                    new_quantity = current_quantity - quantity
                    drinks_cursor.execute("UPDATE drinks SET quantity=? WHERE drink=?", (new_quantity, item_name))

                    # Расчет общей цены
                    total_price = quantity * unit_price

                    # Добавляем запись о продаже в таблицу "sales"
                    sales_conn = sqlite3.connect('sales.db')
                    sales_cursor = sales_conn.cursor()
                    sales_cursor.execute("INSERT INTO sales (item_name, type, quantity, total_price) VALUES (?, ?, ?, ?)",
                                         (item_name, "drink", quantity, total_price))
                    sales_conn.commit()
                    sales_conn.close()

                    drinks_conn.commit()
                    bot.send_message(message.chat.id, f"Успешно отнято {quantity} '{item_name}'.")
                    handle_start(message)
                else:
                    bot.send_message(message.chat.id,
                                     f"Недостаточно товара '{item_name}'. Доступное количество: {current_quantity}.")
            else:
                bot.send_message(message.chat.id, f"Напиток '{item_name}' не найден в базе данных.")

            drinks_conn.close()

        elif is_set:
            # Проверяем наличие всех необходимых продуктов для сета
            selected_set = next((s for s in sets if s["name"] == item_name), None)
            if selected_set:
                enough_products = True
                missing_product = None
                for ingredient in selected_set["ingredients"]:
                    if ingredient["type"] == "product":
                        products_conn = sqlite3.connect('products.db')
                        products_cursor = products_conn.cursor()
                        products_cursor.execute("SELECT quantity FROM products WHERE product=?", (ingredient["name"],))
                        existing_product = products_cursor.fetchone()
                        if not existing_product or existing_product[0] < ingredient["quantity"] * quantity:
                            enough_products = False
                            missing_product = ingredient["name"]
                            break
                        products_conn.close()
                    elif ingredient["type"] == "drink":
                        drinks_conn = sqlite3.connect('drinks.db')
                        drinks_cursor = drinks_conn.cursor()
                        drinks_cursor.execute("SELECT quantity FROM drinks WHERE drink=?", (ingredient["name"],))
                        existing_drink = drinks_cursor.fetchone()
                        if not existing_drink or existing_drink[0] < ingredient["quantity"] * quantity:
                            enough_products = False
                            missing_product = ingredient["name"]
                            break
                        drinks_conn.close()

                if enough_products:
                    total_set_price = selected_set["price"] * quantity
                    for ingredient in selected_set["ingredients"]:
                        if ingredient["type"] == "drink":
                            # Обновляем количество проданного напитка
                            drinks_conn = sqlite3.connect('drinks.db')
                            drinks_cursor = drinks_conn.cursor()
                            drinks_cursor.execute("UPDATE drinks SET quantity=quantity-? WHERE drink=?",
                                                  (ingredient["quantity"] * quantity, ingredient["name"]))
                            drinks_conn.commit()
                            drinks_conn.close()
                        elif ingredient["type"] == "product":
                            # Обновляем количество проданного продукта
                            products_conn = sqlite3.connect('products.db')
                            products_cursor = products_conn.cursor()
                            products_cursor.execute("UPDATE products SET quantity=quantity-? WHERE product=?",
                                                    (ingredient["quantity"] * quantity, ingredient["name"]))
                            products_conn.commit()
                            products_conn.close()

                    # Создаем новую запись о продаже сета
                    sales_conn = sqlite3.connect('sales.db')
                    sales_cursor = sales_conn.cursor()
                    sales_cursor.execute("INSERT INTO sales (item_name, type, quantity, total_price) VALUES (?, ?, ?, ?)",
                                         (selected_set["name"], "set", quantity, total_set_price))
                    sales_conn.commit()
                    sales_conn.close()

                    bot.send_message(message.chat.id,
                                     f"Заказ на сет '{selected_set['name']}' успешно пробит. Цена: {total_set_price} тг.")
                    handle_start(message)
                else:
                    # Выводим сообщение о том, что не хватает продукта для приготовления сета
                    bot.send_message(message.chat.id,
                                     f"Не хватает продукта '{missing_product}' для приготовления сета '{selected_set['name']}'.")
            else:
                bot.send_message(message.chat.id, f"Сет '{item_name}' не найден в базе данных.")

        elif is_rest:
            selected_rest = next((r for r in rest if r["name"] == item_name), None)
            if selected_rest:
                enough_products = True
                missing_product = None
                for ingredient in selected_rest["ingredients"]:
                    if ingredient["type"] == "product":
                        products_conn = sqlite3.connect('products.db')
                        products_cursor = products_conn.cursor()
                        products_cursor.execute("SELECT quantity FROM products WHERE product=?", (ingredient["name"],))
                        existing_product = products_cursor.fetchone()
                        if not existing_product or existing_product[0] < ingredient["quantity"] * quantity:
                            enough_products = False
                            missing_product = ingredient["name"]
                            break
                        products_conn.close()

                if enough_products:
                    total_set_price = selected_rest["price"] * quantity
                    for ingredient in selected_rest["ingredients"]:
                        if  ingredient["type"] == "product":
                            # Обновляем количество проданного продукта
                            products_conn = sqlite3.connect('products.db')
                            products_cursor = products_conn.cursor()
                            products_cursor.execute("UPDATE products SET quantity=quantity-? WHERE product=?",
                                                    (ingredient["quantity"] * quantity, ingredient["name"]))
                            products_conn.commit()
                            products_conn.close()


                    # Создаем новую запись о продаже сета
                    sales_conn = sqlite3.connect('sales.db')
                    sales_cursor = sales_conn.cursor()
                    sales_cursor.execute(
                        "INSERT INTO sales (item_name, type, quantity, total_price) VALUES (?, ?, ?, ?)",
                        (selected_rest["name"], "rest", quantity, total_set_price))
                    sales_conn.commit()
                    sales_conn.close()

                    bot.send_message(message.chat.id,
                                     f"Заказ на сет '{selected_rest['name']}' успешно пробит. Цена: {total_set_price} тг.")
                    handle_start(message)
                else:
                    # Выводим сообщение о том, что не хватает продукта для приготовления сета
                    bot.send_message(message.chat.id,
                                     f"Не хватает продукта '{missing_product}' для приготовления сета '{selected_rest['name']}'.")
            else:
                bot.send_message(message.chat.id, f"Сет '{item_name}' не найден в базе данных.")


        else:
            # Подключение к базе данных SQLite для продуктов
            products_conn = sqlite3.connect('products.db')
            products_cursor = products_conn.cursor()

            # Проверяем, существует ли такой продукт в базе данных
            products_cursor.execute("SELECT quantity FROM products WHERE product=?", (item_name,))
            product = products_cursor.fetchone()
            if product:
                current_quantity = product[0]
                new_quantity = current_quantity - quantity
                products_cursor.execute("UPDATE products SET quantity=? WHERE product=?", (new_quantity, item_name))

                # Добавляем запись о продаже в таблицу "sales"
                sales_conn = sqlite3.connect('sales.db')
                sales_cursor = sales_conn.cursor()
                sales_cursor.execute("INSERT INTO sales (item_name, type, quantity) VALUES (?, ?, ?)",
                                     (item_name, "product", quantity))
                sales_conn.commit()
                sales_conn.close()

                products_conn.commit()
                bot.send_message(message.chat.id, f"Успешно отнято {quantity} '{item_name}'.")
                handle_start(message)
            else:
                bot.send_message(message.chat.id, f"Продукт '{item_name}' не найден в базе данных.")

            products_conn.close()

    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите число.")

# Обработчик кнопки "Количество товаров и их наименование"
@bot.message_handler(func=lambda message: message.text == "Количество товаров и их наименование 📝")
def handle_products_quantity(message):
    response = "Количество товаров и их наименование:\n"

    # Подключение к базе данных SQLite для напитков
    drinks_conn = sqlite3.connect('drinks.db')
    drinks_cursor = drinks_conn.cursor()

    # Получаем все напитки из таблицы drinks
    drinks_cursor.execute("SELECT drink, quantity FROM drinks")
    drinks = drinks_cursor.fetchall()

    response += "----------------------------------------------\nНапитки🧊:\n"
    for drink in drinks:
        response += f"{drink[0]}: {drink[1]}\n"

    # Закрываем соединение с базой данных для напитков
    drinks_conn.close()

    # Подключение к базе данных SQLite для продуктов
    products_conn = sqlite3.connect('products.db')
    products_cursor = products_conn.cursor()

    # Получаем все продукты из таблицы products
    products_cursor.execute("SELECT product, quantity FROM products")
    products = products_cursor.fetchall()

    response += "----------------------------------------------\nПродукты🍞:\n"
    for product in products:
        response += f"{product[0]}: {product[1]}гр.\n"

    # Закрываем соединение с базой данных для продуктов
    products_conn.close()

    bot.send_message(message.chat.id, response)


# Обработчик кнопки "Добавить товар"
@bot.message_handler(func=lambda message: message.text == "Добавить товар 📦")
def handle_add_product(message):
    markup = types.ReplyKeyboardMarkup(row_width=3)
    item1 = types.KeyboardButton("⬅️Назад")
    item2 = types.KeyboardButton("Напитки 🧊")
    item3 = types.KeyboardButton("Продукты 🍞")
    markup.add(item1, item2, item3)
    bot.send_message(message.chat.id, "Выберите категорию товара:", reply_markup=markup)

# Обработчик кнопки "Напитки 🧊"
@bot.message_handler(func=lambda message: message.text == "Напитки 🧊")
def handle_drinks(message):
    markup = types.ReplyKeyboardMarkup(row_width=3)
    item1 = types.KeyboardButton("Sprite")
    item2 = types.KeyboardButton("Fanta")
    item3 = types.KeyboardButton("Gorilla")
    item4 = types.KeyboardButton("Cola")
    item5 = types.KeyboardButton("Piala")
    item6 = types.KeyboardButton("Fuse Tea")
    markup.add(item1, item2, item3, item4, item5, item6)
    bot.send_message(message.chat.id, "Выберите напиток:", reply_markup=markup)

# Обработчик кнопки "Продукты 🍞"
@bot.message_handler(func=lambda message: message.text == "Продукты 🍞")
def handle_products(message):
    markup = types.ReplyKeyboardMarkup(row_width=5)
    item1 = types.KeyboardButton("Рис")
    item2 = types.KeyboardButton("Нори")
    item3 = types.KeyboardButton("Ласось")
    item4 = types.KeyboardButton("Твор Сыр")
    item5 = types.KeyboardButton("Угорь")
    item6 = types.KeyboardButton("Огурцы")
    item7 = types.KeyboardButton("Листья Салат")
    item8 = types.KeyboardButton("Майонез")
    item9 = types.KeyboardButton("Курица")
    item10 = types.KeyboardButton("Снеж Краб")
    item11 = types.KeyboardButton("Плавленный Сыр")
    item12 = types.KeyboardButton("Кунжут")
    item13 = types.KeyboardButton("Спайси")
    item14 = types.KeyboardButton("Сыр Моцарелла")
    item15 = types.KeyboardButton("Унаги Соус")
    item16 = types.KeyboardButton("Масаго")
    item17 = types.KeyboardButton("Крылышки")
    item18 = types.KeyboardButton("Фри")
    item19 = types.KeyboardButton("Тесто")
    item20 = types.KeyboardButton("Сыр")
    item21 = types.KeyboardButton("Пицца соус")
    item22 = types.KeyboardButton("Томато")
    item23 = types.KeyboardButton("Колбаса")
    item24 = types.KeyboardButton("Курица")
    item25 = types.KeyboardButton("Грибы")
    item26 = types.KeyboardButton("Краб")
    markup.add(item1, item2, item3, item4, item5, item6, item7, item8, item9, item10, item11, item12,item13, item14, item15, item16, item17, item18,item19,item20,item21,item22,item23, item24, item25,item26)
    bot.send_message(message.chat.id, "Выберите продукт:", reply_markup=markup)


# Обработчик выбора напитка
@bot.message_handler(func=lambda message: message.text in ["Sprite", "Fanta", "Gorilla", "Cola", "Piala", "Fuse Tea"])
def handle_selected_drink(message):
    drink_name = message.text
    user_id = message.chat.id

    selected_drink[user_id] = {"drink_name": drink_name}
    bot.send_message(message.chat.id, f"Напишите количество {drink_name} в цифрах:")

# Обработчик выбора продукта
@bot.message_handler(func=lambda message: message.text in ["Рис", "Нори", "Ласось", "Твор Сыр", "Угорь", "Огурцы", "Листья Салат", "Майонез", "Курица", "Снеж Краб", "Плавленный Сыр", "Кунжут", "Спайси", "Сыр Моцарелла", "Унаги Соус", "Масаго", "Крылышки", "Фри", "Тесто", "Сыр", "Пицца соус", "Томато", "Колбаса","Курица", "Грибы","Краб"])
def handle_selected_product(message):
    user_id = message.chat.id
    product_name = message.text

    selected_product[user_id] = {"product_name": product_name}
    bot.send_message(user_id, f"Напишите количество {product_name} в граммах:")
    bot.register_next_step_handler(message, handle_product_quantity)

def handle_product_quantity(message):
    user_id = message.chat.id
    product_name = selected_product[user_id]["product_name"]
    quantity_grams = message.text

    # Преобразовать количество в граммах в числовой формат
    try:
        quantity_grams = float(quantity_grams)
    except ValueError:
        bot.send_message(user_id, "Пожалуйста, введите корректное количество в граммах в числовом формате.")
        return

    # bot.send_message(user_id, f"Сохранено: {product_name}: {quantity_grams} гр.")
    sqlite_conn = sqlite3.connect('products.db')
    sqlite_cursor = sqlite_conn.cursor()

    # Проверяем, существует ли уже такой продукт в базе данных
    sqlite_cursor.execute("SELECT * FROM products WHERE user_id=? AND product=?", (user_id, product_name))
    existing_product = sqlite_cursor.fetchone()

    if existing_product:
        # Если продукт уже существует, обновляем его количество
        new_quantity = existing_product[2] + quantity_grams  # 2 - это индекс колонки quantity
        sqlite_cursor.execute("UPDATE products SET quantity=? WHERE user_id=? AND product=?",
                              (new_quantity, user_id, product_name))
    else:
        # Если продукта нет в базе данных, добавляем новую запись
        sqlite_cursor.execute("INSERT INTO products (user_id, product, quantity) VALUES (?, ?, ?)",
                              (user_id, product_name, quantity_grams))

    # Удаляем информацию о выбранном продукте
    del selected_product[user_id]

    bot.send_message(user_id, f"Сохранено: {product_name}: {quantity_grams} гр.")
    handle_start(message)

    # Закрываем соединение с базой данных SQLite
    sqlite_conn.commit()
    sqlite_conn.close()
    handle_start(message)

@bot.message_handler(commands=['clear_all_products'])
def clear_all_drinks(message):
    # Подключение к базе данных SQLite
    sqlite_conn = sqlite3.connect('products.db')
    sqlite_cursor = sqlite_conn.cursor()

    # Удаление всех записей из таблицы drinks
    sqlite_cursor.execute("DELETE FROM products")
    sqlite_conn.commit()
    sqlite_conn.close()

    bot.send_message(message.chat.id, "Все данные о продуктах были успешно удалены из базы данных.")


# Обработчик ввода количества напитка
@bot.message_handler(func=lambda message: message.chat.id in selected_drink and message.text.isdigit())
def handle_drink_quantity(message):
    user_id = message.chat.id
    drink_name = selected_drink[user_id]["drink_name"]
    quantity = message.text

    bot.send_message(user_id, "Введите стоимость напитка:")
    bot.register_next_step_handler(message, lambda m: save_drink_data(user_id, drink_name, quantity, m.text, message))

def save_drink_data(user_id, drink_name, quantity, cost, message):
    # Преобразуем количество и стоимость в числовой формат
    try:
        quantity = int(quantity)
        cost = float(cost)
    except ValueError:
        bot.send_message(user_id, "Пожалуйста, введите корректные данные.")
        return

    # Подключение к базе данных SQLite
    sqlite_conn = sqlite3.connect('drinks.db')
    sqlite_cursor = sqlite_conn.cursor()

    # Проверяем, существует ли уже такой напиток в базе данных
    sqlite_cursor.execute("SELECT * FROM drinks WHERE user_id=? AND drink=?", (user_id, drink_name))
    existing_drink = sqlite_cursor.fetchone()

    if existing_drink:
        # Если напиток уже существует, обновляем его количество
        new_quantity = existing_drink[3] + quantity  # 3 - это индекс колонки quantity
        sqlite_cursor.execute("UPDATE drinks SET quantity=? WHERE user_id=? AND drink=?",
                              (new_quantity, user_id, drink_name))
        sqlite_conn.commit()
        bot.send_message(user_id, f"Количество {drink_name} обновлено: {new_quantity} шт.")
    else:
        # Если напитка нет в базе данных, добавляем новую запись
        sqlite_cursor.execute("INSERT INTO drinks (user_id, drink, quantity, cost) VALUES (?, ?, ?, ?)",
                              (user_id, drink_name, quantity, cost))
        sqlite_conn.commit()
        bot.send_message(user_id, f"Сохранено: {drink_name}: {quantity} шт., стоимость: {cost} тг.")

    # Закрываем соединение с базой данных SQLite
    sqlite_conn.close()
    handle_start(message)


# Обработчик команды /clear_all_drinks
@bot.message_handler(commands=['clear_all_drinks'])
def clear_all_drinks(message):
    # Подключение к базе данных SQLite
    sqlite_conn = sqlite3.connect('drinks.db')
    sqlite_cursor = sqlite_conn.cursor()

    # Удаление всех записей из таблицы drinks
    sqlite_cursor.execute("DELETE FROM drinks")
    sqlite_conn.commit()
    sqlite_conn.close()

    bot.send_message(message.chat.id, "Все данные о напитках были успешно удалены из базы данных.")

# Запуск бота
def start_bot():
    while True:
        try:
            bot.polling(timeout=60, long_polling_timeout=60)
        except ReadTimeout:
            print("Read timeout occurred, retrying...")
            time.sleep(15)  # Wait before retrying
        except ConnectionError:
            print("Connection error occurred, retrying...")
            time.sleep(15)  # Wait before retrying
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            time.sleep(15)  # Wait before retrying

if __name__ == '__main__':
    start_bot()