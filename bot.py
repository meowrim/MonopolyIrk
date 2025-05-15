import asyncio
import random
from dotenv import load_dotenv
import os
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties 
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from collections import defaultdict
from aiogram.types import Message, CallbackQuery

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

# Группы объектов
property_groups = {
    "Коричневые": [
        {"name": "Площадь Декабристов", "price": 50, "house_price": 50, "rent": [2, 10, 30, 90, 160, 250]},
        {"name": "Памятник В.И.Ленину", "price": 60, "house_price": 50, "rent": [4, 20, 60, 100, 180, 300]}
    ],
    "Жёлтые": [
        {"name": "Нижняя набережная", "price": 80, "house_price": 50, "rent": [4, 20, 60, 100, 180, 300]},
        {"name": "Московские ворота", "price": 90, "house_price": 50, "rent": [8, 40, 100, 290, 450, 600]},
        {"name": "Сквер Кирова", "price": 100, "house_price": 50, "rent": [10, 50, 150, 300, 500, 700]}
    ],
    "Оранжевые": [
        {"name": "Памятник Александру III", "price": 120, "house_price": 100, "rent": [12, 60, 180, 500, 700, 900]},
        {"name": "Мемориал Вечный огонь", "price": 130, "house_price": 100, "rent": [14, 70, 200, 550, 750, 950]},
        {"name": "Памятник Леониду Гайдаю", "price": 140, "house_price": 100, "rent": [16, 80, 220, 600, 800, 1000]}
    ],
    "Голубые": [
        {"name": "Памятник первопроходцам", "price": 160, "house_price": 100, "rent": [18, 90, 250, 700, 900, 1100]},
        {"name": "Казанская церковь", "price": 170, "house_price": 100, "rent": [20, 100, 300, 750, 850, 1200]},
        {"name": "Музей истории г.Иркутска", "price": 180, "house_price": 100, "rent": [22, 110, 330, 800, 1000, 1300]}
    ],
    "Зелёные": [
        {"name": "Иркутский цирк", "price": 200, "house_price": 150, "rent": [24, 120, 360, 850, 1100, 1400]},
        {"name": "Усадьба В.П.Сукачева", "price": 210, "house_price": 150, "rent": [26, 130, 390, 900, 1150, 1500]},
        {"name": "Галерея В.Бронштейна", "price": 220, "house_price": 150, "rent": [28, 140, 400, 950, 1200, 1600]}
    ],
    "Бирюзовые": [
        {"name": "Музей на свалке", "price": 240, "house_price": 150, "rent": [30, 150, 450, 1000, 1300, 1700]},
        {"name": "Улица Урицкого", "price": 250, "house_price": 150, "rent": [32, 160, 470, 1050, 1350, 1800]},
        {"name": "Усадьба Волконских", "price": 260, "house_price": 150, "rent": [34, 170, 500, 1100, 1400, 1900]}
    ],
    "Розовые": [
        {"name": "Остров Юность", "price": 280, "house_price": 200, "rent": [36, 180, 520, 1150, 1450, 2000]},
        {"name": "Музей-ледокол Ангара", "price": 290, "house_price": 200, "rent": [38, 190, 550, 1200, 1500, 2100]},
        {"name": "Спорт-парк Поляна", "price": 300, "house_price": 200, "rent": [40, 200, 600, 1250, 1550, 2200]}
    ],
    "Фиолетовые": [
        {"name": "Иркутская слобода", "price": 320, "house_price": 200, "rent": [42, 220, 650, 1300, 1600, 2300]},
        {"name": "Театр им.Загурского", "price": 350, "house_price": 200, "rent": [50, 250, 700, 1400, 1800, 2500]}
    ],
    "Железные дороги": [
        {"name": "Станция Академическая", "price": 200},
        {"name": "Станция Кая", "price": 200},
        {"name": "Станция Иркутск-Пасс.", "price": 200},
        {"name": "Станция Мельниково", "price": 200}
    ],
    "Заводы": [
        {"name": "Кабельный завод", "price": 150},
        {"name": "Алюминиевый завод", "price": 150},
    ]
}

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
# Словари для хранения данных о игровой сессии и игроков
games = {}
game_started = {}
player_sessions = {}
player_balance = {}
player_properties = {}
property_owners = {}
player_names = {}
player_buildings = {}
sent_start_button = {}

START_MONEY = 1500

# Состояние FSM для подключения в игру
class JoinGameStates(StatesGroup):
    waiting_for_game_code = State()
# Состояние FSM для строительства
class BuildHouseStates(StatesGroup):
    waiting_for_house_count = State()
# Состояние FSM для изменения баланса
class BalanceChangeStates(StatesGroup):
    waiting_for_action = State()
    waiting_for_amount = State()
# Состояние FSM для обмена собственностью
class TradeStates(StatesGroup):
    choosing_player = State()
    choosing_group = State()
    choosing_property = State()
# Состояние FSM для оплаты ренты заводов
class RentStates(StatesGroup):
    wait_for_dice_sum = State()

# НАЧАТЬ ИГРУ--------------------------------------------------------------------------------------------------

@dp.message(Command("start"))
async def welcome(message: types.Message):
    text = (
        "👋 Привет! Это бот для настольной игры «Монополия Иркутска».",
        "Выберите действие ниже:"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Начать игру", callback_data="create_game")],
        [InlineKeyboardButton(text="🔗 Присоединиться к игре", callback_data="join_game")]
    ])
    await message.answer("\n".join(text), reply_markup=keyboard)

#Создать игру от хоста
@dp.callback_query(lambda c: c.data == "create_game")
async def handle_create_game(callback: types.CallbackQuery):
    code = str(random.randint(1000, 9999))
    games[code] = [callback.from_user.id]
    player_sessions[callback.from_user.id] = code
    player_names[callback.from_user.id] = callback.from_user.full_name
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/завершить_игру")]
        ],
        resize_keyboard=True)
    await callback.message.answer(
        f"Вы стали хостом игры! Код: <b>{code}</b>\nЖдём других игроков...",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# БАЛАНС МЕНЮ--------------------------------------------------------------------------------------------------------------------------------------------------

# Основное меню
@dp.message(Command("баланс"))
async def balance_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Текущий баланс", callback_data="show_balance")],
        [InlineKeyboardButton(text="🔄 Изменить баланс", callback_data="change_balance")]
    ])
    await message.answer("Выберите действие:", reply_markup=keyboard)

# Показать текущий баланс
@dp.callback_query(lambda c: c.data == "show_balance")
async def show_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    balance = player_balance.get(user_id, START_MONEY)
    await callback.message.edit_text(f"Ваш баланс: {balance}₽")

# Изменить баланс (пополнение или снятие)
@dp.callback_query(lambda c: c.data == "change_balance")
async def change_balance_command(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Пополнить баланс", callback_data="balance_add")],
        [InlineKeyboardButton(text="➖ Снять с баланса", callback_data="balance_subtract")]
    ])
    await callback.message.edit_text("💰 Что вы хотите сделать с балансом?", reply_markup=keyboard)
    await state.set_state(BalanceChangeStates.waiting_for_action)

# Выбор действия (пополнение или снятие)
@dp.callback_query(lambda c: c.data in ["balance_add", "balance_subtract"])
async def choose_balance_action(callback: CallbackQuery, state: FSMContext):
    action = callback.data  # balance_add или balance_subtract
    await state.update_data(action=action)
    await callback.message.edit_text("💸 Введите сумму (только число):")
    await state.set_state(BalanceChangeStates.waiting_for_amount)

# Обработка ввода суммы
@dp.message(BalanceChangeStates.waiting_for_amount)
async def process_balance_amount(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❗ Введите положительное целое число.")
        return

    data = await state.get_data()
    action = data.get("action")

    current_balance = player_balance.get(user_id, START_MONEY)

    if action == "balance_add":
        player_balance[user_id] = current_balance + amount
        await message.answer(f"✅ Баланс пополнен на {amount}₽.\n💰 Новый баланс: {player_balance[user_id]}₽")
    elif action == "balance_subtract":
        if amount > current_balance:
            await message.answer(f"❗ Недостаточно средств. У вас только {current_balance}₽.")
            await state.clear()
            return
        player_balance[user_id] = current_balance - amount
        await message.answer(f"✅ С баланса снято {amount}₽.\n💰 Новый баланс: {player_balance[user_id]}₽")

    await state.clear()

# ПОДКЛЮЧЕНИЕ К ИГРЕ-----------------------------------------------------------------------------------------------------

@dp.callback_query(lambda c: c.data == "join_game")
async def handle_join_game(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(JoinGameStates.waiting_for_game_code)
    await callback.message.edit_text("Введите код игры (4 цифры):")

@dp.message(JoinGameStates.waiting_for_game_code)
async def join_game(message: types.Message, state: FSMContext):
    code = message.text
    user_id = message.from_user.id

    if code.isdigit() and len(code) == 4:
        if code in games:
            if user_id not in games[code]:
                games[code].append(user_id)
                player_sessions[user_id] = code
                player_names[user_id] = message.from_user.full_name
                await message.answer(f"Вы присоединились к игре {code}!")
                await state.clear()

            players = games.get(code, [])

            if len(players) < 2:
                await message.answer("❗ Нужно минимум 2 игрока, чтобы начать игру.")
                return

            # Сообщение текущему игроку (не хосту)
            if user_id != games[code][0]:
                await message.answer("Ожидаем начала игры от хоста...")

            # Отправка кнопки хосту
            host_id = games[code][0]
            if len(players) >= 2 and not sent_start_button.get(code):
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="▶️ Начать игру", callback_data=f"start_game:{code}")]
                ])
                await bot.send_message(host_id, "✅ Игроки присоединились. Вы можете начать игру:", reply_markup=keyboard)
                sent_start_button[code] = True
                await state.clear()
        else:
            await message.answer("❌ Игра с таким кодом не найдена.")
    else:
        await message.answer("Введите корректный код игры (4 цифры).")

@dp.callback_query(lambda c: c.data.startswith("start_game:"))
async def handle_start_game(callback: types.CallbackQuery):
    code = callback.data.split(":")[1]
    if code not in games:
        await callback.message.answer("❌ Игра не найдена.")
        return

    user_id = callback.from_user.id
    if games[code][0] != user_id:
        await callback.message.answer("❗ Только хост может начать игру.")
        return

    await start_game(code)

# Игра началась
async def start_game(code):
    players = games[code]
    game_started[code] = True
    host_id = players[0]
    for user_id in players:
        player_balance[user_id] = START_MONEY
        player_properties[user_id] = []
        builder = ReplyKeyboardBuilder()
        builder.button(text="/баланс")
        builder.button(text="/купить")
        builder.button(text="/собственность")
        builder.button(text="/строить")
        builder.button(text="/рента")

        if user_id == host_id:
            builder.button(text="/завершить_игру")

        builder.adjust(2)
        await bot.send_message(
            user_id,
            f"🎲 Игра началась! Ваш баланс: {START_MONEY}₽",
            reply_markup=builder.as_markup(resize_keyboard=True)
        )

# ЗАВЕРШИТЬ ИГРУ---------------------------------------------------------------------------------------------------------------------------------------------

@dp.message(Command("завершить_игру"))
async def end_game(message: types.Message):
    user_id = message.from_user.id
    code = player_sessions.get(user_id)

    if not code or code not in games:
        await message.answer("❗ Вы не участвуете в активной игре.")
        return

    if games[code][0] != user_id:
        await message.answer("❌ Только хост может завершить игру.")
        return

    # Список игроков, чтобы потом всем было отправлено сообщение
    player_ids = games[code]

    # Удаление игры и все связанные данные
    for pid in player_ids:
        player_sessions.pop(pid, None)
        player_balance.pop(pid, None)
        player_properties.pop(pid, None)
        player_names.pop(pid, None)
        player_buildings.pop(pid, None)

    # Удаление владельцев недвижимости, которые участвовали в игре
    for prop in list(property_owners.keys()):
        if property_owners[prop] in player_ids:
            del property_owners[prop]

    for group, streets in property_groups.items():
        for street in streets:
            street["houses"] = 0
            street["hotel"] = False

    # Сбрасывание информации о зданиях у игроков
    player_buildings.clear()

    del games[code]
    del sent_start_button[code]

    for pid in player_ids:
        await bot.send_message(
            pid,
            "🛑 Игра завершена.",
            reply_markup=types.ReplyKeyboardRemove()
        )

        text = (
            "👋 Привет! Это бот для настольной игры «Монополия Иркутска».",
            "Выберите действие ниже:"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать игру", callback_data="create_game")],
            [InlineKeyboardButton(text="🔗 Присоединиться к игре", callback_data="join_game")]
        ])
        await bot.send_message(pid, "\n".join(text), reply_markup=keyboard)

# МЕНЮ СОБСТВЕННОСТЬ--------------------------------------------------------------------------------------------------------------------------------------

# Основное меню для управления собственностью
@dp.message(Command("собственность"))
async def property_menu(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Текущая собственность", callback_data="show_properties")],
        [InlineKeyboardButton(text="🔄 Обмен собственностью", callback_data="trade_properties")],
        [InlineKeyboardButton(text="👁️‍🗨️ Просмотр собственности других", callback_data="view_all_properties")]
    ])
    await message.answer("Выберите действие с вашей собственностью:", reply_markup=keyboard)

# Показать текущую собственность
@dp.callback_query(lambda c: c.data == "show_properties")
async def show_properties(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    props = player_properties.get(user_id, [])
    
    if props:
        lines = []
        for p in props:
            buildings = player_buildings.get(user_id, {}).get(p, {"houses": 0, "hotel": False})
            houses = buildings["houses"]
            hotel = buildings["hotel"]
                
            street_color = None
            for group_name, streets in property_groups.items():
                for street in streets:
                    if street["name"].strip().lower() == p.strip().lower():
                        street_color = group_name
                        break
                    if street_color:
                        break
            
            if street_color in ["Заводы", "Железные дороги"]:
                lines.append(f"◆ {p} ({street_color})")
            else:
                lines.append(f"◆ {p} ({street_color}) \n 🏠 Дома: {houses} | 🏨 Отель: {'да' if hotel else 'нет'}")

        await callback.message.edit_text("Ваша собственность:\n" + "\n".join(lines))
    else:
        await callback.message.edit_text("❗ У вас пока нет собственности.")

# Обмен собственностью
@dp.callback_query(lambda c: c.data == "trade_properties")
async def start_trade(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in player_sessions:
        await callback.message.edit_text("❗ Вы не находитесь в игре.")
        return

    code = player_sessions[user_id]
    players_in_game = games.get(code, [])
    other_players = [pid for pid in players_in_game if pid != user_id]

    if not other_players:
        await callback.message.edit_text("❗ В игре нет других игроков для обмена.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[ 
        [InlineKeyboardButton(text=player_names[pid], callback_data=f"trade_player_{pid}")] 
        for pid in other_players
    ])
    await callback.message.edit_text("🔄 Кому вы хотите передать собственность?", reply_markup=keyboard)
    await state.set_state(TradeStates.choosing_player)

# Обработка выбора игрока
@dp.callback_query(lambda c: c.data.startswith("trade_player_"))
async def choose_trade_partner(callback: types.CallbackQuery, state: FSMContext):
    receiver_id = int(callback.data.split("_")[-1])
    sender_id = callback.from_user.id

    await state.update_data(receiver_id=receiver_id)

    sender_props = player_properties.get(sender_id, [])
    if not sender_props:
        await callback.message.edit_text("❗ У вас нет собственности для передачи.")
        await state.clear()
        return

    owned_groups = []
    for group, props in property_groups.items():
        if any(p["name"] in sender_props for p in props):
            owned_groups.append(group)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=group, callback_data=f"trade_group_{group}")]
        for group in owned_groups
    ])

    await callback.message.edit_text("🎨 Выберите группу собственности:", reply_markup=keyboard)
    await state.set_state(TradeStates.choosing_group)

#Обработка выбора группы 
@dp.callback_query(lambda c: c.data.startswith("trade_group_"))
async def choose_property_group(callback: types.CallbackQuery, state: FSMContext):
    sender_id = callback.from_user.id
    group_name = callback.data.split("trade_group_")[1]

    sender_props = player_properties.get(sender_id, [])
    streets_in_group = property_groups.get(group_name, [])

    for street in streets_in_group:
        street_name = street["name"]
        if street_name in sender_props:
            buildings = player_buildings.get(sender_id, {}).get(street_name, {"houses": 0, "hotel": False})
            if buildings["houses"] > 0 or buildings["hotel"]:
                await callback.message.edit_text(
                    f"❌ Нельзя передать улицы из группы «{group_name}», потому что на одной из них есть постройки."
                )
                await state.clear()
                return

    owned_in_group = [p for p in streets_in_group if p["name"] in sender_props]

    if not owned_in_group:
        await callback.message.edit_text("❗ У вас нет собственности в этой группе.")
        await state.clear()
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=p["name"], callback_data=f"trade_property_{p['name']}")]
        for p in owned_in_group
    ])

    await callback.message.edit_text("🏘 Выберите конкретную собственность для передачи:", reply_markup=keyboard)
    await state.set_state(TradeStates.choosing_property)

# Финальная передача
@dp.callback_query(lambda c: c.data.startswith("trade_property_"))
async def finalize_trade(callback: types.CallbackQuery, state: FSMContext):
    sender_id = callback.from_user.id
    data = await state.get_data()
    receiver_id = data.get("receiver_id")
    property_name = callback.data.split("trade_property_")[1]

    player_properties[sender_id].remove(property_name)

    if receiver_id not in player_properties:
        player_properties[receiver_id] = []
    player_properties[receiver_id].append(property_name)

    # Обновление владельца
    property_owners[property_name] = receiver_id

    await callback.message.edit_text(
        f"✅ Вы передали {property_name} игроку {player_names[receiver_id]}."
    )

    await bot.send_message(
        receiver_id,
        f"📦 Вы получили собственность «{property_name}» от {player_names[sender_id]}!"
    )

    await state.clear()

# Просмотр собственности всех игроков
@dp.callback_query(lambda c: c.data == "view_all_properties")
async def view_all_properties(callback: types.CallbackQuery):
    all_players = list(player_properties.keys())
    
    if not all_players:
        await callback.message.edit_text("❗ В игре нет игроков.")
        return

    lines = []
    for player_id in all_players:
        props = player_properties.get(player_id, [])
        if props:
            player_info = [f"🏷 Игрок: {player_names.get(player_id, 'Неизвестный')}"]
            for p in props:
                buildings = player_buildings.get(player_id, {}).get(p, {"houses": 0, "hotel": False})
                houses = buildings["houses"]
                hotel = buildings["hotel"]
                
                street_color = None
                for group_name, streets in property_groups.items():
                    for street in streets:
                        if street["name"].strip().lower() == p.strip().lower():
                            street_color = group_name
                            break
                    if street_color:
                        break
                
                if street_color in ["Заводы", "Железные дороги"]:
                    player_info.append(f"◆ {p} ({street_color})")
                else:
                    player_info.append(f"◆ {p} ({street_color}) \n 🏠 Дома: {houses} | 🏨 Отель: {'да' if hotel else 'нет'}")

            lines.append("\n".join(player_info))
        else:
            lines.append(f"🏷 Игрок: {player_names.get(player_id, 'Неизвестный')} \n ❗ Нет собственности")

    if lines:
        await callback.message.edit_text("👀 Собственность всех игроков:\n\n" + "\n\n".join(lines))
    else:
        await callback.message.edit_text("❗ У игроков нет собственности.")

# КУПИТЬ---------------------------------------------------------------------------------------------------------------------------------

@dp.message(Command("купить"))
async def choose_group(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=group, callback_data=f"group:{group}")]
            for group in property_groups
        ]
    )
    await message.answer("Выбери цветовую группу или тип собственности:", reply_markup=keyboard)

# Выбор группы улиц
@dp.callback_query(lambda c: c.data.startswith("group:"))
async def show_properties_from_group(callback: types.CallbackQuery):
    group = callback.data.split(":", 1)[1]
    streets = property_groups.get(group, [])

    buttons = []
    for s in streets:
        name = s['name']
        price = s['price']

        if name in property_owners:
            owner_id = property_owners[name]
            owner_name = player_names.get(owner_id, "другой игрок")

            if owner_id == callback.from_user.id:
                label = f"📍 {name} — ваша собственность"
                buttons.append([InlineKeyboardButton(text=label, callback_data=f"owned:{name}")])
            else:
                label = f"📍 {name} — занята ({owner_name})"
                buttons.append([InlineKeyboardButton(text=label, callback_data=f"occupied:{name}")])
        else:
            label = f"{name} — {price}₽"
            buttons.append([InlineKeyboardButton(text=label, callback_data=f"buy:{name}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        f"🏘 Улицы в группе «{group}». Выбери доступную для покупки:",
        reply_markup=keyboard
    )

# Выбор конкретной улицы и покупка
@dp.callback_query(lambda c: c.data.startswith("buy:"))
async def handle_buy_property(callback: types.CallbackQuery):
    property_name = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id

    if user_id not in player_sessions:
        await callback.answer("❗ Вы не присоединились к игре", show_alert=True)
        return

    price = None
    for group in property_groups.values():
        for prop in group:
            if prop["name"] == property_name:
                price = prop["price"]
                break
        if price is not None:
            break

    if price is None:
        await callback.answer("❌ Недвижимость не найдена", show_alert=True)
        return

    balance = player_balance.get(user_id)
    if balance is None:
        player_balance[user_id] = START_MONEY
        balance = START_MONEY

    if balance < price:
        await callback.answer("💸 Недостаточно средств для покупки", show_alert=True)
        return

    player_balance[user_id] -= price
    player_properties.setdefault(user_id, []).append(property_name)
    property_owners[property_name] = user_id

    await callback.message.edit_text(f"✅ Вы купили «{property_name}» за {price}₽")
    await callback.answer("Покупка прошла успешно!")

# Когда пользователь нажимает на свою собственность
@dp.callback_query(lambda c: c.data.startswith("owned:"))
async def handle_owned_property(callback: types.CallbackQuery):
    property_name = callback.data.split(":", 1)[1]
    await callback.answer(f"🏠 {property_name} уже принадлежит вам", show_alert=True)

# Когда пользователь нажимает на занятую другим игроком собственность
@dp.callback_query(lambda c: c.data.startswith("occupied:"))
async def handle_occupied_property(callback: types.CallbackQuery):
    property_name = callback.data.split(":", 1)[1]
    owner_id = property_owners.get(property_name)
    owner_name = player_names.get(owner_id, "другой игрок")
    await callback.answer(f"❌ {property_name} уже принадлежит {owner_name}", show_alert=True)

# СТРОИТЕЛЬСТВО----------------------------------------------------------------------------------------------------------------------------------------------------

# Функция начала строительства домов
async def show_build_menu(user_id: int, send_func):
    properties = player_properties.get(user_id, [])

    owned_groups = {}
    for group_name, streets in property_groups.items():
        group_owned_streets = []
        for street in streets:
            if street["name"] in properties:
                group_owned_streets.append(street["name"])
        if group_owned_streets:
            owned_groups[group_name] = group_owned_streets

    buttons = []
    for group_name, owned_streets in owned_groups.items():
        # Пропуск заводов и жд
        if group_name in ["Заводы", "Железные дороги"]:
            continue

        full_group_streets = [street["name"] for street in property_groups[group_name]]
        if set(full_group_streets).issubset(set(properties)):
            buttons.append([InlineKeyboardButton(text=group_name, callback_data=f"choose_group:{group_name}")])

    if not buttons:
        await send_func("❗ У вас нет полной группы улиц для строительства.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await send_func("🏗 Выберите цветовую группу для строительства:", reply_markup=keyboard)

# Команда начала строительства домов
@dp.message(Command("строить"))
async def start_building(message: types.Message, state: FSMContext):
    await show_build_menu(message.from_user.id, message.answer)

def find_street_info_and_group(street_name):
    for group, street_list in property_groups.items():
        for street in street_list:
            if street["name"].strip() == street_name.strip():
                return street, group
    return None, None

# Обработка выбора группы улиц
@dp.callback_query(lambda c: c.data.startswith("choose_group:"))
async def choose_street_in_group(callback: types.CallbackQuery, state: FSMContext):
    group = callback.data.split(":")[1]
    streets = [street["name"] for street in property_groups[group]]
    buttons = [[InlineKeyboardButton(text=street, callback_data=f"choose_build:{street}")] for street in streets]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(f"🏘 Выберите улицу для строительства:", reply_markup=keyboard)

# Обработка выбора конкретной улицы
@dp.callback_query(lambda c: c.data.startswith("choose_build:"))
async def ask_build_option(callback: types.CallbackQuery, state: FSMContext):
    street = callback.data.split(":")[1].strip()

    await state.set_state(BuildHouseStates.waiting_for_house_count)
    await state.update_data(street=street)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Построить дом", callback_data="build_house")],
        [InlineKeyboardButton(text="🏨 Построить отель", callback_data="build_hotel")]
    ])

    await callback.message.edit_text(f"🏗 Что вы хотите построить на «{street}»?", reply_markup=keyboard)

# Постройка дома
@dp.callback_query(lambda c: c.data == "build_house")
async def build_house_callback(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    street_name = data.get("street")
    user_id = callback.from_user.id

    if not street_name:
        await callback.message.answer("❗ Улица не выбрана.")
        await state.clear()
        return

    street_info, group = find_street_info_and_group(street_name)
    if not street_info:
        await callback.message.answer("❗ Улица не найдена.")
        await state.clear()
        return

    buildings = player_buildings.setdefault(user_id, {}).setdefault(street_name, {"houses": 0, "hotel": False})

    if buildings["hotel"]:
        await callback.message.answer("🏨 Отель уже построен на этой улице.")
        return

    if buildings["houses"] >= 4:
        await callback.message.answer("❗ На улице уже 4 дома. Постройте отель.")
        return

    await state.set_state(BuildHouseStates.waiting_for_house_count)
    await callback.message.answer(f"🏠 Сколько домов построить на «{street_name}»? (1–{4 - buildings['houses']})")

# Обработка количества домов
@dp.message(BuildHouseStates.waiting_for_house_count)
async def handle_house_count(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        count = int(message.text)
        if count < 1 or count > 4:
            raise ValueError
    except ValueError:
        await message.answer("❗ Введите число от 1 до 4.")
        return

    data = await state.get_data()
    street_name = data.get("street", "").strip()
    if not street_name:
        await message.answer("❗ Улица не была выбрана.")
        await state.clear()
        return

    street_info, group_name = find_street_info_and_group(street_name)
    if street_info is None:
        await message.answer(f"❗ Улица «{street_name}» не найдена в базе.")
        await state.clear()
        return

    buildings = player_buildings.setdefault(user_id, {}).setdefault(street_name, {"houses": 0, "hotel": False})

    if buildings["hotel"]:
        await message.answer("🏨 Отель уже построен на этой улице.")
        return

    total_houses = buildings["houses"] + count
    if total_houses > 4:
        await message.answer("❗ Можно максимум 4 дома на одной улице.")
        return

    total_cost = count * street_info["house_price"]
    balance = player_balance.get(user_id, START_MONEY)
    if balance < total_cost:
        await message.answer(f"💸 Не хватает средств. Нужно {total_cost}₽, у вас {balance}₽.")
        await state.clear()
        return

    player_balance[user_id] = balance - total_cost
    buildings["houses"] += count
    
    await message.answer(
        f"✅ Построено {count} дом(ов) на «{street_name}» за {total_cost}₽.\n"
        f"🏠 Всего домов: {buildings['houses']}, отель: {'✅' if buildings['hotel'] else '❌'}\n"
        f"💰 Остаток: {player_balance[user_id]}₽"
    )
    
    # Клавиатура для продолжения или завершения строительства
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Продолжить строительство", callback_data="continue_building")],
        [InlineKeyboardButton(text="🔚 Завершить", callback_data="cancel_building")]
    ])
    await message.answer("Хотите продолжить строительство на другой улице?", reply_markup=keyboard)
    await state.clear()

# Постройка отеля
@dp.callback_query(lambda c: c.data == "build_hotel")
async def build_hotel_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()

    street_name = data.get("street", "").strip()
    if not street_name:
        await callback.message.answer("❗ Улица не выбрана.")
        await state.clear()
        return

    street_info, group = find_street_info_and_group(street_name)
    if not street_info:
        await callback.message.answer(f"❗ Улица «{street_name}» не найдена.")
        await state.clear()
        return

    buildings = player_buildings.setdefault(user_id, {}).setdefault(street_name, {"houses": 0, "hotel": False})

    if buildings["hotel"]:
        await callback.message.answer("🏨 Отель уже построен на этой улице.")
        return

    if buildings["houses"] < 4:
        await callback.message.answer("❗ Для постройки отеля нужно 4 дома.")
        return

    cost = street_info["house_price"]
    balance = player_balance.get(user_id, START_MONEY)
    if balance < cost:
        await callback.message.answer(f"💸 Недостаточно средств. Нужно {cost}₽, у вас {balance}₽.")
        await state.clear()
        return

    player_balance[user_id] = balance - cost
    buildings["houses"] = 0
    buildings["hotel"] = True

    await callback.message.answer(
        f"🏨 Отель построен на «{street_name}» за {cost}₽.\n"
        f"💰 Остаток: {player_balance[user_id]}₽"
    )

    # Клавиатура для продолжения или завершения строительства
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Продолжить строительство", callback_data="continue_building")],
        [InlineKeyboardButton(text="🔚 Завершить", callback_data="cancel_building")]
    ])
    await callback.message.answer("Хотите продолжить строительство на другой улице?", reply_markup=keyboard)

    await state.clear()

# Обработчик кнопки отмены строительства
@dp.callback_query(lambda c: c.data == "cancel_building")
async def handle_cancel_building(callback: types.CallbackQuery):
    await callback.message.edit_text("🔚 Строительство завершено.")

# Обработчик кнопки продолжения строительства
@dp.callback_query(lambda c: c.data == "continue_building")
async def continue_building(callback: types.CallbackQuery, state: FSMContext):
    await show_build_menu(callback.from_user.id, callback.message.answer)
    await callback.answer()

# РЕНТА-----------------------------------------------------------------------------------------------------------------------------------------

# Кнопка ренты
@dp.message(Command("рента"))
async def start_rent(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    other_players = [uid for uid in player_properties if uid != user_id]

    if not other_players:
        await message.answer("❗ Сейчас нет других игроков.")
        return

    buttons = [
        [InlineKeyboardButton(text=f"{player_names[uid]}", callback_data=f"rent_to:{uid}")]
        for uid in other_players
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("👤 Кому вы платите ренту?", reply_markup=keyboard)

# Обработка выбора игрока
@dp.callback_query(lambda c: c.data.startswith("rent_to:"))
async def choose_rent_group(callback: types.CallbackQuery, state: FSMContext):
    to_id = int(callback.data.split(":")[1])
    await state.update_data(rent_to=to_id)

    owned = player_properties.get(to_id, [])
    groups_with_streets = set()
    for group_name, streets in property_groups.items():
        if any(street["name"] in owned for street in streets):
            groups_with_streets.add(group_name)

    if not groups_with_streets:
        await callback.message.answer("❗ У этого игрока нет собственности.")
        return

    buttons = [
        [InlineKeyboardButton(text=group, callback_data=f"rent_group:{group}")]
        for group in groups_with_streets
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("🌈 На какую группу собственности попали?", reply_markup=keyboard)

# Обработка выбора группы улиц
@dp.callback_query(lambda c: c.data.startswith("rent_group:"))
async def choose_rent_street(callback: types.CallbackQuery, state: FSMContext):
    group = callback.data.split(":")[1]
    data = await state.get_data()
    to_id = data["rent_to"]
    owned = player_properties.get(to_id, [])

    streets = [
        street["name"]
        for street in property_groups[group]
        if street["name"] in owned
    ]

    buttons = [
        [InlineKeyboardButton(text=street, callback_data=f"rent_street:{street}")]
        for street in streets
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("🏘 Какая конкретно улица?", reply_markup=keyboard)

# Выбор улицы и списание ренты
@dp.callback_query(lambda c: c.data.startswith("rent_street:"))
async def pay_rent(callback: types.CallbackQuery, state: FSMContext):
    street_name = callback.data.split(":")[1].strip()
    data = await state.get_data()
    user_id = callback.from_user.id
    to_id = data.get("rent_to")

    street_info, group_name = find_street_info_and_group(street_name)
    if not street_info:
        await callback.message.answer("❗ Улица не найдена.")
        await state.clear()
        return

    # Если это заводы — просим ввести сумму кубиков
    if group_name == "Заводы":
        await state.update_data(rent_street=street_name, rent_group=group_name, rent_to=to_id)
        await callback.message.edit_text("🎲 Введите сумму, выпавшую на кубиках (от 2 до 12):")
        await state.set_state(RentStates.wait_for_dice_sum)
        return

    # Если это железные дороги
    if group_name == "Железные дороги":
        owned = player_properties.get(to_id, [])
        railroads = [s["name"] for s in property_groups["Железные дороги"]]
        num_owned = sum(1 for r in railroads if r in owned)

        if num_owned == 1:
            rent = 25
        elif num_owned == 2:
            rent = 50
        elif num_owned == 3:
            rent = 100
        elif num_owned >= 4:
            rent = 200
        else:
            rent = 0
    else:
        buildings = player_buildings.get(to_id, {}).get(street_name, {"houses": 0, "hotel": False})
        if buildings["hotel"]:
            rent = street_info["rent"][5]
        else:
            rent = street_info["rent"][buildings["houses"]]

    balance_from = player_balance.get(user_id, START_MONEY)
    balance_to = player_balance.get(to_id, START_MONEY)

    if balance_from < rent:
        await callback.message.answer(f"💸 У вас не хватает денег. Рента: {rent}₽, у вас: {balance_from}₽.")
        await state.clear()
        return

    player_balance[user_id] = balance_from - rent
    player_balance[to_id] = balance_to + rent

    await callback.message.answer(
        f"✅ Вы заплатили {rent}₽ ренты за «{street_name}» игроку {player_names[to_id]}.\n"
        f"📤 Ваш баланс: {player_balance[user_id]}₽\n"
        f"📥 Баланс получателя: {player_balance[to_id]}₽"
    )

    await bot.send_message(
        to_id,
        f"💰 Вам заплатили {rent}₽ ренты за «{street_name}»!\n"
        f"👤 От: {player_names[user_id]}\n"
        f"💵 Ваш новый баланс: {player_balance[to_id]}₽"
    )

    await state.clear()

# Обработка суммы кубиков
@dp.message(RentStates.wait_for_dice_sum)
async def process_dice_sum_input(message: types.Message, state: FSMContext):
    try:
        dice_sum = int(message.text.strip())
        if dice_sum < 2 or dice_sum > 12:
            raise ValueError
    except ValueError:
        await message.answer("❗ Введите корректное число от 2 до 12.")
        return

    data = await state.get_data()
    user_id = message.from_user.id
    to_id = data.get("rent_to")
    street_name = data.get("rent_street")

    owned = player_properties.get(to_id, [])
    factories = [s["name"] for s in property_groups["Заводы"]]
    num_owned = sum(1 for f in factories if f in owned)

    rent = dice_sum * (5 if num_owned == 1 else 10)

    balance_from = player_balance.get(user_id, START_MONEY)
    balance_to = player_balance.get(to_id, START_MONEY)

    if balance_from < rent:
        await message.answer(f"💸 У вас не хватает денег. Рента: {rent}₽, у вас: {balance_from}₽.")
        await state.clear()
        return

    player_balance[user_id] = balance_from - rent
    player_balance[to_id] = balance_to + rent

    await message.answer(
        f"✅ Вы заплатили {rent}₽ ренты за «{street_name}» игроку {player_names[to_id]}.\n"
        f"📤 Ваш баланс: {player_balance[user_id]}₽\n"
        f"📥 Баланс получателя: {player_balance[to_id]}₽"
    )

    await bot.send_message(
        to_id,
        f"💰 Вам заплатили {rent}₽ ренты за «{street_name}»!\n"
        f"👤 От: {player_names[user_id]}\n"
        f"💵 Ваш новый баланс: {player_balance[to_id]}₽"
    )

    await state.clear()

# Ответ бота если это не команда и игрок находится не в состоянии
@dp.message()
async def unknown_message(message: types.Message):
    await message.answer("Введите команду, я вас не понимаю.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())