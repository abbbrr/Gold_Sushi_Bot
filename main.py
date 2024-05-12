import telebot, datetime
from sets_data import sets, rest
from PIL import Image, ImageDraw, ImageFont
from telebot import types
from pymongo import MongoClient

TOKEN = '7058378528:AAFk9MP7hAclT34-JAz29ewI-icYntRzeqU'
MONGODB_URI = 'mongodb://localhost:27018/'
DB_NAME = 'my-gold'

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]


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
    print("Продажа за месяц")


# Обработчик команды "Закрыть день 🚫"
@bot.message_handler(func=lambda message: message.text == "Закрыть день 🚫")
def close_day(message):
    if db.sales.count_documents({}) == 0:
        bot.reply_to(message, "Пробейте заказ или вы уже закрыли день.")
        return

    total_earnings = 0
    total_costs = 0

    # Получение информации о проданных товарах за день из базы данных
    sales = db.sales.find()
    for sale in sales:
        if sale["type"] == "set":
            total_earnings += sale["total_price"]
        elif sale["type"] == "drink":
            drink_info = db.drinks.find_one({"drink": sale['item_name']})
            if drink_info:
                drink_cost = drink_info["cost"]  # Получаем стоимость напитка из базы данных
                total_costs += drink_cost * sale["quantity"]  # Рассчитываем себестоимость напитка
                total_earnings += sale["quantity"] * 690  # Рассчитываем прибыль от продажи напитка
            else:
                # Если информация о напитке не найдена в базе данных, используем дефолтную стоимость
                total_costs += sale["quantity"] * 400  # Дефолтная себестоимость напитка
                total_earnings += sale["quantity"] * 690  # Рассчитываем прибыль от продажи напитка

    # Вычисление чистой прибыли за день
    net_earnings = total_earnings - total_costs

    # Текущая дата
    current_date = datetime.datetime.now().strftime("%d.%m.%Y")

    # Формирование строки для записи в базу данных и вывода пользователю
    sales_summary = f"{current_date}, Прибыль: {total_earnings} тг, Себестоимость: {total_costs} тг, Чистая: {net_earnings} тг"

    # Создание записи для сохранения в коллекцию month_sales
    day_summary = {
        "date": current_date,
        "earnings": total_earnings,
        "costs": total_costs,
        "net_earnings": net_earnings
    }

    # Сохранение данных в коллекцию month_sales
    db.month_sales.insert_one(day_summary)
    db.sales.delete_many({})

    bot.reply_to(message, f"День успешно закрыт. Сохранена информация: \n{sales_summary} ")



@bot.message_handler(func=lambda message: message.text == "Общий счет за день 📈")
def handle_total_sales(message):
    total_price = 0
    total_cost = 0
    current_date = datetime.datetime.now() .strftime("----------------------------%d.%m.%Y--------------------------")
    sales_text = f"{current_date}\n-----------------------Общий чек за день---------------------\n\n"

    # Получение информации о проданных товарах из базы данных
    sales = db.sales.find()
    for sale in sales:
        if sale["type"] == "set":
            set_info = next((s for s in sets if s["name"] == sale["item_name"]), None)
            if set_info:
                total_price += sale["total_price"]  # Используем цену сета из записи в базе данных
                # Добавляем информацию о продаже сета в чек
                sales_text += f"{sale['item_name']} (Сет): {sale['total_price']} тг. (Себестоимость: {set_info['cost_price']} тг.)\n"
                # Вычитаем себестоимость сета из общей себестоимости
                total_cost += set_info["cost_price"]
        elif sale["type"] == "drink":
            drink_info = db.drinks.find_one(
                {"drink": sale['item_name']})  # Получаем информацию о напитке из базы данных
            if drink_info:
                drink_cost = drink_info["cost"]  # Получаем стоимость напитка из базы данных
                total_cost += drink_cost * sale["quantity"]  # Рассчитываем себестоимость напитка
                total_price += 690 * sale["quantity"]  # Рассчитываем цену напитка по фиксированной цене продажи
                sales_text += f"{sale['item_name']} (Напиток x{sale['quantity']}): {690 * sale['quantity']} тг.\n"
            else:
                # Если информация о напитке не найдена в базе данных, используем дефолтную стоимость
                total_cost += sale["quantity"] * 500  # Дефолтная себестоимость напитка
                total_price += 690 * sale["quantity"]  # Рассчитываем цену напитка по фиксированной цене продажи
                sales_text += f"{sale['item_name']} (Напиток x{sale['quantity']}): {690 * sale['quantity']} тг.\n"
        elif sale["type"] == "rest":
            rest_info = next((r for r in rest if r["name"] == sale["item_name"]), None)
            if rest_info:
                total_price += sale["total_price"]  # Используем цену сета из записи в базе данных
                # Добавляем информацию о продаже сета в чек
                sales_text += f"{sale['item_name']} (Остальное): {sale['total_price']} тг. (Себестоимость: {rest_info['cost_price']} тг.)\n"
                # Вычитаем себестоимость сета из общей себестоимости
                total_cost += rest_info["cost_price"]

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

    drinks = db.drinks.find()

    markup = types.InlineKeyboardMarkup(row_width=2)
    for drink in drinks:
        markup.add(types.InlineKeyboardButton(drink['drink'], callback_data=f"quantity_{drink['drink']}"))

    bot.send_message(message.chat.id, f"Выберите напиток из категории '{category}':", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("quantity_"))
def handle_quantity(call):
    item_name = call.data.split("_")[1]

    # Проверяем, является ли товар напитком
    existing_drink = db.drinks.find_one({"drink": item_name})
    if existing_drink:
        bot.send_message(call.message.chat.id, f"Напишите количество {item_name} в цифрах:")
        bot.register_next_step_handler(call.message, lambda message: update_quantity(message, item_name, is_drink=True))
        return

    # Проверяем, является ли товар продуктом
    existing_product = db.products.find_one({"product": item_name})
    if existing_product:
        bot.send_message(call.message.chat.id, f"Напишите количество {item_name} в цифрах:")
        bot.register_next_step_handler(call.message, lambda message: update_quantity(message, item_name, is_drink=False))
        return

    # Проверяем, является ли товар сетом
    selected_set = next((s for s in sets if s["name"] == item_name), None)
    if selected_set:
        # Проверяем наличие всех необходимых продуктов для сета
        enough_products = True
        missing_product = None
        for ingredient in selected_set["ingredients"]:
            if ingredient["type"] == "product":
                existing_product = db.products.find_one({"product": ingredient["name"]})
                if not existing_product or existing_product["quantity"] < ingredient.get("quantity", 0):
                    enough_products = False
                    missing_product = ingredient["name"]
                    break
            elif ingredient["type"] == "drink":
                existing_product = db.drinks.find_one({"drink": ingredient["name"]})
                if not existing_product or existing_product["quantity"] < ingredient.get("quantity", 0):
                    enough_products = False
                    missing_product = ingredient["name"]
                    break

        if enough_products:
            total_set_price = selected_set["price"]
            for ingredient in selected_set["ingredients"]:
                if ingredient["type"] == "drink":
                    # Обновляем количество проданного напитка
                    db.drinks.update_one({"drink": ingredient["name"]}, {"$inc": {"quantity": -1}})
                elif ingredient["type"] == "product":
                    # Обновляем количество проданного продукта
                    db.products.update_one({"product": ingredient["name"]},
                                           {"$inc": {"quantity": -ingredient.get("quantity", 0)}})
            # Создаем новую запись о продаже сета
            db.sales.insert_one(
                {"item_name": selected_set["name"], "type": "set", "quantity": 1, "total_price": total_set_price})

            bot.send_message(call.message.chat.id,
                             f"Заказ на сет '{selected_set['name']}' успешно пробит. Цена: {total_set_price} тг.")
            handle_start(call.message)
        else:
            # Выводим сообщение о том, что не хватает продукта для приготовления сета
            bot.send_message(call.message.chat.id,
                             f"Не хватает продукта '{missing_product}' для приготовления сета '{selected_set['name']}'.")
        return

    selected_rest = next((r for r in rest if r["name"] == item_name), None)
    if selected_rest:
        # Проверяем наличие всех необходимых продуктов для категории "Остальное"
        enough_products = True
        missing_product = None
        for ingredient in selected_rest["ingredients"]:
            if ingredient["type"] == "product":
                existing_product = db.products.find_one({"product": ingredient["name"]})
                if not existing_product or existing_product["quantity"] < ingredient.get("quantity", 0):
                    enough_products = False
                    missing_product = ingredient["name"]
                    break

        if enough_products:
            total_set_price = selected_rest["price"]
            for ingredient in selected_rest["ingredients"]:
                if ingredient["type"] == "drink":
                    # Обновляем количество проданного напитка
                    db.drinks.update_one({"drink": ingredient["name"]}, {"$inc": {"quantity": -1}})
                elif ingredient["type"] == "product":
                    # Обновляем количество проданного продукта
                    db.products.update_one({"product": ingredient["name"]},
                                           {"$inc": {"quantity": -ingredient.get("quantity", 0)}})
            # Создаем новую запись о продаже сета
            db.sales.insert_one(
                {"item_name": selected_rest["name"], "type": "rest", "quantity": 1, "total_price": total_set_price})

            bot.send_message(call.message.chat.id,
                             f"Заказ на сет '{selected_rest['name']}' успешно пробит. Цена: {total_set_price} тг.")
            handle_start(call.message)
        else:
            # Выводим сообщение о том, что не хватает продукта для приготовления сета
            bot.send_message(call.message.chat.id,
                             f"Не хватает продукта '{missing_product}' для приготовления сета '{selected_rest['name']}'.")
        return

    # Если товар не является напитком, продуктом или сетом, обработка ошибки
    bot.send_message(call.message.chat.id, "Произошла ошибка. Пожалуйста, попробуйте еще раз.")

def update_quantity(message, item_name, is_drink):
    try:
        quantity = int(message.text)
        if is_drink:
            drink = db.drinks.find_one({"drink": item_name})
            if drink:
                current_quantity = drink.get("quantity", 0)
                if current_quantity >= quantity:
                    new_quantity = current_quantity - quantity
                    db.drinks.update_one({"drink": item_name}, {"$set": {"quantity": new_quantity}})
                    # Добавляем запись о продаже в коллекцию "sales"
                    db.sales.insert_one({"item_name": item_name, "type": "drink", "quantity": quantity})
                    bot.send_message(message.chat.id, f"Успешно отнято {quantity} '{item_name}'.")
                    handle_start(message)
                else:
                    bot.send_message(message.chat.id, f"Недостаточно товара '{item_name}'. Доступное количество: {current_quantity}.")
            else:
                bot.send_message(message.chat.id, f"Напиток '{item_name}' не найден в базе данных.")
        else:
            product = db.products.find_one({"product": item_name})
            if product:
                current_quantity = product.get("quantity", 0)
                new_quantity = current_quantity - quantity
                db.products.update_one({"product": item_name}, {"$set": {"quantity": new_quantity}})
                # Добавляем запись о продаже в коллекцию "sales"
                db.sales.insert_one({"item_name": item_name, "type": "product", "quantity": quantity})
                bot.send_message(message.chat.id, f"Успешно отнято {quantity} '{item_name}'.")
                handle_start(message)
            else:
                bot.send_message(message.chat.id, f"Продукт '{item_name}' не найден в базе данных.")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите число.")


# Обработчик кнопки "Количество товаров и их наименование"
@bot.message_handler(func=lambda message: message.text == "Количество товаров и их наименование 📝")
def handle_products_quantity(message):
    response = "Количество товаров и их наименование:\n"

    # Получаем все напитки
    drinks = db.drinks.find()
    response += "----------------------------------------------\nНапитки🧊:\n"
    for drink in drinks:
        response += f"{drink['drink']}: {drink['quantity']}\n"

    # Получаем все продукты
    products = db.products.find()
    response += "----------------------------------------------\nПродукты🍞:\n"
    for product in products:
        response += f"{product['product']}: {product['quantity']}гр.\n"

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
    markup = types.ReplyKeyboardMarkup(row_width=6)
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
    markup.add(item1, item2, item3, item4, item5, item6, item7, item8, item9, item10, item11, item12,item13, item14, item15, item16, item17, item18)
    bot.send_message(message.chat.id, "Выберите продукт:", reply_markup=markup)


# Обработчик выбора напитка
@bot.message_handler(func=lambda message: message.text in ["Sprite", "Fanta", "Gorilla", "Cola", "Piala", "Fuse Tea"])
def handle_selected_drink(message):
    drink_name = message.text
    user_id = message.chat.id

    selected_drink[user_id] = {"drink_name": drink_name}
    bot.send_message(message.chat.id, f"Напишите количество {drink_name} в цифрах:")

# Обработчик выбора продукта
@bot.message_handler(func=lambda message: message.text in ["Рис", "Нори", "Ласось", "Твор Сыр", "Угорь", "Огурцы", "Листья Салат", "Майонез", "Курица", "Снеж Краб", "Плавленный Сыр", "Кунжут", "Спайси", "Сыр Моцарелла", "Унаги Соус", "Масаго", "Крылышки", "Фри"])
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

    # Проверяем, существует ли уже такой продукт в базе данных
    existing_product = db.products.find_one({"product": product_name})
    if existing_product:
        # Если продукт уже существует, обновляем его количество
        new_quantity = existing_product["quantity"] + quantity_grams
        db.products.update_one({"product": product_name}, {"$set": {"quantity": new_quantity}})
    else:
        # Если продукта нет в базе данных, добавляем новую запись
        db.products.insert_one(
            {"user_id": user_id, "product": product_name, "quantity": quantity_grams})

    # Удаляем информацию о выбранном продукте
    del selected_product[user_id]

    bot.send_message(user_id, f"Сохранено: {product_name}: {quantity_grams} гр.")
    handle_start(message)


@bot.message_handler(func=lambda message: message.chat.id in selected_drink and message.text.isdigit())
def handle_drink_quantity(message):
    user_id = message.chat.id
    drink_name = selected_drink[user_id]["drink_name"]
    quantity = int(message.text)

    # Проверяем, существует ли уже такой напиток в базе данных
    existing_drink = db.drinks.find_one({"user_id": user_id, "drink": drink_name})

    if existing_drink:
        # Если напиток уже существует, обновляем его количество
        new_quantity = existing_drink["quantity"] + quantity
        db.drinks.update_one({"user_id": user_id, "drink": drink_name}, {"$set": {"quantity": new_quantity}})
        bot.send_message(user_id, f"Количество {drink_name} обновлено: {new_quantity} шт.")
        handle_start(message)
    else:
        # Если напитка нет в базе данных, запрашиваем стоимость
        bot.send_message(user_id, "Введите стоимость напитка:")
        bot.register_next_step_handler(message, lambda m: save_drink_data(user_id, drink_name, quantity, m.text))


    def save_drink_data(user_id, drink_name, quantity, cost):
        # Преобразовать стоимость в числовой формат
        try:
            cost = float(cost)
        except ValueError:
            bot.send_message(user_id, "Пожалуйста, введите корректную стоимость в числовом формате.")
            return

        # Добавляем новую запись о напитке
        db.drinks.insert_one({"user_id": user_id, "drink": drink_name, "quantity": quantity, "cost": cost})

        bot.send_message(user_id, f"Сохранено: {drink_name}: {quantity} шт., стоимость: {cost} тг.")
        handle_start(message)

# Запускаем бот
bot.polling()

