import json
import math
import random
import threading
from data import change_users_info, main_keyboard, users_info, tz
from datetime import datetime, timedelta, time as datetime_time
from keyboard import get_callback_button
from math import floor
from vk_auth import vk_session, VkBotEventType


class GamePets:
    all_pets = {}
    all_foods = {}
    all_pills = {}
    all_potions = {}

    all_max_pets = {}
    start_max_pets = 3

    shelter = []
    shelter_price = 20
    market = {}
    max_lot = 0

    def save_me(self):
        for pets in self.all_pets.values():
            for pet in pets:
                pet.stop_me()
        return self.all_pets, self.all_foods, self.all_pills, self.all_max_pets, self.shelter, self.all_potions, self.market, self.max_lot

    def load_me(self, data):
        self.all_pets = data[0]
        self.all_foods = data[1]
        self.all_pills = data[2]
        if len(data) >= 4:
            self.all_max_pets = data[3]
        if len(data) >= 5:
            self.shelter = data[4]
        if len(data) >= 6:
            self.all_potions = data[5]
        if len(data) >= 7:
            self.market = data[6]
        if len(data) >= 8:
            self.max_lot = data[7]

        for pets in self.all_pets.values():
            for pet in pets:
                pet.game_pets = self
                pet.start_me()

        for pet in self.shelter:
            pet.game_pets = self

    def add_pet(self, owner_id: str):
        self.all_pets[owner_id] += [Pet(self, owner_id)]

    def delete_pet(self, owner_id: str, pet):
        self.all_pets[owner_id].remove(pet)

    @staticmethod
    def send_pets_page(user_id, page, pets_list, prefix):
        buttons = []
        pets_in_page = 5
        first = page * pets_in_page
        last = (page + 1) * pets_in_page
        for i, x in enumerate(pets_list):
            if first <= i < last:
                buttons += [[get_callback_button(f'{x.name}', 'primary', {'args': f'{prefix}.Pet.{x.name}'})]]

        menu = []
        if page > 0:
            menu += [get_callback_button('⬅', 'positive', {'args': f'{prefix}.page.{page - 1}'})]
        menu += [get_callback_button('Назад', 'negative', {'args': f'{prefix}.back'})]
        if last < len(pets_list):
            menu += [get_callback_button('➡', 'positive', {'args': f'{prefix}.page.{page + 1}'})]

        keyboard = str(json.dumps({
            "one_time": False,
            "buttons": buttons + [menu]
        }, ensure_ascii=False))

        vk_session.method('messages.send',
                          {'user_id': int(user_id),
                           'message': f'Страница {page + 1}',
                           'random_id': 0, 'keyboard': keyboard})

    def shelter_actions(self, user_id, args=None):
        if args is None:
            args = ''

        # Взять питомца
        if args == 'shelter.take':
            self.send_pets_page(user_id, 0, self.shelter, 'shelter.take')
            return
        elif args.startswith('shelter.take.Pet'):
            name = args.replace('shelter.take.Pet.', '')
            answer = f'Вот информация о питомце {name}. Желаете взять его себе в домик?\n'
            for pet in self.shelter:
                if pet.name == name:
                    answer += pet.get_info(True)
                    break
            keyboard = str(json.dumps({
                "one_time": False,
                "buttons": [
                    [get_callback_button('Да', 'positive', {'args': f'shelter.take.yes.{name}'}),
                     get_callback_button('Нет', 'negative', {'args': f'shelter.take.no'})]
                ]
            }, ensure_ascii=False))
        elif args.startswith('shelter.take.yes'):
            if users_info.get(user_id, {}).get("balance", 0) >= self.shelter_price:
                users_info[user_id]["balance"] -= self.shelter_price

                name = args.replace('shelter.take.yes.', '')
                for pet in self.shelter:
                    if pet.name == name:
                        pet.start_me()

                        new_name = name
                        n = 1
                        while True:
                            for x in self.all_pets.get(user_id):
                                if new_name == x.name:
                                    new_name = f'{name} {n}'
                                    n += 1
                                    break
                            else:
                                break
                        pet.name = new_name

                        pet.status = 'обрел нового хозяина!'
                        pet.owner_id = user_id

                        self.all_pets[user_id] += [pet]
                        self.shelter.remove(pet)
                        self.all_foods[user_id] += 10
                        break
                answer = f'Вы забрали {name} из приюта. Дарим Вам 10🍎 для обеспечения питомца в первое время.'

            else:
                answer = f'Недостаточно 💰 для покупки.\n' \
                         f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 2)}💰\n' \
                         f'Требуется: {round(self.shelter_price, 2)}💰'

            vk_session.method('messages.send',
                              {'user_id': int(user_id),
                               'message': answer,
                               'random_id': 0})
            self.shelter_actions(user_id)
            return
        elif args == 'shelter.take.no':
            self.send_pets_page(user_id, 0, self.shelter, 'shelter.take')
            return
        elif args.startswith('shelter.take.page.'):
            self.send_pets_page(user_id, int(args.replace('shelter.take.page.', '')), self.shelter, 'shelter.take')
            return
        elif args == 'shelter.take.back':
            self.shelter_actions(user_id)
            return

        # Отдать питомца
        elif args == 'shelter.give':
            pets = [user_pet for user_pet in self.all_pets.get(user_id, [])
                    if user_pet not in [market_pet.get('pet') for market_pet in self.market.values()]]
            self.send_pets_page(user_id, 0, pets, 'shelter.give')
            return
        elif args.startswith('shelter.give.Pet'):
            name = args.replace('shelter.give.Pet.', '')
            answer = f'Уверены, что хотите отдать {name} в приют?'
            keyboard = str(json.dumps({
                "one_time": False,
                "buttons": [
                    [get_callback_button('Да', 'positive', {'args': f'shelter.give.yes.{name}'}),
                     get_callback_button('Нет', 'negative', {'args': f'shelter.give.no'})]
                ]
            }, ensure_ascii=False))
        elif args.startswith('shelter.give.yes'):
            name = args.replace('shelter.give.yes.', '')
            for pet in self.all_pets[user_id]:
                if pet.name == name:
                    pet.stop_me()
                    pet.status = 'переехал в приют'

                    new_name = name
                    n = 1
                    while True:
                        for x in self.shelter:
                            if new_name == x.name:
                                new_name = f'{name} {n}'
                                n += 1
                                break
                        else:
                            break
                    pet.name = new_name
                    self.shelter += [pet]
                    self.all_pets[user_id].remove(pet)
                    break
            answer = f'Вы отдали {name} в приют. Там ему будет хорошо. Обещаем!'
            vk_session.method('messages.send',
                              {'user_id': int(user_id),
                               'message': answer,
                               'random_id': 0})
            self.shelter_actions(user_id)
            return
        elif args == 'shelter.give.no':
            pets = [user_pet for user_pet in self.all_pets.get(user_id, [])
                    if user_pet not in [market_pet.get('pet') for market_pet in self.market.values()]]
            self.send_pets_page(user_id, 0, pets, 'shelter.give')
            return
        elif args.startswith('shelter.give.page.'):
            pets = [user_pet for user_pet in self.all_pets.get(user_id, [])
                    if user_pet not in [market_pet.get('pet') for market_pet in self.market.values()]]
            self.send_pets_page(user_id, int(args.replace('shelter.give.page.', '')), pets,
                                'shelter.give')
            return
        elif args == 'shelter.give.back':
            self.shelter_actions(user_id)
            return

        elif args == 'shelter.back':
            self.start(user_id)
            return

        else:
            answer = 'Выберите действие'
            keyboard = str(json.dumps({
                "one_time": False,
                "buttons": [
                    [get_callback_button(f'Забрать ({round(self.shelter_price, 2)}💰)', 'primary',
                                         {'args': 'shelter.take'}),
                     get_callback_button('Отдать', 'secondary', {'args': 'shelter.give'})],
                    [get_callback_button('Назад', 'negative', {'args': 'shelter.back'})]
                ]
            }, ensure_ascii=False))

        vk_session.method('messages.send',
                          {'user_id': int(user_id),
                           'message': answer,
                           'random_id': 0, 'keyboard': keyboard})

    def market_actions(self, user_id, args=None, event=None):
        keyboard = None
        if args is None:
            args = ''

        message = ''
        if event is not None:
            args = 'market.price'
            message = event.obj.text.strip()

        # Купить питомца
        if args == 'market.take':
            self.send_pets_page(user_id, 0, list(self.market.keys()), 'market.take')
            return
        elif args.startswith('market.take.Pet'):
            lot_name = args.replace('market.take.Pet.', '')
            for lot in self.market.keys():
                if lot.name == lot_name:
                    pet = self.market.get(lot).get("pet")
                    owner_id = self.market.get(lot).get("owner_id")
                    if pet in self.all_pets.get(owner_id):
                        price = self.market.get(lot).get("price")
                        answer = f'Вот информация о лоте {lot_name.replace("Лот", "")}. Желаете приобрести его?\n\n' \
                                 f'Стоимость: {round(price, 2)}💰\n\n' \
                                 f'{pet.get_info(True)}'

                        keyboard = str(json.dumps({
                            "one_time": False,
                            "buttons": [
                                [get_callback_button(f'Да ({round(price, 2)}💰)', 'positive',
                                                     {'args': f'market.take.yes.{lot_name}'}),
                                 get_callback_button('Нет', 'negative', {'args': f'market.take.no'})]
                            ]
                        }, ensure_ascii=False))
                        break
                    else:
                        answer = f'{lot_name} не найден на рынке. Возможно, кто-то уже купил его или питомец был ' \
                                 f'переведен в другой домик. Такое иногда случается'
                        vk_session.method('messages.send', {'user_id': int(user_id), 'message': answer, 'random_id': 0})
                        self.market.pop(lot)
                        self.market_actions(user_id, 'market.take')
                        return
            else:
                answer = f'{lot_name} не найден на рынке. Возможно, кто-то уже купил его или питомец был ' \
                         f'переведен в другой домик. Такое иногда случается'
        elif args.startswith('market.take.yes'):
            lot_name = args.replace('market.take.yes.', '')
            for lot in self.market.keys():
                if lot.name == lot_name:
                    price = self.market.get(lot).get("price")
                    pet = self.market.get(lot).get("pet")
                    owner_id = self.market.get(lot).get("owner_id")
                    if pet in self.all_pets.get(owner_id):
                        if users_info.get(user_id, {}).get("balance", 0) >= price:
                            pet.stop_me()

                            users_info[user_id]["balance"] -= price
                            users_info[owner_id]["balance"] += price

                            self.all_pets[owner_id].remove(pet)
                            self.market.pop(lot)

                            vk_session.method('messages.send',
                                              {'user_id': int(owner_id),
                                               'message': f'Кто-то купил Вашего питомца ({pet.name})\n'
                                                          f'{round(price, 2)}💰 поступили на Ваш счет.',
                                               'random_id': 0})

                            new_name = pet.name
                            n = 1
                            while True:
                                for x in self.all_pets.get(user_id):
                                    if new_name == x.name:
                                        new_name = f'{pet.name} {n}'
                                        n += 1
                                        break
                                else:
                                    break
                            pet.name = new_name

                            self.all_pets[user_id] += [pet]

                            pet.status = 'обрел нового хозяина!'
                            pet.all_messages = []
                            pet.owner_id = user_id

                            pet.start_me()
                            answer = f'Вы купили {pet.name}. Он уже в Вашем домике!'
                        else:
                            answer = f'Недостаточно 💰 для покупки.\n' \
                                     f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 2)}💰\n' \
                                     f'Требуется: {round(price, 2)}💰'
                    else:
                        answer = f'{lot_name} не найден на рынке. Возможно, кто-то уже купил его или питомец был ' \
                                 f'переведен в другой домик. Такое иногда случается'
                        self.market.pop(lot)

                    vk_session.method('messages.send', {'user_id': int(user_id), 'message': answer, 'random_id': 0})
                    self.market_actions(user_id, 'market.take')
                    return
            else:
                answer = f'{lot_name} не найден на рынке. Возможно, кто-то уже купил его или питомец был ' \
                         f'переведен в другой домик. Такое иногда случается'
        elif args == 'market.take.no':
            self.send_pets_page(user_id, 0, list(self.market.keys()), 'market.take')
            return
        elif args.startswith('market.take.page.'):
            self.send_pets_page(user_id, int(args.replace('market.take.page.', '')), list(self.market.keys()),
                                'market.take')
            return
        elif args == 'market.take.back':
            self.market_actions(user_id)
            return

        # Продать питомца
        elif args == 'market.give':
            pets = [user_pet for user_pet in self.all_pets.get(user_id, [])
                    if user_pet not in [market_pet.get('pet') for market_pet in self.market.values()]]
            self.send_pets_page(user_id, 0, pets, 'market.give')
            return
        elif args.startswith('market.give.Pet'):
            name = args.replace('market.give.Pet.', '')
            change_users_info(user_id, new_method='market', new_args={'name': name})
            answer = 'Укажите желаемую стоимость питомца (в 💰)\n' \
                     'На следующем этапе Вы сможете подтвердить или отменить свой выбор'
            keyboard = str(json.dumps({
                "one_time": False,
                "buttons": [
                    [get_callback_button('Назад', 'negative', {'args': f'market.give'})]
                ]
            }, ensure_ascii=False))
        elif args == 'market.price':
            if is_float(message):
                price = round(float(message), 2)
                name = users_info.get(user_id, {}).get("args", {}).get("name")
                change_users_info(user_id, new_method='start')
                answer = f'Уверены, что хотите продать {name} за {round(price, 2)}💰?\n' \
                         f'Отменить выставленный лот будет НЕВОЗМОЖНО!'
                keyboard = str(json.dumps({
                    "one_time": False,
                    "buttons": [
                        [get_callback_button('Да', 'positive', {'args': f'market.give.yes.{name}.{price}'}),
                         get_callback_button('Нет', 'negative', {'args': f'market.give.no'})]
                    ]
                }, ensure_ascii=False))
            else:
                answer = 'Неверная стоимость. Допустимый формат: вещественное число\n' \
                         'Укажите желаемую стоимость питомца (в 💰)'
                keyboard = None
        elif args.startswith('market.give.yes'):
            name_price = args.replace('market.give.yes.', '')
            name = name_price[:name_price.find('.')]
            price = round(float(name_price[name_price.find('.') + 1:]), 2)
            for pet in self.all_pets[user_id]:
                if pet.name == name:
                    lot = Lot(f'Лот {self.max_lot}')
                    self.max_lot += 1

                    self.market[lot] = {'pet': pet, 'owner_id': user_id, 'price': price}
                    answer = f'Вы выставили {name} на продажу. Ему присвоен {lot.name}\n' \
                             f'Питомец все еще находится у Вас. Как только на заявку кто-то откликнется, он самостоятельно ' \
                             f'завершит все текущие действия и перейдет к новому хозяину, а его стоимость поступит на Ваш счет.'
                    break
            else:
                answer = 'Питомец не найден.'
            vk_session.method('messages.send',
                              {'user_id': int(user_id),
                               'message': answer,
                               'random_id': 0})
            self.market_actions(user_id)
            return
        elif args == 'market.give.no':
            pets = [user_pet for user_pet in self.all_pets.get(user_id, [])
                    if user_pet not in [market_pet.get('pet') for market_pet in self.market.values()]]
            self.send_pets_page(user_id, 0, pets, 'market.give')
            return
        elif args.startswith('market.give.page.'):
            pets = [user_pet for user_pet in self.all_pets.get(user_id, [])
                    if user_pet not in [market_pet.get('pet') for market_pet in self.market.values()]]
            self.send_pets_page(user_id, int(args.replace('market.give.page.', '')), pets, 'market.give')
            return
        elif args == 'market.give.back':
            self.market_actions(user_id)
            return

        elif args == 'market.back':
            self.start(user_id)
            return

        else:
            answer = 'Выберите действие'
            keyboard = str(json.dumps({
                "one_time": False,
                "buttons": [
                    [get_callback_button(f'Купить', 'primary', {'args': 'market.take'}),
                     get_callback_button('Продать', 'secondary', {'args': 'market.give'})],
                    [get_callback_button('Назад', 'negative', {'args': 'market.back'})]
                ]
            }, ensure_ascii=False))

        vk_session.method('messages.send',
                          {'user_id': int(user_id),
                           'message': answer,
                           'random_id': 0, 'keyboard': keyboard})

    def process_event(self, event):
        if event is None:
            return

        if event.type == VkBotEventType.MESSAGE_EVENT:
            user_id = str(event.obj.user_id)

            method = users_info.get(user_id, {}).get('method')
            args = event.obj.payload.get('args')

            if method == 'start':
                if args.startswith('pets'):
                    if args == 'pets':
                        self.send_pets_page(user_id, 0, self.all_pets.get(user_id, []), 'pets')

                    elif args.startswith('pets.Pet'):
                        name = args.replace('pets.Pet.', '')
                        change_users_info(user_id, new_method='Pet.process_event',
                                          new_args={'name': name})
                        for x in self.all_pets[user_id]:
                            if x.name == name:
                                x.process_event(event)
                                break

                    elif args.startswith('pets.page.'):
                        self.send_pets_page(user_id, int(args.replace('pets.page.', '')),
                                            self.all_pets.get(user_id, []), 'pets')

                    elif args == 'pets.back':
                        self.start(user_id)
                elif args == 'storage':
                    self.get_storage(user_id)
                elif args == 'store':
                    change_users_info(user_id, new_method='store')
                    self.store(user_id)
                elif args.startswith('shelter'):
                    if args == 'shelter':
                        self.shelter_actions(user_id)
                    else:
                        self.shelter_actions(user_id, args)
                elif args.startswith('market'):
                    if args == 'market':
                        self.market_actions(user_id)
                    else:
                        self.market_actions(user_id, args)
                elif args == 'give_food_to_all_pets':
                    change_users_info(user_id, new_method='give_food_to_all_pets')
                    self.give_food_to_all_pets(user_id)
                    return
                elif args == 'back':
                    vk_session.method('messages.send',
                                      {'user_id': int(user_id),
                                       'message': 'Твои питомцы будут ждать тебя, хозяин!',
                                       'random_id': 0, 'keyboard': main_keyboard})
                    change_users_info(user_id, 'autoresponder')
                    return
            elif method == 'give_food_to_all_pets':
                self.give_food_to_all_pets(user_id, event)
            elif method == 'market':
                self.market_actions(user_id, args)
            elif method == 'store':
                self.store(user_id, event)
            elif method.startswith('Pet.process_event'):
                for x in self.all_pets.get(user_id, []):
                    if x.name == users_info[user_id]['args'].get('name'):
                        x.process_event(event)
                        break
                else:
                    self.start(user_id)

        elif event.type == VkBotEventType.MESSAGE_NEW:
            user_id = str(event.obj.from_id)
            method = users_info.get(user_id, {}).get('method')

            if method.startswith('Pet.process_event'):
                for x in self.all_pets.get(user_id, []):
                    if x.name == users_info[user_id]['args'].get('name'):
                        x.process_event(event)
                        break
                else:
                    self.start(user_id)
            elif method == 'market':
                self.market_actions(user_id, event=event)

    def start(self, user_id: str):
        if self.all_pets.get(user_id) is None:
            self.all_pets[user_id] = []
        if self.all_foods.get(user_id) is None:
            self.all_foods[user_id] = 0
        if self.all_pills.get(user_id) is None:
            self.all_pills[user_id] = 0
        if self.all_max_pets.get(user_id) is None:
            self.all_max_pets[user_id] = self.start_max_pets
        if self.all_potions.get(user_id) is None:
            self.all_potions[user_id] = 0
        count_pets = len(self.all_pets.get(user_id))
        if count_pets == 0:
            pets_str = 'питомцев'
        elif count_pets == 1:
            pets_str = 'питомец'
        elif 2 <= count_pets <= 4:
            pets_str = 'питомца'
        else:
            pets_str = 'питомцев'

        buttons = []
        if len(self.all_pets.get(user_id, 0)) > 0:
            pets_str += ':\n'
            buttons += [[get_callback_button('Мои питомцы', 'positive', {'args': 'pets'})]]
            if self.all_foods.get(user_id, 0) >= len(self.all_pets.get(user_id, 0)):
                buttons[0] += [get_callback_button('Покормить всех', 'positive', {'args': 'give_food_to_all_pets'})]
        for x in self.all_pets[user_id]:
            pets_str += f'\n{x.get_status()}\n'

        buttons += [[get_callback_button('Склад', 'primary', {'args': 'storage'}),
                     get_callback_button('Магазин', 'primary', {'args': 'store'})]]
        buttons += [[get_callback_button('Приют', 'secondary', {'args': 'shelter'}),
                     get_callback_button('Рынок', 'secondary', {'args': 'market'})]]
        buttons += [[get_callback_button('Выйти из игры', 'negative', {'args': 'back'})]]
        keyboard = str(json.dumps({
            "one_time": False,
            "buttons": buttons
        }, ensure_ascii=False))

        vk_session.method('messages.send',
                          {'user_id': int(user_id),
                           'message': f'Приветствуем Вас в домике для питомцев!\n'
                                      f'У Вас {count_pets} {pets_str}\n'
                                      f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 2)}💰\n',
                           'random_id': 0, 'keyboard': keyboard})

        change_users_info(user_id, new_method='start')

    def give_food_to_all_pets_keyboard(self, user_id):
        food_per_pet = math.floor(self.all_foods.get(user_id, 0) / len(self.all_pets.get(user_id)))
        buttons = [[]]
        if food_per_pet == 0:
            return None
        if food_per_pet >= 1:
            buttons[0] += [get_callback_button('1🍎', 'positive', {'args': 'give_food_1'})]
        if food_per_pet >= 10:
            buttons[0] += [get_callback_button('10🍎', 'positive', {'args': 'give_food_10'})]
        if food_per_pet >= 50:
            buttons[0] += [get_callback_button('50🍎', 'positive', {'args': 'give_food_50'})]
        if food_per_pet >= 100:
            buttons[0] += [get_callback_button('100🍎', 'positive', {'args': 'give_food_100'})]
        if food_per_pet > 0:
            buttons += [[get_callback_button(f'{food_per_pet}🍎', 'positive', {'args': f'give_food_{food_per_pet}'})]]
        buttons += [[get_callback_button('Назад', 'negative', {'args': 'back'})]]
        return str(json.dumps({"one_time": False, "buttons": buttons}, ensure_ascii=False))

    def give_food_to_all_pets(self, user_id: str, event=None):
        keyboard = None
        if event is None:
            keyboard = self.give_food_to_all_pets_keyboard(user_id)
            if keyboard is None:
                answer = 'В Вашем хранилище недостаточно еды, чтобы покормить каждого питомца'
                vk_session.method('messages.send', {'user_id': int(user_id), 'message': answer, 'random_id': 0})
                self.start(user_id)
                return
            else:
                answer = f'Выберите количество еды для питомцев\n' \
                         f'У Вас в хранилище: {self.all_foods[user_id]}🍎'
        else:
            args = event.obj.payload.get('args')
            answer = ''
            if args.startswith('give_food_'):
                food = int(args.replace('give_food_', ''))
            else:
                self.start(user_id)
                return

            if food is not None:
                if self.all_foods.get(user_id, 0) >= food * len(self.all_pets.get(user_id)):
                    self.all_foods[user_id] -= food * len(self.all_pets.get(user_id))
                    for pet in self.all_pets.get(user_id):
                        pet.food += food
                    answer = f'Вы дали всем питомцам по {food}🍎.\n' \
                             f'У Вас в хранилище: {self.all_foods.get(user_id, 0)}🍎'
                    keyboard = self.give_food_to_all_pets_keyboard(user_id)
                    if keyboard is None:
                        answer = 'В Вашем хранилище недостаточно еды, чтобы покормить каждого питомца'
                        vk_session.method('messages.send', {'user_id': int(user_id), 'message': answer, 'random_id': 0})
                        self.start(user_id)
                        return
                else:
                    answer = f'Недостаточно 🍎.\n' \
                             f'У Вас в хранилище: {self.all_foods.get(user_id, 0)}🍎'

        if answer != '':
            vk_session.method('messages.send', {'user_id': int(user_id), 'message': answer, 'random_id': 0,
                                                'keyboard': keyboard})

    def get_storage(self, user_id: str):
        vk_session.method('messages.send',
                          {'user_id': int(user_id),
                           'message': f'Ваш склад:\n'
                                      f'{self.all_foods.get(user_id, 0)}🍎\n'
                                      f'{self.all_pills.get(user_id, 0)}💊\n'
                                      f'{self.all_potions.get(user_id, 0)}🧪\n'
                                      f'Мест для питомцев:\n'
                                      f'{self.all_max_pets.get(user_id, self.start_max_pets)}🧺',
                           'random_id': 0})

    def store(self, user_id: str, event=None):
        prices = {'pet': 10, 'food_1': 0.2, 'food_10': 1.5, 'food_100': 10, 'food_500': 40, 'pill_1': 5, 'pill_5': 20,
                  'pill_10': 30,
                  'home_1': 50, 'potion_1': 50, 'potion_5': 230, 'potion_10': 400}
        keyboard = str(json.dumps({
            "one_time": False,
            "buttons": [
                [get_callback_button('1🐣', 'positive', {'args': 'pet'})],

                [get_callback_button('1🍎', 'positive', {'args': 'food_1'}),
                 get_callback_button('10🍎', 'positive', {'args': 'food_10'}),
                 get_callback_button('100🍎', 'positive', {'args': 'food_100'}),
                 get_callback_button('500🍎', 'positive', {'args': 'food_500'})],

                [get_callback_button('1💊', 'positive', {'args': 'pill_1'}),
                 get_callback_button('5💊', 'positive', {'args': 'pill_5'}),
                 get_callback_button('10💊', 'positive', {'args': 'pill_10'})],

                [get_callback_button('1🧪', 'positive', {'args': 'potion_1'}),
                 get_callback_button('5🧪', 'positive', {'args': 'potion_5'}),
                 get_callback_button('10🧪', 'positive', {'args': 'potion_10'})],

                [get_callback_button('1🧺', 'positive', {'args': 'home_1'})],

                [get_callback_button('Назад', 'negative', {'args': 'back'})]
            ]
        }, ensure_ascii=False))
        if event is None:
            answer = f'Добро пожаловать в магазин "Все для питомцев"!\nВыберите желаемый товар:\n\n' \
                     f'Яйцо с питомцем:\n' \
                     f'1🐣 - {round(prices.get("pet"), 2)}💰\n\n' \
                     f'Еда для питомца:\n' \
                     f'1🍎 - {round(prices.get("food_1"), 2)}💰\n' \
                     f'10🍎 - {round(prices.get("food_10"), 2)}💰\n' \
                     f'100🍎 - {round(prices.get("food_100"), 2)}💰\n' \
                     f'500🍎 - {round(prices.get("food_500"), 2)}💰\n\n' \
                     f'Лекарство для питомца:\n' \
                     f'1💊 - {round(prices.get("pill_1"), 2)}💰\n' \
                     f'5💊 - {round(prices.get("pill_5"), 2)}💰\n' \
                     f'10💊 - {round(prices.get("pill_10"), 2)}💰\n\n' \
                     f'Всемогущие эликсиры:\n' \
                     f'1🧪 - {round(prices.get("potion_1"), 2)}💰\n' \
                     f'5🧪 - {round(prices.get("potion_5"), 2)}💰\n' \
                     f'10🧪 - {round(prices.get("potion_10"), 2)}💰\n\n' \
                     f'Дополнительное место для питомца:\n' \
                     f'1🧺 - {round(prices.get("home_1"), 2)}💰\n\n' \
                     f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 2)}💰'
        else:
            args = event.obj.payload.get('args')
            if args == 'pet':
                if len(self.all_pets.get(user_id)) < self.all_max_pets.get(user_id, self.start_max_pets):
                    if users_info.get(user_id, {}).get("balance", 0) >= prices.get("pet"):
                        users_info[user_id]["balance"] -= prices.get("pet")
                        self.add_pet(user_id)
                        answer = f'Вы приобрели нового питомца. Он доступен в главном меню\n' \
                                 f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 2)}💰'
                    else:
                        answer = f'Недостаточно 💰 для покупки.\n' \
                                 f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 2)}💰\n' \
                                 f'Требуется: {round(prices.get("pet"), 2)}💰'
                else:
                    answer = 'У Вас имеется максимально допустимое количество питомцев'

            elif args.startswith('food_'):
                food = int(args.replace('food_', ''))
                if users_info.get(user_id, {}).get("balance", 0) >= prices.get(args):
                    users_info[user_id]["balance"] -= prices.get(args)
                    self.all_foods[user_id] += food
                    answer = f'Вы приобрели {food}🍎.\n' \
                             f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 2)}💰\n' \
                             f'В хранилище: {self.all_foods[user_id]}🍎'
                else:
                    answer = f'Недостаточно 💰 для покупки.\n' \
                             f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 2)}💰\n' \
                             f'Требуется: {round(prices.get(args), 2)}💰'

            elif args.startswith('pill_'):
                pill = int(args.replace('pill_', ''))
                if users_info.get(user_id, {}).get("balance", 0) >= prices.get(args):
                    users_info[user_id]["balance"] -= prices.get(args)
                    self.all_pills[user_id] += pill
                    answer = f'Вы приобрели {pill}💊.\n' \
                             f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 2)}💰\n' \
                             f'В аптечке: {self.all_pills[user_id]}💊'
                else:
                    answer = f'Недостаточно 💰 для покупки.\n' \
                             f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 2)}💰\n' \
                             f'Требуется: {round(prices.get(args), 2)}💰'

            elif args.startswith('potion_'):
                potion = int(args.replace('potion_', ''))
                if users_info.get(user_id, {}).get("balance", 0) >= prices.get(args):
                    users_info[user_id]["balance"] -= prices.get(args)
                    self.all_potions[user_id] += potion
                    answer = f'Вы приобрели {potion}🧪.\n' \
                             f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 2)}💰\n' \
                             f'В хранилище: {self.all_potions[user_id]}🧪'
                else:
                    answer = f'Недостаточно 💰 для покупки.\n' \
                             f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 2)}💰\n' \
                             f'Требуется: {round(prices.get(args), 2)}💰'

            elif args == 'home_1':
                if users_info.get(user_id, {}).get("balance", 0) >= prices.get(args):
                    users_info[user_id]["balance"] -= prices.get(args)
                    self.all_max_pets[user_id] += 1
                    answer = f'Вы приобрели 1🧺.\n' \
                             f'Всего доступно: {self.all_max_pets[user_id]}🧺'
                else:
                    answer = f'Недостаточно 💰 для покупки.\n' \
                             f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 2)}💰\n' \
                             f'Требуется: {round(prices.get(args), 2)}💰'

            elif args == 'back':
                self.start(user_id)
                return
            else:
                answer = 'В магазине нет данного товара'

        vk_session.method('messages.send',
                          {'user_id': int(user_id),
                           'message': answer,
                           'random_id': 0, 'keyboard': keyboard})


class Lot:
    name: str

    def __init__(self, name):
        self.name = name


def is_float(string):
    """ Проверка: является ли сообщение числом.
    :param string: str.

    :return: True, если сообщение - число.
        False - иначе.
    """
    try:
        float(string)
        return True
    except ValueError:
        return False


class TemplatePet:
    ages: dict
    sexes: list
    level_0: dict
    level_1: dict
    level_2: dict
    level_3: dict
    legendary: dict

    diseases: dict
    works: dict

    # in seconds
    time_between_satiety = 60 * 30

    def __init__(self):
        self.ages = {'Яйцо': 60 * 10, 'Младенчество': 60 * 20, 'Детство': 60 * 60 * 24, 'Юность': 60 * 60 * 24 * 2,
                     'Молодость': 60 * 60 * 24 * 7, 'Зрелость': 60 * 60 * 24 * 21, 'Старость': 0}
        self.sexes = ['Женщина', 'Мужчина']

        # food_per_meal=0, health=0, intellect=0, power=0, speed=0, industriousness=0, neatness=0, luck=0, work_time_night=False
        self.level_0 = {'Миньон': [Minion, (2, 30, 10, 30, 40, 80, 20, 0, False)],
                        'Грут': [FloraColossus, (2, 30, 80, 30, 60, 30, 30, 0, False)],
                        'Вампир': [Vampire, (2, 50, 20, 30, 100, 30, 30, 0, True)],
                        'Ведьма': [Witch, (2, 50, 40, 20, 50, 40, 40, 0, True)]
                        # 'Дракон': [Dragon, (1.5, 30, 80, 30, 80, 30, 30, 0, False)],  # TODO: Проработать характеристики
                        # 'Пират': [Pirate, (1.5, 30, 80, 30, 80, 30, 30, 0, False)]  # TODO: Проработать характеристики
                        # 'Гунган': self.get_features(30, 5, 15, 40, 40, 30, 0, False),
                        }  # TODO: Заполнить!
        self.level_1 = {'Смурф': (40, 0, 0, 0, 0, 0, 0, False),
                        }  # TODO: Заполнить!
        self.level_2 = {'На\'Ви': (50, 0, 0, 0, 0, 0, 0, False),
                        }  # TODO: Заполнить!
        self.level_3 = {'Автобот': (70, 0, 0, 0, 0, 0, 0, False)
                        }  # TODO: Заполнить!
        self.legendary = {'Джа-Джа Бинкс': (80, 0, 0, 0, 0, 0, 0, False),
                          'Бамблби': (100, 0, 0, 0, 0, 0, 0, False),
                          'Оптимус Прайм': (100, 0, 0, 0, 0, 0, 0, False),
                          }  # TODO: Заполнить!

        # Заболевания влияют на основные характеристики в пределах -(0 - 100), но не более заданного в характеристиках
        self.diseases = {
            'Простуда': {'treatment': 2, 'effects': self.get_features(health=10, speed=10, industriousness=10)},
            'Депрессия': {'treatment': 2, 'effects': self.get_features(food_per_meal=-3, industriousness=100)},
            'Ожирение': {'treatment': 3, 'effects': self.get_features(food_per_meal=-5, health=10, speed=20)},
            'Вывих ноги': {'treatment': 4, 'effects': self.get_features(health=10, power=100, speed=100)},
            'Грипп': {'treatment': 3, 'effects': self.get_features(health=20, speed=20, industriousness=20)}
        }  # TODO: Заполнить!
        # health=0, intellect=0, power=0, speed=0, industriousness=0, neatness=0, luck=0, work_time_night=False
        self.works = {
            'Отладчик бота': {
                'skills': {'intellect': 80, 'industriousness': 50},
                'salary_per_min': 0.15, 'salary_in': 'money'},
            'Переворачиватель пингвинов': {
                'skills': {'health': 40, 'power': 40, 'industriousness': 40, 'neatness': 40},
                'salary_per_min': 0.1, 'salary_in': 'money'},
            'Преподаватель физики': {
                'skills': {'intellect': 100, 'industriousness': 40},
                'salary_per_min': 0.15, 'salary_in': 'money'},
            'Дегустатор сладких тортиков': {
                'skills': {'food_per_meal': 5, 'health': 60, 'industriousness': 40},
                'salary_per_min': 2, 'salary_in': 'food'},
            'Искатель конца скотча': {
                'skills': {'intellect': 70, 'industriousness': 70, 'neatness': 70},
                'salary_per_min': 0.2, 'salary_in': 'money'},
            'Дрессировщик сов': {
                'skills': {'power': 20, 'speed': 20, 'neatness': 20},
                'salary_per_min': 0.1, 'salary_in': 'money'},
            'Искатель акций и скидок': {
                'skills': {'industriousness': 50, 'luck': 50},
                'salary_per_min': 0.15, 'salary_in': 'money'}
            # 'Двойник Илона Маска': {
            #     'skills': {'health': 100, 'intellect': 100, 'power': 100, 'speed': 100, 'industriousness': 100,
            #                'neatness': 100, 'luck': 100},
            #     'salary_per_min': 0.5, 'salary_in': 'money'},
        }

    @staticmethod
    def get_features(food_per_meal=0, health=0, intellect=0, power=0, speed=0, industriousness=0, neatness=0,
                     luck=0, work_time_night=False):
        return {'food_per_meal': food_per_meal,  # Количество еды за прием пищи
                'health': health,  # Здоровье
                'intellect': intellect,  # Интеллект
                'power': power,  # Сила
                'speed': speed,  # Скорость
                'industriousness': industriousness,  # Трудолюбие
                'neatness': neatness,  # Аккуратность
                'luck': luck,  # Шанс получения выгоды при ЧП
                'work_time_night': work_time_night  # False = День, True = Ночь
                }

    @staticmethod
    def translate(item):
        translate = {'food_per_meal': 'Количество еды за прием пищи',
                     'health': 'Здоровье',
                     'intellect': 'Интеллект',
                     'power': 'Сила',
                     'speed': 'Скорость',
                     'industriousness': 'Трудолюбие',
                     'neatness': 'Аккуратность',
                     'luck': 'Удача',
                     'work_time_night': 'Время работы'}
        return translate.get(item, None)

    def get_string_features(self, features):

        answer = str()
        for x in features.items():
            if x[0] == 'work_time_night':
                answer += f'{self.translate(x[0])}: {"Ночь" if x[1] else "День"}\n'
            else:
                answer += f'{self.translate(x[0])}: {x[1]}/100\n'
        return answer


class Pet(TemplatePet):
    game_pets: GamePets
    all_messages: list

    owner_id: str
    name: str
    age: int
    sex: str
    type: str
    level: dict

    status: str

    lives: int
    disease = None

    satiety: int
    food: int

    identified_pet = None
    features_permanent: dict
    features_now: dict

    timer_age = None
    time_finish_age: datetime

    timer_satiety = None

    action = None
    work_name: str
    timer_action = None
    time_start_action: datetime
    time_finish_action: datetime

    bones = 0
    max_bones = 10
    food_from_bone = 1 / 5

    is_body_studied = False

    def __init__(self, all_pets: GamePets, owner_id: str):
        super().__init__()
        self.game_pets = all_pets
        self.all_messages = list()
        self.owner_id = owner_id

        name = 'Питомец 1'
        n = 2
        while True:
            for x in self.game_pets.all_pets.get(owner_id, []):
                if name == x.name:
                    name = f'Питомец {n}'
                    n += 1
                    break
            else:
                break

        self.name = name

        # r = random.randint(0, 1000)
        r = 1000
        if r == 0:
            self.level = self.legendary
        elif 0 < r <= 20:
            self.level = self.level_3
        elif 20 < r <= 100:
            self.level = self.level_2
        elif 100 < r <= 250:
            self.level = self.level_1
        else:
            self.level = self.level_0
        self.type = random.choice(list(self.level))
        self.features_permanent = self.get_features(*self.level.get(self.type)[1]).copy()
        self.features_now = self.features_permanent.copy()

        self.sex = random.choice(self.sexes)
        self.status = 'пока еще неопознанное яйцо'

        self.age = 0
        self.timer_age = threading.Timer(self.ages[list(self.ages.keys())[self.age]], self.next_age)
        self.timer_age.start()
        self.time_finish_age = datetime.now(tz=tz) + timedelta(seconds=self.ages[list(self.ages.keys())[self.age]])

        self.lives = 100
        self.disease = None

        self.satiety = 100
        self.food = 0

        self.identified_pet = self.level.get(self.type)[0](self)

    def stop_me(self):
        if self.timer_age is not None:
            self.timer_age.cancel()
            self.timer_age = None

        if self.timer_action is not None:
            if self.action is not None:
                if self.action.startswith('работает'):
                    self.work('work.finish')
                else:
                    answer = f'{self.name} не смог завершить начатое действие и вернулся домой'
                    if users_info.get(self.owner_id, {}).get('args', {}) is not None and \
                            users_info.get(self.owner_id, {}).get('args', {}).get('name', '') == self.name:
                        vk_session.method('messages.send',
                                          {'user_id': int(self.owner_id),
                                           'message': answer,
                                           'random_id': 0})
                    else:
                        self.all_messages += [(datetime.now(tz=tz).strftime('%d.%m.%Y %H:%M:%S'), answer)]

                self.action = None

            self.timer_action.cancel()
            self.timer_action = None

        if self.timer_satiety is not None:
            self.timer_satiety.cancel()
            self.timer_satiety = None

    def start_me(self):
        super().__init__()
        if self.type in self.level_0:
            self.level = self.level_0
        elif self.type in self.level_1:
            self.level = self.level_1
        elif self.type in self.level_2:
            self.level = self.level_2
        elif self.type in self.level_3:
            self.level = self.level_3
        elif self.type in self.legendary:
            self.level = self.legendary

        self.features_permanent = self.get_features(*self.level.get(self.type)[1]).copy()
        for key in self.features_permanent.keys():
            if self.features_now.get(key) is None:
                self.features_now[key] = self.features_permanent.get(key)

        if self.time_finish_age > datetime.now(tz=tz):
            self.timer_age = threading.Timer(round((self.time_finish_age - datetime.now(tz=tz)).total_seconds()),
                                             self.next_age)
            self.timer_age.start()
        else:
            self.next_age()

        self.timer_satiety = threading.Timer(self.time_between_satiety, self.update_satiety)
        self.timer_satiety.start()

    def is_male(self):
        return True if self.sex == 'Мужчина' else False

    def get_main_keyboard(self):
        buttons = []
        buttons += [[get_callback_button(f'{self.name}', 'secondary', {'args': 'get_status'})]]
        if self.disease is not None:
            buttons += [[get_callback_button(f'Вылечить ({self.diseases[self.disease]["treatment"]}💊)', 'negative',
                                             {'args': 'heal'}),
                         get_callback_button('Покормить', 'positive', {'args': 'give_food'})]]
        elif self.lives < 100:
            buttons += [[get_callback_button(f'Восстановить жизни (1💊)',
                                             'negative', {'args': 'heal'}),
                         get_callback_button('Покормить', 'positive', {'args': 'give_food'})]]
        else:
            buttons += [[get_callback_button('Покормить', 'positive', {'args': 'give_food'})]]
        buttons += [
            [get_callback_button('Действия', 'primary', {'args': 'actions'})],

            [get_callback_button('Время до следующей стадии', 'primary', {'args': 'get_time_to_next_age'})],

            [get_callback_button('Справка', 'primary', {'args': 'get_info_main'}),
             get_callback_button('Информация', 'primary', {'args': 'get_info_all'})],

            [get_callback_button('Сменить имя', 'negative', {'args': 'set_name'}),
             get_callback_button('Назад', 'negative', {'args': 'back'})]
        ]
        return str(json.dumps({"one_time": False, "buttons": buttons}, ensure_ascii=False))

    def process_event(self, event=None, message=None):
        if event is None:
            if message is None:
                message = f'~{self.name}~'
            vk_session.method('messages.send',
                              {'user_id': int(self.owner_id),
                               'message': message,
                               'random_id': 0, 'keyboard': self.get_main_keyboard()})
            return

        if event.type == VkBotEventType.MESSAGE_EVENT:
            method = users_info.get(self.owner_id, {}).get('method')
            args = event.obj.payload.get('args')

            if method == 'Pet.process_event':
                keyboard = self.get_main_keyboard()
                if args == 'get_status':
                    answer = self.get_status()
                elif args == 'heal':
                    answer = self.heal()
                    keyboard = self.get_main_keyboard()
                elif args == 'give_food':
                    change_users_info(self.owner_id, new_method='Pet.process_event.give_food',
                                      new_args=users_info.get(self.owner_id, {}).get('args'))
                    self.give_food()
                    return
                elif args == 'actions':
                    change_users_info(self.owner_id, new_method='Pet.process_event.actions',
                                      new_args=users_info.get(self.owner_id, {}).get('args'))
                    self.actions()
                    return
                elif args == 'get_time_to_next_age':
                    answer = self.get_time_to_next_age()
                elif args == 'get_info_main':
                    answer = self.get_info(False)
                elif args == 'get_info_all':
                    answer = self.get_info(True)
                elif args == 'set_name':
                    answer = 'Введите новое имя питомца (длиной от 1 до 30 символов)'
                    change_users_info(self.owner_id, new_method='Pet.process_event.set_name',
                                      new_args=users_info.get(self.owner_id, {}).get('args'))
                elif args == 'back':
                    change_users_info(self.owner_id, new_method='start')
                    self.game_pets.send_pets_page(self.owner_id, 0, self.game_pets.all_pets.get(self.owner_id, []),
                                                  'pets')
                    return
                else:
                    keyboard = self.get_main_keyboard()
                    answer = f'~{self.name}~'
                    for m in self.all_messages:
                        answer += f'\n{m[0]}: {m[1]}'
                    self.all_messages.clear()

                vk_session.method('messages.send',
                                  {'user_id': int(self.owner_id),
                                   'message': answer,
                                   'random_id': 0, 'keyboard': keyboard})
            elif method == 'Pet.process_event.give_food':
                self.give_food(event)
            elif method == 'Pet.process_event.actions':
                self.actions(event)

        elif event.type == VkBotEventType.MESSAGE_NEW:
            user_id = str(event.obj.from_id)
            method = users_info.get(user_id, {}).get('method')
            message = event.obj.text

            if method == 'Pet.process_event.set_name':
                self.set_name(message)

    def set_name(self, name):
        name = name.strip()
        if name is not None and 30 >= len(name) > 0:
            if name not in [x.name for x in self.game_pets.all_pets[self.owner_id]]:
                self.name = name
                answer = f'Имя питомца изменено на {name}'
            else:
                answer = 'Питомец с таким именем уже существует'
        else:
            answer = 'Недопустимое имя питомца'

        vk_session.method('messages.send',
                          {'user_id': int(self.owner_id),
                           'message': answer,
                           'random_id': 0, 'keyboard': self.get_main_keyboard()})
        change_users_info(self.owner_id, new_method='Pet.process_event',
                          new_args={'name': self.name})

    def next_age(self):
        self.age += 1
        if list(self.ages.keys())[self.age] == 'Младенчество':
            self.timer_satiety = threading.Timer(self.time_between_satiety, self.update_satiety)
            self.timer_satiety.start()
        elif list(self.ages.keys())[self.age] == 'Старость':
            self.leave(True)
            return
        self.status = f'вырос до стадии "{list(self.ages.keys())[self.age]}"'
        self.timer_age = threading.Timer(self.ages[list(self.ages.keys())[self.age]], self.next_age)
        self.timer_age.start()
        self.time_finish_age = datetime.now(tz=tz) + timedelta(seconds=self.ages[list(self.ages.keys())[self.age]])

        answer = f'Ура! {self.name} {self.status}'
        if users_info.get(self.owner_id, {}).get('args', {}) is not None and \
                users_info.get(self.owner_id, {}).get('args', {}).get('name', '') == self.name:
            vk_session.method('messages.send',
                              {'user_id': int(self.owner_id),
                               'message': answer,
                               'random_id': 0})
            self.update_actions_to_new_age()
        else:
            self.all_messages += [(datetime.now(tz=tz).strftime('%d.%m.%Y %H:%M:%S'), answer)]

    def update_actions_to_new_age(self):
        if users_info.get(self.owner_id, {}).get('method') == 'Pet.process_event.actions':
            self.actions()

    def get_time_to_next_age(self):
        time = self.time_finish_age - datetime.now(tz=tz)
        if time.days == 1:
            days = 'день'
        elif 2 <= time.days <= 4:
            days = 'дня'
        else:
            days = 'дней'
        return f'До следующей стадии "{list(self.ages.keys())[self.age + 1]}" еще {time.days} {days}, {timedelta(seconds=time.seconds)}'

    def get_food_keyboard(self):
        all_food = self.game_pets.all_foods.get(self.owner_id, 0)
        buttons = [[]]
        if all_food == 0:
            return None
        if all_food >= 1:
            buttons[0] += [get_callback_button('1🍎', 'positive', {'args': 'give_food_1'})]
        if all_food >= 10:
            buttons[0] += [get_callback_button('10🍎', 'positive', {'args': 'give_food_10'})]
        if all_food >= 50:
            buttons[0] += [get_callback_button('50🍎', 'positive', {'args': 'give_food_50'})]
        if all_food >= 100:
            buttons[0] += [get_callback_button('100🍎', 'positive', {'args': 'give_food_100'})]
        buttons += [[get_callback_button(f'{all_food}🍎', 'positive', {'args': 'give_food_all'})]]
        buttons += [[get_callback_button('Назад', 'negative', {'args': 'back'})]]
        return str(json.dumps({"one_time": False, "buttons": buttons}, ensure_ascii=False))

    def give_food(self, event=None):
        keyboard = None
        if event is None:
            keyboard = self.get_food_keyboard()
            if keyboard is None:
                change_users_info(self.owner_id, new_method='Pet.process_event',
                                  new_args=users_info.get(self.owner_id, {}).get('args'))
                answer = 'В Вашем хранилище нет еды'
                keyboard = self.get_main_keyboard()
            else:
                answer = f'Выберите количество еды для питомца\n' \
                         f'У него в кормушке: {round(self.food, 2)}🍎\n' \
                         f'У Вас в хранилище: {self.game_pets.all_foods[self.owner_id]}🍎'
        else:
            args = event.obj.payload.get('args')
            food = None
            answer = ''
            if args.startswith('give_food_'):
                if args == 'give_food_all':
                    food = self.game_pets.all_foods.get(self.owner_id)
                else:
                    food = int(args.replace('give_food_', ''))
            else:
                change_users_info(self.owner_id, new_method='Pet.process_event',
                                  new_args=users_info.get(self.owner_id, {}).get('args'))
                answer = 'Вы закончили кормление питомца'
                keyboard = self.get_main_keyboard()

            if food is not None:
                if self.game_pets.all_foods[self.owner_id] >= food:
                    self.game_pets.all_foods[self.owner_id] -= food
                    self.food += food
                    answer = f'Вы дали питомцу {food}🍎.\n' \
                             f'У него в кормушке: {round(self.food, 2)}🍎\n' \
                             f'У Вас в хранилище: {self.game_pets.all_foods[self.owner_id]}🍎'
                    keyboard = self.get_food_keyboard()
                    if keyboard is None:
                        change_users_info(self.owner_id, new_method='Pet.process_event',
                                          new_args=users_info.get(self.owner_id, {}).get('args'))
                        answer = 'В Вашем хранилище нет еды'
                        keyboard = self.get_main_keyboard()
                else:
                    answer = f'Недостаточно 🍎.\n' \
                             f'У Вас в хранилище: {self.game_pets.all_foods[self.owner_id]}🍎'

        if answer != '':
            vk_session.method('messages.send',
                              {'user_id': int(self.owner_id),
                               'message': answer,
                               'random_id': 0, 'keyboard': keyboard})

    def update_satiety(self):
        if self.bones > 0:
            self.food += self.food_from_bone * self.bones

        food_per_meal = self.features_now.get('food_per_meal', 2)
        satiety_per_meal = food_per_meal * 2

        self.satiety -= satiety_per_meal if self.satiety >= satiety_per_meal else self.satiety

        while self.food >= food_per_meal:
            if self.satiety < 100:
                self.food -= food_per_meal
                self.satiety += satiety_per_meal if self.satiety <= 100 - satiety_per_meal else 100 - self.satiety
                self.status = f'покушал{"" if self.is_male() else "a"}'
            else:
                break
        else:
            self.status = 'голодает'

        if self.satiety == 0:
            if self.disease is None:
                self.fall_ill()
            else:
                self.lives -= (100 - self.features_now.get('health', 0)) / 10

            if self.lives <= 0:
                self.leave(False)
                return

        elif self.satiety == 100 and self.lives < 100:
            self.lives += self.features_now.get('health', 0) / 10
            if self.lives > 100:
                self.lives = int(100)

        self.timer_satiety = threading.Timer(self.time_between_satiety, self.update_satiety)
        self.timer_satiety.start()

    def fall_ill(self):
        self.disease = random.choice(list(self.diseases))
        self.status = f'заболел{"" if self.is_male() else "a"} ({self.disease})'
        for x in self.diseases.get(self.disease).get('effects').items():
            if self.features_now.get(x[0]) is None:  # TODO: Временное
                self.features_now[x[0]] = self.features_permanent.get(x[0])
            self.features_now[x[0]] -= x[1] if self.features_now[x[0]] > x[1] else self.features_now[x[0]]

    def leave(self, is_elderly):
        self.game_pets.delete_pet(self.owner_id, self)
        if is_elderly:
            vk_session.method('messages.send',
                              {'user_id': int(self.owner_id),
                               'message': f'Питомец {self.name} вырос совсем большим и был переведен в другой домик',
                               'random_id': 0})
        else:
            vk_session.method('messages.send',
                              {'user_id': int(self.owner_id),
                               'message': f'Питомец {self.name} стал совсем слаб, поэтому его забрали в другой домик',
                               'random_id': 0})
        if users_info.get(self.owner_id, {}).get('args', {}) is not None and \
                users_info.get(self.owner_id, {}).get('args', {}).get('name', '') == self.name:
            self.game_pets.start(self.owner_id)
        del self

    def heal(self):
        if self.disease is None:
            treatment = 1
            answer = 'Вы восстановили жизни питомца!'
        else:
            treatment = self.diseases.get(self.disease).get('treatment')
            answer = 'Вы вылечили питомца!'

        if self.game_pets.all_pills.get(self.owner_id, 0) >= treatment:
            self.game_pets.all_pills[self.owner_id] -= treatment
            self.disease = None
            self.features_now.clear()
            self.features_now = self.features_permanent.copy()
            self.lives = 100
            self.status = f'недавно вылечил{"ся" if self.is_male() else "aсь"}'
        else:
            answer = f'Недостаточно 💊 для лечения.\n' \
                     f'У Вас в аптечке: {self.game_pets.all_pills.get(self.owner_id)}💊\n' \
                     f'Требуется: {treatment}💊'
        return answer

    def get_status(self):
        if self.age == 0:
            return f'{self.name} {self.status}'
        else:
            return f'{self.name} {self.status}\nДействие: ' \
                   f'{self.action if self.action is not None else "Свободен" if self.is_male() else "Свободна"}'

    def get_info(self, is_all):
        if self.age == 0:
            return (f'\n'
                    f'~Информация о питомце~\n'
                    f'Имя: {self.name}\n'
                    f'Возраст: {list(self.ages.keys())[self.age]}\n'
                    f'Статус: {self.status}\n'
                    f'Еда в кормушке: {round(self.food, 2)}\n\n')
        elif not is_all:
            return (f'\n'
                    f'~Информация о питомце~\n'
                    f'Имя: {self.name}\n'
                    f'Возраст: {list(self.ages.keys())[self.age]}\n'
                    f'Статус: {self.status}\n'
                    f'Жизни: {round(self.lives, 2)}/100\n'
                    f'Болезнь: {"Нет" if self.disease is None else self.disease}\n'
                    f'Сытость: {self.satiety}/100\n'
                    f'Еда в кормушке: {round(self.food, 2)}\n\n')
        else:
            return (f'\n'
                    f'~Информация о питомце~\n'
                    f'Имя: {self.name}\n'
                    f'Возраст: {list(self.ages.keys())[self.age]}\n'
                    f'Пол: {self.sex}\n'
                    f'Тип: {self.type}\n'
                    f'Статус: {self.status}\n'
                    f'Жизни: {round(self.lives, 2)}/100\n'
                    f'Болезнь: {"Нет" if self.disease is None else self.disease}\n'
                    f'Сытость: {self.satiety}/100\n'
                    f'Еда в кормушке: {round(self.food, 2)}\n\n'

                    f'Характеристики:\n'
                    f'{self.get_string_features(self.features_now)}')

    def get_time_to_finish_action(self):
        if self.action is None:
            return f'До завершения осталось 0 секунд'
        else:
            if self.action.startswith('работает'):
                time = datetime.now(tz=tz) - self.time_start_action
                text = 'С начала прошло'
            else:
                time = self.time_finish_action - datetime.now(tz=tz)
                text = 'До завершения осталось'
            if time.days == 1:
                days = 'день'
            elif 2 <= time.days <= 4:
                days = 'дня'
            else:
                days = 'дней'
            return f'{text} {time.days} {days}, {timedelta(seconds=time.seconds)}'

    def get_actions_keyboard(self):
        buttons = []

        if self.age >= list(self.ages.keys()).index('Молодость'):
            if self.action is not None and self.action.startswith('работает'):
                buttons += [[get_callback_button('Вернуться с работы', 'negative', {'args': 'work.finish'})]]
            elif self.action is None:
                buttons += [[get_callback_button('Идти на работу', 'positive', {'args': 'work'})]]

        if self.action is None:
            if self.age >= list(self.ages.keys()).index('Детство'):
                if self.bones < self.max_bones:
                    buttons += [
                        [get_callback_button('Посадить косточку (1🍎, 1мин)', 'secondary', {'args': 'plant_bone'})]]
            if self.age >= list(self.ages.keys()).index('Юность'):
                if self.age != list(self.ages.keys()).index('Зрелость'):
                    for value in self.features_now.values():
                        if value < 100:
                            buttons += [[get_callback_button('Принять эликсир', 'secondary', {'args': 'potion'})]]
                            break
                else:
                    buttons += [[get_callback_button('Принять эликсир', 'secondary', {'args': 'potion'})]]
                buttons += [[get_callback_button('Соревнования (0.5💰, 30мин)', 'secondary', {'args': 'competition'})]]
            buttons += self.identified_pet.get_action_buttons()

        buttons += [[get_callback_button('Назад', 'negative', {'args': 'back'})]]
        return str(json.dumps({"one_time": False, "buttons": buttons}, ensure_ascii=False))

    def check_action(self, args):
        answer = None
        if args == 'plant_bone':
            answer = self.plant_bone()
        elif args.startswith('competition'):
            answer = self.competition(args)
        elif args.startswith('work'):
            answer = self.work(args)
        elif args.startswith('potion'):
            answer = self.potion(args)

        return answer

    def actions(self, event=None):
        answer = f'Вот, что умеет {self.name}'
        keyboard = None

        if self.age == list(self.ages.keys()).index('Яйцо'):
            answer = f'Питомец {self.name} еще мал для самостоятельных действий'
            change_users_info(self.owner_id, new_method='Pet.process_event',
                              new_args=users_info.get(self.owner_id, {}).get('args'))
            self.process_event(message=answer)
            return

        elif event is None:
            if self.action is not None and not self.action.startswith('работает'):
                answer = f'{self.name} {self.action} и не может выполнить еще одно действие.\n' \
                         f'{self.get_time_to_finish_action()}'

                vk_session.method('messages.send',
                                  {'user_id': int(self.owner_id),
                                   'message': answer,
                                   'random_id': 0})

                change_users_info(self.owner_id, new_method='Pet.process_event',
                                  new_args=users_info.get(self.owner_id, {}).get('args'))
                self.process_event()
                return
            else:
                keyboard = self.get_actions_keyboard()

        elif event.type == VkBotEventType.MESSAGE_EVENT:
            args = event.obj.payload.get('args')
            if args == 'back':
                change_users_info(self.owner_id, new_method='Pet.process_event',
                                  new_args=users_info.get(self.owner_id, {}).get('args'))
                self.process_event()
                return

            elif self.action is not None and not self.action.startswith('работает'):
                answer = f'{self.name} {self.action} и не может выполнить еще одно действие.\n' \
                         f'{self.get_time_to_finish_action()}'

                vk_session.method('messages.send',
                                  {'user_id': int(self.owner_id),
                                   'message': answer,
                                   'random_id': 0})

                change_users_info(self.owner_id, new_method='Pet.process_event',
                                  new_args=users_info.get(self.owner_id, {}).get('args'))
                self.process_event()
                return

            else:
                answer = self.check_action(args)
                if answer is None:
                    answer = self.identified_pet.check_action(args)
                    if answer is None:
                        answer = f'{self.name} еще не умеет это делать'

        if answer != -1:
            if keyboard is None:
                keyboard = self.get_actions_keyboard()
            vk_session.method('messages.send',
                              {'user_id': int(self.owner_id),
                               'message': answer,
                               'random_id': 0, 'keyboard': keyboard})

    def send_message_action(self, answer):
        if users_info.get(self.owner_id, {}).get('args', {}) is not None and \
                users_info.get(self.owner_id, {}).get('args', {}).get('name', '') == self.name:

            if users_info.get(self.owner_id).get('method') == 'Pet.process_event.actions':
                keyboard = self.get_actions_keyboard()
            else:
                keyboard = None
            vk_session.method('messages.send',
                              {'user_id': int(self.owner_id), 'message': answer, 'random_id': 0, 'keyboard': keyboard})
        else:
            self.all_messages += [(datetime.now(tz=tz).strftime('%d.%m.%Y %H:%M:%S'), answer)]

    def plant_bone(self, is_finish=False):
        if is_finish:
            self.action = None
            success = max(20, self.features_now.get('neatness') * 0.6 + self.features_now.get('luck') * 0.6)
            if random.randint(0, 100) <= success:
                self.bones += 1
                answer = f'{self.name} посадил{"" if self.is_male() else "a"} косточку!'
            else:
                answer = f'{self.name} посадил{"" if self.is_male() else "a"} косточку, но она не прижилась.'
            answer += f'\nВсего посажено {self.bones}🌳\n' \
                      f'Они приносят {round(self.bones * self.food_from_bone, 2)}🍎/{int(self.time_between_satiety / 60)}мин'
            self.action = None
            self.send_message_action(answer)
            return
        elif self.bones >= self.max_bones:
            answer = f'{self.name} посадил{"" if self.is_male() else "a"} максимально возможное количество 🌳.'
        elif self.food >= 1:
            self.food -= 1
            self.action = 'сажает косточку'
            self.timer_action = threading.Timer(60, function=self.plant_bone, args=[True])
            self.timer_action.start()
            self.time_finish_action = datetime.now(tz=tz) + timedelta(seconds=60)
            answer = f'{self.name} начал{"" if self.is_male() else "a"} сажать косточку.'
        else:
            answer = f'У {self.name} недостаточно 🍎, чтобы посадить косточку.'
        answer += f'\nВсего посажено {self.bones}🌳\n' \
                  f'Они приносят {round(self.bones * self.food_from_bone, 2)}🍎/{int(self.time_between_satiety / 60)}мин'

        return answer

    def competition(self, args, is_finish=False):
        def go():
            if not is_finish:
                if users_info.get(self.owner_id, {}).get("balance", 0) >= 0.5:
                    users_info[self.owner_id]["balance"] -= 0.5
                    self.action = f'участвует в соревнованиях по {text_competition}'
                    self.timer_action = threading.Timer(60 * 30, function=self.competition,
                                                        args=[args, True])
                    self.timer_action.start()
                    self.time_finish_action = datetime.now(tz=tz) + timedelta(seconds=60 * 30)
                    answer_ = f'{self.name} начал{"" if self.is_male() else "a"} сражаться за первое место ' \
                              f'в соревнованиях по {text_competition}'
                else:
                    answer_ = f'Недостаточно 💰 для вступительного взноса.\n' \
                              f'Ваш баланс: {round(users_info.get(self.owner_id, {}).get("balance", 0), 2)}💰\n' \
                              f'Требуется: 0.5💰'
            else:
                if random.randint(1, 110) <= success:
                    users_info[self.owner_id]["balance"] += 10
                    answer_ = f'{self.name} выиграл{"" if self.is_male() else "a"} соревнования по {text_competition} ' \
                              f'и заработал{"" if self.is_male() else "a"} 10💰'
                else:
                    if self.features_now.get('luck', 0) > 0 and random.randint(0, 100) <= self.features_now.get('luck'):
                        users_info[self.owner_id]["balance"] += 5
                        answer_ = f'{self.name} ничего не выиграл{"" if self.is_male() else "a"} на соревнованиях ' \
                                  f'по {text_competition}, но удача оказалась на {"его" if self.is_male() else "ее"} ' \
                                  f'стороне, и спонсоры выдали поощрительный приз 5💰'
                    else:
                        answer_ = f'{self.name} занял{"" if self.is_male() else "a"} {random.randint(4, 100)} место ' \
                                  f'на соревнованиях по {text_competition} и ничего не ' \
                                  f'заработал{"" if self.is_male() else "a"}'

            return answer_

        if args == 'competition':
            keyboard = None
            if users_info.get(self.owner_id, {}).get("balance", 0) >= 0.5:
                answer = 'Выберите направление соревнования'
                keyboard = str(json.dumps(
                    {"one_time": True,
                     "buttons": [
                         [get_callback_button('Наука', 'primary', {'args': 'competition.science'})],
                         [get_callback_button('Перетягивание каната', 'primary', {'args': 'competition.tug_of_war'})],
                         [get_callback_button('Бег', 'primary', {'args': 'competition.running'})],
                         [get_callback_button('Оригами', 'primary', {'args': 'competition.origami'})],
                         [get_callback_button('Назад', 'negative', {'args': 'competition.back'})]
                     ]
                     }, ensure_ascii=False))
            else:
                answer = f'Недостаточно 💰 для вступительного взноса.\n' \
                         f'Ваш баланс: {round(users_info.get(self.owner_id, {}).get("balance", 0), 2)}💰\n' \
                         f'Требуется: 0.5💰'
            vk_session.method('messages.send',
                              {'user_id': int(self.owner_id),
                               'message': answer,
                               'random_id': 0, 'keyboard': keyboard})
            return -1
        elif args == 'competition.back':
            self.actions()
            return -1
        elif args == 'competition.science':
            success = self.features_now.get('intellect', 0)
            text_competition = 'науке'
        elif args == 'competition.tug_of_war':
            success = self.features_now.get('intellect', 0) * 0.2 + \
                      self.features_now.get('power', 0) * 0.8
            text_competition = 'перетягиванию каната'
        elif args == 'competition.running':
            success = self.features_now.get('speed', 0)
            text_competition = 'бегу'
        elif args == 'competition.origami':
            success = self.features_now.get('neatness', 0)
            text_competition = 'оригами'
        else:
            answer = 'Данные соревнования сейчас не проводятся'
            return answer

        if is_finish:
            self.action = None
            self.send_message_action(go())
            return -1
        vk_session.method('messages.send',
                          {'user_id': int(self.owner_id),
                           'message': go(),
                           'random_id': 0, 'keyboard': self.get_actions_keyboard()})
        return -1

    def work(self, args):
        if args == 'work.back':
            self.actions()
            return -1

        if (self.features_now.get('work_time_night') and
                datetime_time(hour=9) <= datetime.now(tz=tz).time() < datetime_time(hour=21)):
            self.action = None
            self.send_message_action(f'{self.name} работает только с 21:00 до 9:00')
            return -1
        elif (not self.features_now.get('work_time_night') and
              (datetime_time(hour=21) <= datetime.now(tz=tz).time() <= datetime_time(hour=23, minute=59, second=59) or
               datetime_time(hour=0) <= datetime.now(tz=tz).time() < datetime_time(hour=9))):
            self.action = None
            self.send_message_action(f'{self.name} работает только с 9:00 до 21:00')
            return -1
        else:
            if self.disease is not None:
                self.send_message_action(f'{self.name} болеет ({self.disease}) и не может пойти на работу')
                return -1

            all_works = {**self.works, **self.identified_pet.works}
            if args == 'work':
                buttons = []
                for work_name in list(all_works.keys()):
                    skills = all_works.get(work_name).get('skills')
                    for skill in list(skills.keys()):
                        if skills.get(skill) > self.features_now.get(skill):
                            break
                    else:
                        buttons += [[get_callback_button(
                            f'{work_name} '
                            f'[{round(all_works.get(work_name).get("salary_per_min"), 2)}'
                            f'{"💰" if all_works.get(work_name).get("salary_in") == "money" else "🍎"} в мин]',
                            'primary', {'args': f'work.{work_name}'}
                        )]]

                if not buttons:
                    answer = f'Нет доступных работ для {self.name}'
                    keyboard = None
                else:
                    buttons += [[get_callback_button('Назад', 'negative', {'args': 'work.back'})]]
                    answer = f'Доступные работы для {self.name}'
                    keyboard = str(json.dumps({"one_time": True, "buttons": buttons}, ensure_ascii=False))

                vk_session.method('messages.send',
                                  {'user_id': int(self.owner_id),
                                   'message': answer,
                                   'random_id': 0, 'keyboard': keyboard})
                return -1
            elif args.startswith('work.'):
                if args == 'work.finish':
                    self.action = None
                    self.timer_action.cancel()
                    work_time = round(floor((datetime.now(tz=tz) - self.time_start_action).total_seconds() / 60), 2)
                    salary = work_time * all_works.get(self.work_name).get('salary_per_min')

                    answer = f'{self.name} вернул{"ся" if self.is_male() else "aсь"} с работы\n' \
                             f'Заработано: {round(salary, 2)}'

                    if all_works.get(self.work_name).get('salary_in') == 'money':
                        users_info[self.owner_id]["balance"] += salary
                        answer += '💰'
                    else:
                        self.game_pets.all_foods[self.owner_id] += salary
                        answer += '🍎'

                    if work_time >= 180:
                        if random.randint(0, 20) == 0:
                            self.fall_ill()
                            answer += f'\nНа работе произошел несчастный случай, из-за чего {self.name} заболел.'

                        if random.randint(50, 100) <= self.features_now.get('luck', 0):
                            prize = round(random.random() * salary, 2)
                            answer += f'\nБлагодаря большому трудовому дню и своей удаче {self.name} заработал премию ' \
                                      f'в размере {round(prize, 2)}'
                            if all_works.get(self.work_name).get('salary_in') == 'money':
                                users_info[self.owner_id]["balance"] += prize
                                answer += '💰'
                            else:
                                self.game_pets.all_foods[self.owner_id] += prize
                                answer += '🍎'

                else:
                    self.work_name = args.replace('work.', '')
                    self.action = f'работает ({self.work_name})'
                    self.time_start_action = datetime.now(tz=tz)

                    now = datetime.now(tz=tz)
                    if self.features_now.get('work_time_night'):
                        self.time_finish_action = datetime(year=now.year, month=now.month, day=now.day, hour=9,
                                                           tzinfo=tz)
                        if now.time() <= datetime_time(hour=23, minute=59, second=59):
                            self.time_finish_action += timedelta(days=1)
                    else:
                        self.time_finish_action = datetime(year=now.year, month=now.month, day=now.day, hour=21,
                                                           tzinfo=tz)
                    self.timer_action = threading.Timer(round((self.time_finish_action - now).total_seconds()),
                                                        function=self.work, args=['work.finish'])
                    self.timer_action.start()
                    answer = f'{self.name} начал{"" if self.is_male() else "a"} работать ({self.work_name})'
            else:
                answer = 'В настоящий момент данная работа недоступна'

            self.send_message_action(answer)
            return -1

    def potion(self, args=None):
        if args is None:
            args = ''

        if args == 'potion.back':
            self.actions()
            return -1
        elif args.startswith('potion.'):
            feature = args.replace('potion.', '')
            if feature not in self.features_now:
                return f'{self.name} не обладает данной характеристикой'

            if self.game_pets.all_potions.get(self.owner_id, 0) >= 1:
                self.game_pets.all_potions[self.owner_id] -= 1
                self.features_now[feature] = 100
                self.features_now['food_per_meal'] += 1
                answer = f'{self.name} выпил{"" if self.is_male() else "a"} эликсир и ' \
                         f'улучшил{"" if self.is_male() else "a"} показатель ' \
                         f'"{self.translate(feature)}" до 100/100!\n' \
                         f'Помните, что лекарства отменяют любые изменения!'
                vk_session.method('messages.send',
                                  {'user_id': int(self.owner_id),
                                   'message': answer,
                                   'random_id': 0})
                self.potion()
                return -1
            else:
                answer = f'Недостаточно 🧪.\n' \
                         f'В хранилище: {self.game_pets.all_potions.get(self.owner_id, 0)}🧪\n' \
                         f'Требуется: 1🧪'
        elif args == 'potion_age':
            if self.game_pets.all_potions.get(self.owner_id, 0) >= 2:
                self.game_pets.all_potions[self.owner_id] -= 2
                self.age = list(self.ages.keys()).index('Детство')
                self.status = f'омолодил{"ся" if self.is_male() else "aсь"}'

                self.timer_age.cancel()
                self.timer_age = threading.Timer(self.ages[list(self.ages.keys())[self.age]], self.next_age)
                self.timer_age.start()
                self.time_finish_age = datetime.now(tz=tz) + timedelta(
                    seconds=self.ages[list(self.ages.keys())[self.age]])

                answer = f'{self.name} выпил{"" if self.is_male() else "a"} эликсир и ' \
                         f'стал{"" if self.is_male() else "a"} молод{"ым" if self.is_male() else "ой"}!'
                vk_session.method('messages.send',
                                  {'user_id': int(self.owner_id),
                                   'message': answer,
                                   'random_id': 0})
                self.actions()
                return -1
            else:
                answer = f'Недостаточно 🧪.\n' \
                         f'В хранилище: {self.game_pets.all_potions.get(self.owner_id, 0)}🧪\n' \
                         f'Требуется: 2🧪'
        else:
            buttons = []
            left_button = True
            for key, value in self.features_now.items():
                if key in ['food_per_meal', 'work_time_night']:
                    continue
                elif value < 100:
                    if left_button:
                        buttons += [[get_callback_button(f'{self.translate(key)} (1🧪)', 'positive',
                                                         {'args': f'potion.{key}'})]]
                        left_button = False
                    else:
                        buttons[-1] += [
                            get_callback_button(f'{self.translate(key)} (1🧪)', 'positive', {'args': f'potion.{key}'})]
                        left_button = True

            if self.age >= list(self.ages.keys()).index('Зрелость'):
                buttons += [[get_callback_button('Вернуть молодость (2🧪)', 'positive', {'args': 'potion_age'})]]

            buttons += [[get_callback_button('Назад', 'negative', {'args': 'potion.back'})]]
            keyboard = str(json.dumps({"one_time": True, "buttons": buttons}, ensure_ascii=False))
            vk_session.method('messages.send',
                              {'user_id': int(self.owner_id),
                               'message': 'Выберите характеристику\n'
                                          'Учтите, что каждое улучшение повышает потребление еды на 1🍎, '
                                          'а лекарства отменяют любые изменения!',
                               'random_id': 0, 'keyboard': keyboard})
            return -1
        return answer


class Minion:
    pet: Pet
    works: dict

    def __init__(self, pet: Pet):
        self.pet = pet
        self.works = {'Помощник злодея': {'skills': {'power': 20, 'industriousness': 40},
                                          'salary_per_min': 1, 'salary_in': 'food'},
                      'Помощник главного злодея': {'skills': {'power': 80, 'industriousness': 80},
                                                   'salary_per_min': 2, 'salary_in': 'food'}}

    def get_action_buttons(self):
        # 'Яйцо': 60 * 10, 'Младенчество': 60 * 20, 'Детство': 60 * 60 * 24, 'Юность': 60 * 60 * 24 * 2,
        # 'Молодость': 60 * 60 * 24 * 7, 'Зрелость': 60 * 60 * 24 * 21, 'Старость': 0
        buttons = []
        buttons += [[get_callback_button('Банана!', 'primary', {'args': 'banana'})]]
        if self.pet.age >= list(self.pet.ages.keys()).index('Юность'):
            buttons += [[get_callback_button('Сделать гадость', 'primary', {'args': 'vandalize'})]]

        return buttons

    def check_action(self, args):
        answer = None
        if args == 'banana':
            answer = 'Банана!'
        elif args == 'vandalize':
            answer = self.vandalize()
        return answer

    def vandalize(self):
        actions = [1, 2, 3]
        if users_info.get(self.pet.owner_id, {}).get("balance", 0) >= 5:
            actions += [0]
        if self.pet.disease is None:
            actions += [4]
        if users_info.get(self.pet.owner_id, {}).get("balance", 0) > 0:
            actions += [5]
        action = random.choice(actions)
        answer = f'{self.pet.name} '
        if action == 0:
            money = round(random.uniform(0.5, max(5, users_info.get(self.pet.owner_id, {}).get("balance", 0) / 10)), 2)
            price = round(random.uniform(0.0, 0.5), 2)
            food = int(money / max(price, 0.05))
            answer += f'украл{"" if self.pet.is_male() else "a"} у Вас {round(money, 2)}💰 и ' \
                      f'купил{"" if self.pet.is_male() else "a"} на них {food}🍎'
            users_info[self.pet.owner_id]["balance"] -= money
            self.pet.food += food
        elif action == 1:
            pills = random.randint(0, 3)
            if bool(random.randint(0, 1)):
                answer += f'угнал{"" if self.pet.is_male() else "a"} фургон с медикаментами, но так как водить ' \
                          f'он{"" if self.pet.is_male() else "a"} не умеет, большая часть рассыпалась по дороге.\n' \
                          f'Сохранилось только {pills}💊, и все заработанное {self.pet.name} ' \
                          f'отдал{"" if self.pet.is_male() else "a"} Вам'
            else:
                self.pet.fall_ill()
                answer += f'угнал{"" if self.pet.is_male() else "a"} фургон с медикаментами, ' \
                          f'наел{"ся" if self.pet.is_male() else "aсь"} лекарства и ' \
                          f'заболел{"" if self.pet.is_male() else "a"}.\n' \
                          f'Сохранилось еще {pills}💊, и все заработанное {self.pet.name} ' \
                          f'отдал{"" if self.pet.is_male() else "a"} Вам.\n' \
                          f'Только вылечите, пожааалуйста'
            self.pet.game_pets.all_pills[self.pet.owner_id] += pills
        elif action == 2:
            food = random.randint(1, 100)
            lost = random.randint(1, food)
            lives = random.randint(5, int(self.pet.lives / 2 - 1)) if int(self.pet.lives / 2 - 1) > 5 else int(
                self.pet.lives / 2 - 1)
            self.pet.food += food - lost
            self.pet.lives -= lives
            answer += f'нарвал{"" if self.pet.is_male() else "a"} {food}🍎 с соседского дерева, но ' \
                      f'сломал{"" if self.pet.is_male() else "a"} ветку и ' \
                      f'грохнул{"ся" if self.pet.is_male() else "aсь"}, поэтому ' \
                      f'потерял{"" if self.pet.is_male() else "a"} часть урожая.\n' \
                      f'Добыто: {food - lost}🍎\n' \
                      f'Сейчас жизней: {round(self.pet.lives, 2)}'
        elif action == 3:
            count = random.randint(30, 50)
            if self.pet.food >= count:
                self.pet.food -= count
                self.pet.features_now['power'] = 100
                answer += f'сварил{"" if self.pet.is_male() else "a"} зелье силы из {count}🍎 и ' \
                          f'выпил{"" if self.pet.is_male() else "a"} его.' \
                          f'Появились какие-то синие пятна, зато сила увеличилась до 100/100!\n' \
                          f'Сколько продержится действие зелья никто не знает, но любое лекарство точно вернет все как было'
            else:
                self.pet.food = 0
                answer += f'пытал{"ся" if self.pet.is_male() else "aсь"} сварить зелье силы, но не хватило 🍎, ' \
                          f'поэтому все взорвалось.\n' \
                          f'Кстати, еды в кормушке теперь тоже нет'
        elif action == 4:
            self.pet.fall_ill()
            answer += f'увидел{"" if self.pet.is_male() else "a"} желтый гриб. ' \
                      f'Подумал{"" if self.pet.is_male() else "a"}, что это банан. ' \
                      f'Съел{"" if self.pet.is_male() else "a"} его и заболел{"" if self.pet.is_male() else "a"}. ' \
                      f'Типичный миньон.\n' \
                      f'Не забудьте вылечить питомца, а то помрет еще...'
        elif action == 5:
            if random.randint(0, 2) == 0:
                money = random.randint(1, 20)
                users_info[self.pet.owner_id]["balance"] += money
                answer += f'выкопал{"" if self.pet.is_male() else "a"} яму на дороге, в которую влетела ' \
                          f'инкассаторская машина.\n' \
                          f'У Вас пополнение на {round(money, 2)}💰'
            else:
                money = round(random.uniform(0, min(users_info.get(self.pet.owner_id, {}).get("balance", 0), 10)), 2)
                users_info[self.pet.owner_id]["balance"] -= money
                answer += f'выкопал{"" if self.pet.is_male() else "a"} яму на дороге, в которую влетела ' \
                          f'полицейская машина.\n' \
                          f'У Вас штраф на {round(money, 2)}💰'
        else:
            answer = 'Что-то ничего не получилось'

        return answer


class FloraColossus:
    pet: Pet
    works: dict

    def __init__(self, pet: Pet):
        self.pet = pet
        self.works = {'Работник Call-центра': {'skills': {'intellect': 20, 'industriousness': 30},
                                               'salary_per_min': 1, 'salary_in': 'food'},
                      'Инсталляция в ботаническом саду': {'skills': {'health': 40, 'industriousness': 50},
                                                          'salary_per_min': 1, 'salary_in': 'food'}}

    def get_action_buttons(self):
        # 'Яйцо': 60 * 10, 'Младенчество': 60 * 20, 'Детство': 60 * 60 * 24, 'Юность': 60 * 60 * 24 * 2,
        # 'Молодость': 60 * 60 * 24 * 7, 'Зрелость': 60 * 60 * 24 * 21, 'Старость': 0
        buttons = []
        if self.pet.age >= list(self.pet.ages.keys()).index('Детство'):
            if self.pet.features_now.get('health') == self.pet.features_now.get('power') == 100:
                buttons += [
                    [get_callback_button('Вырастить еду на себе [20-40🍎]', 'primary', {'args': 'to_small_tree'})]]
            else:
                buttons += [[get_callback_button('Стать большим деревом (30🍎)', 'primary', {'args': 'to_big_tree'})]]
        if self.pet.age >= list(self.pet.ages.keys()).index('Юность'):
            buttons += [[get_callback_button('Использовать знания', 'primary', {'args': 'use_knowledge'})]]

        return buttons

    def check_action(self, args):
        answer = None
        if args == 'to_big_tree':
            answer = self.change_height(to_big=True)
        elif args == 'to_small_tree':
            answer = self.change_height(to_big=False)
        elif args == 'use_knowledge':
            answer = self.use_knowledge()
        return answer

    def change_height(self, to_big):
        if to_big:
            if self.pet.disease is not None:
                answer = f'{self.pet.name} болеет и не может вырасти'
            else:
                if self.pet.features_now.get('health') == self.pet.features_now.get('power') == 100:
                    answer = f'{self.pet.name} уже большой'
                else:
                    if self.pet.food < 30:
                        answer = f'Недостаточно 🍎 для роста.\n' \
                                 f'В кормушке: {self.pet.food}🍎\n' \
                                 f'Требуется: 30🍎'
                    else:
                        self.pet.food -= 30
                        self.pet.features_now['health'] = 100
                        self.pet.features_now['power'] = 100
                        self.pet.features_now['speed'] = 10
                        self.pet.features_now['industriousness'] = 10
                        self.pet.features_now['neatness'] = 10
                        answer = f'{self.pet.name} стал{"" if self.pet.is_male() else "a"} больше и ' \
                                 f'увеличил{"" if self.pet.is_male() else "a"} показатели здоровья и силы до 100/100, ' \
                                 f'однако скорость, трудолюбие и аккуратность стали всего 10/100\n' \
                                 f'Будьте внимательны: лекарства возвращают показатели в первоначальное состояние!'

        else:
            if self.pet.disease is not None:
                answer = f'{self.pet.name} болеет и не может выращивать еду'
            else:
                if self.pet.features_now.get('health') < 100 or self.pet.features_now.get('power') < 100:
                    answer = f'{self.pet.name} мал для выращивания еды'
                else:
                    food = random.randint(20, 40)
                    self.pet.food += food
                    self.pet.features_now = self.pet.get_features(*self.pet.level.get(self.pet.type)[1])
                    answer = f'{self.pet.name} вырастил{"" if self.pet.is_male() else "a"} на себе {food}🍎, ' \
                             f'из-за чего стал{"" if self.pet.is_male() else "a"} меньше и ' \
                             f'вернул{"" if self.pet.is_male() else "a"} все показатели в первоначальное состояние'

        return answer

    def use_knowledge(self):
        actions = [0, 1, 2, 4]
        for pet in self.pet.game_pets.all_pets.get(self.pet.owner_id):
            if pet.type == 'Миньон':
                actions += [3]
                break
        action = random.choice(actions)
        answer = f'{self.pet.name} '
        if action == 0:
            food = random.randint(20, 40)
            if self.pet.food >= food:
                self.pet.food -= food
                for pet in self.pet.game_pets.all_pets.get(self.pet.owner_id):
                    pet.satiety = 100
                answer = f'изучил{"" if self.pet.is_male() else "a"} книгу по кулинарии и ' \
                         f'приготовил{"" if self.pet.is_male() else "a"} вкусный суп, которым ' \
                         f'накормил{"" if self.pet.is_male() else "a"} всех питомцев досыта.\n' \
                         f'Потрачено: {food}🍎'
            else:
                self.pet.food = 0
                answer = f'изучил{"" if self.pet.is_male() else "a"} книгу по кулинарии и ' \
                         f'хотел{"" if self.pet.is_male() else "a"} приготовить яблочный пирог, но' \
                         f'не хватило 🍎, поэтому ничего не получилось.\n' \
                         f'Кстати, еды в кормушке теперь тоже нет'
        elif action == 1:
            pills = random.randint(0, 3)
            if pills > 0:
                self.pet.game_pets.all_pills[self.pet.owner_id] += pills
                answer += f'изучил{"" if self.pet.is_male() else "a"} книгу по медицине и ' \
                          f'синтезировал{"" if self.pet.is_male() else "a"} {pills}💊'
            else:
                self.pet.fall_ill()
                answer += f'изучал{"" if self.pet.is_male() else "a"} книгу по медицине и ' \
                          f'синтезировал{"" if self.pet.is_male() else "a"} {random.randint(1, 5)}💊, которые ' \
                          f'решил{"" if self.pet.is_male() else "a"} испытать на себе и ' \
                          f'отравил{"ся" if self.pet.is_male() else "ась"}.\n' \
                          f'Лекарства были признаны непригодными, а питомца надо вылечить!'
        elif action == 2:
            someone_fall_ill = False
            for pet in self.pet.game_pets.all_pets.get(self.pet.owner_id):
                if pet.action is None:
                    if random.randint(0, 20) != 0:
                        pet.features_now['intellect'] = 100
                    else:
                        someone_fall_ill = True
                        pet.fall_ill()
            answer += f'прочитал{"" if self.pet.is_male() else "a"} всем незанятым питомцам лекцию по квантовой физике.\n'
            if someone_fall_ill:
                answer += f'Кто-то что-то понял и повысил показатели интеллекта до 100/100, а кто-то сошел с ума, заболел ' \
                          f'и требует Вашего внимания. ' \
                          f'{self.pet.name} сказал{"" if self.pet.is_male() else "a"}, что ' \
                          f'он{"" if self.pet.is_male() else "a"} тут не при чем, это просто неокрепший мозг!'
            else:
                answer += f'На удивление, все питомцы поняли данный материал и теперь мучают соседей опытами с ' \
                          f'телепортацией информации.'
        elif action == 3:
            someone_fall_ill = False
            answer += f'подсмотрел{"" if self.pet.is_male() else "a"} у Вашего Миньона рецепт зелья силы и ' \
                      f'усовершенствовал{"" if self.pet.is_male() else "a"} его: приготовленное зелье не затратило 🍎.\n'
            if bool(random.randint(0, 1)):
                for pet in self.pet.game_pets.all_pets.get(self.pet.owner_id):
                    if pet.action is None:
                        if random.randint(0, 20) != 0:
                            pet.features_now['power'] = 80
                        else:
                            someone_fall_ill = True
                            pet.fall_ill()
                answer += 'Однако получился странный эффект: оно не увеличивает силу до максимума, а устанавливает ее ' \
                          'ровно на 80/100.\n'
            else:
                feature = random.choice(['health', 'intellect', 'speed', 'industriousness', 'neatness'])
                new_value = random.randint(30, 90)
                for pet in self.pet.game_pets.all_pets.get(self.pet.owner_id):
                    if pet.action is None:
                        if random.randint(0, 20) != 0:
                            pet.features_now[feature] = new_value
                        else:
                            someone_fall_ill = True
                            pet.fall_ill()
                answer += f'К сожалению, что-то пошло не так, и вместо силы зелье меняет параметр ' \
                          f'{self.pet.translate(feature)} до {new_value}/100.\n'
            answer += 'Тем не менее, все незанятые питомцы получили свою дозу!'
            if someone_fall_ill:
                answer += ' Кому-то, правда, зелье не пошло и появились признаки болезни...'
        elif action == 4:
            money = random.randint(1, 15)
            users_info[self.pet.owner_id]["balance"] += money
            answer += f'выиграл{"" if self.pet.is_male() else "a"} международную олимпиаду по математическому ' \
                      f'описанию физической модели биотехнофилософского обоснования возможности существования расы ' \
                      f'Флора Колосс, так как является представителем данной рассы, и ' \
                      f'заработал{"" if self.pet.is_male() else "a"} {round(money * 10, 2)}💰, ' \
                      f'большая часть которых ушла на оплату проезда и вступительного взноса.' \
                      f'Заработано: {round(money, 2)}💰'
            if random.randint(0, 20) == 0:
                self.pet.fall_ill()
                answer += f'\n\nК сожалению, в стране проведения олимпиады сейчас пандемия нового грутовируса, поэтому ' \
                          f'{self.pet.name} заболел{"" if self.pet.is_male() else "a"}'
        else:
            answer = 'Что-то ничего не получилось'

        return answer


class Vampire:
    pet: Pet
    works: dict

    def __init__(self, pet: Pet):
        self.pet = pet
        self.works = {'Охранник в детском саду': {'skills': {'speed': 60, 'industriousness': 20, 'neatness': 20},
                                                  'salary_per_min': 0.05, 'salary_in': 'money'},
                      f'Дояр{"" if self.pet.is_male() else "кa"} насосавшихся комаров': {
                          'skills': {'speed': 20, 'industriousness': 30, 'neatness': 30},
                          'salary_per_min': 1.5, 'salary_in': 'food'}}

    def get_action_buttons(self):
        # 'Яйцо': 60 * 10, 'Младенчество': 60 * 20, 'Детство': 60 * 60 * 24, 'Юность': 60 * 60 * 24 * 2,
        # 'Молодость': 60 * 60 * 24 * 7, 'Зрелость': 60 * 60 * 24 * 21, 'Старость': 0
        buttons = []
        if self.pet.age >= list(self.pet.ages.keys()).index('Детство'):
            if self.pet.disease is not None or self.pet.lives < 100:
                buttons += [
                    [get_callback_button('Использовать регенерацию (5мин)', 'primary', {'args': 'use_regeneration'})]]
            buttons += [[get_callback_button('Съесть чеснок', 'primary', {'args': 'eat_garlic'})]]
        if self.pet.age >= list(self.pet.ages.keys()).index('Юность'):
            buttons += [[get_callback_button('Обратить питомца в вампира', 'primary', {'args': 'turn_into_vampire'})]]
            buttons += [[get_callback_button('Насытиться витамином D3', 'primary', {'args': 'sunbathing'})]]
        # if self.pet.age >= list(self.pet.ages.keys()).index('Молодость'):
        #     buttons += [[get_callback_button('Использовать гипноз', 'primary', {'args': 'use_hypnosis'})]]

        return buttons

    def check_action(self, args):
        answer = None
        if args == 'use_regeneration':
            answer = self.use_regeneration()
        elif args == 'eat_garlic':
            answer = self.eat_garlic()
        elif args == 'turn_into_vampire':
            self.turn_into_vampire()
            return -1
        elif args.startswith('vampire.'):
            self.turn_into_vampire(args)
            return -1
        elif args == 'sunbathing':
            self.sunbathing()
            return -1
        # elif args == 'use_hypnosis':
        #     answer = self.use_hypnosis()
        return answer

    def use_regeneration(self, is_finally=None):
        if is_finally:
            self.pet.disease = None
            self.pet.lives = 100
            answer = f'{self.pet.name} избавил{"ся" if self.pet.is_male() else "aсь"} от болезней и полностью ' \
                     f'восстановил{"" if self.pet.is_male() else "a"} жизни'
            self.pet.action = None
            self.pet.send_message_action(answer)
            return -1
        else:
            self.pet.action = 'использует навык регенерации'
            self.pet.timer_action = threading.Timer(60 * 5, function=self.use_regeneration, args=[True])
            self.pet.timer_action.start()
            self.pet.time_finish_action = datetime.now(tz=tz) + timedelta(seconds=60 * 5)
            answer = f'{self.pet.name} начал{"" if self.pet.is_male() else "a"} регенерироваться.'
        return answer

    def eat_garlic(self):
        self.pet.fall_ill()
        answer = f'{self.pet.name} отравил{"ся" if self.pet.is_male() else "aсь"} и ' \
                 f'заболел{"" if self.pet.is_male() else "a"}. А Вы чего хотели?'
        return answer

    def turn_into_vampire(self, args=None):
        if args is None:
            args = ''

        if args.startswith('vampire.Pet'):
            name = args.replace('vampire.Pet.', '')
            answer = f'Уверены, что хотите обратить {name} в вампира?'
            keyboard = str(json.dumps({
                "one_time": False,
                "buttons": [
                    [get_callback_button('Да', 'positive', {'args': f'vampire.yes.{name}'}),
                     get_callback_button('Нет', 'negative', {'args': f'vampire.no'})]
                ]
            }, ensure_ascii=False))
            vk_session.method('messages.send',
                              {'user_id': int(self.pet.owner_id),
                               'message': answer,
                               'random_id': 0, 'keyboard': keyboard})
            return
        elif args.startswith('vampire.yes'):
            name = args.replace('vampire.yes.', '')
            for pet in self.pet.game_pets.all_pets.get(self.pet.owner_id):
                if pet.name == name:
                    pet.level = pet.level_0
                    pet.type = 'Вампир'
                    pet.features_now = pet.get_features(*pet.level.get(pet.type)[1])
                    pet.status = 'стал вампиром'
                    break
            answer = f'{self.pet.name} обратил{"" if self.pet.is_male() else "a"} питомца {name} в вампира'

            vk_session.method('messages.send',
                              {'user_id': int(self.pet.owner_id),
                               'message': answer,
                               'random_id': 0})
            self.turn_into_vampire(self.pet.owner_id)
            return
        elif args == 'vampire.no':
            vk_session.method('messages.send',
                              {'user_id': int(self.pet.owner_id),
                               'message': f'Выберите питомца для обращения',
                               'random_id': 0})
            self.pet.game_pets.send_pets_page(self.pet.owner_id, 0, self.pet.game_pets.all_pets.get(self.pet.owner_id),
                                              'vampire')
            return
        elif args.startswith('vampire.page.'):
            self.pet.game_pets.send_pets_page(self.pet.owner_id, int(args.replace('vampire.page.', '')),
                                              self.pet.game_pets.all_pets.get(self.pet.owner_id), 'vampire')
            return
        elif args == 'vampire.back':
            self.pet.actions()
            return
        else:
            vk_session.method('messages.send',
                              {'user_id': int(self.pet.owner_id),
                               'message': f'Выберите питомца для обращения',
                               'random_id': 0})
            self.pet.game_pets.send_pets_page(self.pet.owner_id, 0, self.pet.game_pets.all_pets.get(self.pet.owner_id),
                                              'vampire')
            return

    def sunbathing(self):
        answer = 'Вампира отправить загорать на солнце? Ну Вы... Ващеее...\n'
        leave = False
        if random.randint(0, 50) == 0:
            answer += f'Он{"" if self.pet.is_male() else "a"} потерял{"" if self.pet.is_male() else "a"} все жизни!'
            leave = True
        else:
            self.pet.fall_ill()
            answer += f'Он{"" if self.pet.is_male() else "a"} заболел{"" if self.pet.is_male() else "a"}! ' \
                      f'И хорошо, что только заболел{"" if self.pet.is_male() else "a"}...'

        vk_session.method('messages.send',
                          {'user_id': int(self.pet.owner_id),
                           'message': answer,
                           'random_id': 0})
        if leave:
            self.pet.leave(False)

    def use_hypnosis(self):
        pass


class Witch:
    pet: Pet
    works: dict
    know_magic = False

    def __init__(self, pet: Pet):
        self.pet = pet
        self.pet.sex = 'Женщина'
        self.works = {'Фармацевт': {'skills': {'health': 40, 'intellect': 40, 'neatness': 40},
                                    'salary_per_min': 1, 'salary_in': 'food'},
                      f'Водитель аэротакси': {
                          'skills': {'intellect': 40, 'industriousness': 30, 'neatness': 30},
                          'salary_per_min': 1, 'salary_in': 'food'}}

    def get_action_buttons(self):
        # 'Яйцо': 60 * 10, 'Младенчество': 60 * 20, 'Детство': 60 * 60 * 24, 'Юность': 60 * 60 * 24 * 2,
        # 'Молодость': 60 * 60 * 24 * 7, 'Зрелость': 60 * 60 * 24 * 21, 'Старость': 0
        buttons = []
        if self.pet.age >= list(self.pet.ages.keys()).index('Детство'):
            if not self.know_magic:
                buttons += [
                    [get_callback_button('Практиковаться в магии (20мин)', 'primary', {'args': 'practice_magic'})]]
                buttons += [[get_callback_button('Изучить магию (нужен Грут)', 'primary',
                                                 {'args': 'study_magic'})]]
        if self.pet.age >= list(self.pet.ages.keys()).index('Юность'):
            if self.know_magic:
                buttons += [[get_callback_button('Сварить быстрое зелье (200🍎) [1🧪]', 'primary',
                                                 {'args': 'create_potion.fast'})]]
                buttons += [[get_callback_button('Сварить дешевое зелье (50🍎, 5ч) [1🧪]', 'primary',
                                                 {'args': 'create_potion.cheap'})]]

        return buttons

    def check_action(self, args):
        answer = None
        if args == 'practice_magic':
            answer = self.practice_magic()
        elif args == 'study_magic':
            answer = self.study_magic()
        elif args.startswith('create_potion.'):
            answer = self.create_potion(args)

        return answer

    def practice_magic(self, is_finish=False):
        answer = f'{self.pet.name} '
        if self.know_magic:
            answer += 'уже знает магию'
        else:
            if not is_finish:
                self.pet.action = f'практикуется в магии'
                self.pet.timer_action = threading.Timer(60 * 20, function=self.practice_magic, args=[True])
                self.pet.timer_action.start()
                self.pet.time_finish_action = datetime.now(tz=tz) + timedelta(seconds=60 * 20)
                answer += f'начал{"" if self.pet.is_male() else "a"} изучать магию!'
            else:
                if random.randint(0, 10) == 0:
                    self.know_magic = True
                    answer += f'практиковал{"ся" if self.pet.is_male() else "aсь"} в магии и ' \
                              f'понял{"" if self.pet.is_male() else "a"} каким зельем можно превратить всех гуманитариев ' \
                              f'в математиков!\n' \
                              f'Открыта способность зельеварения.'
                else:
                    answer += f'практиковал{"ся" if self.pet.is_male() else "aсь"} в магии, но так и не ' \
                              f'смог{"" if self.pet.is_male() else "лa"} понять, почему лягушки не летают, а гуси не ' \
                              f'программируют ботов. Е{"му" if self.pet.is_male() else "й"} требуются еще практики для ' \
                              f'постижения данных вопросов Вселенной!'
                self.pet.action = None
                self.pet.send_message_action(answer)
                return -1
        return answer

    def study_magic(self):
        there_is_groot = False
        groot_name = None
        groot_is_male = None
        for pet in self.pet.game_pets.all_pets.get(self.pet.owner_id):
            if pet.type == 'Грут' and pet.age >= list(pet.ages.keys()).index('Юность') and pet.action is None:
                there_is_groot = True
                groot_name = pet.name
                groot_is_male = pet.is_male()
                break
        if not there_is_groot:
            answer = 'У Вас нет Грута или он еще мал для обучения ведьмы (требуется возраст "Юность" и выше) или он занят'
        else:
            self.know_magic = True
            answer = f'{groot_name} использовал{"" if groot_is_male else "a"} свой интеллект и ' \
                     f'обучил{"" if groot_is_male else "a"} питомца {self.pet.name} магии\n' \
                     f'Открыта способность зельеварения.'
        return answer

    def create_potion(self, args, is_finish=False):
        if args == 'create_potion.fast':
            if self.pet.food >= 200:
                self.pet.food -= 200
                self.pet.game_pets.all_potions[self.pet.owner_id] += 1
                answer = f'{self.pet.name} приготовил{"" if self.pet.is_male() else "a"} 1🧪, использовав 200🍎\n' \
                         f'Он{"" if self.pet.is_male() else "a"} надеется, что полученной смесью никто не отравится...\n' \
                         f'В хранилище: {self.pet.game_pets.all_potions[self.pet.owner_id]}🧪'
            else:
                answer = f'У {self.pet.name} недостаточно 🍎, чтобы сварить быстрое зелье.'
        elif args == 'create_potion.cheap':
            if not is_finish:
                if self.pet.food >= 50:
                    self.pet.food -= 50
                    self.pet.action = f'готовит зелье'
                    self.pet.timer_action = threading.Timer(60 * 60 * 5, function=self.create_potion,
                                                            args=['create_potion.cheap', True])
                    self.pet.timer_action.start()
                    self.pet.time_finish_action = datetime.now(tz=tz) + timedelta(seconds=60 * 60 * 5)
                    answer = f'{self.pet.name} начал{"" if self.pet.is_male() else "a"} готовить дешевое зелье.'
                else:
                    answer = f'У {self.pet.name} недостаточно 🍎, чтобы сварить дешевое зелье.'
            else:
                self.pet.game_pets.all_potions[self.pet.owner_id] += 1
                answer = f'{self.pet.name} приготовил{"" if self.pet.is_male() else "a"} 1🧪, использовав 50🍎\n' \
                         f'Он{"" if self.pet.is_male() else "a"} надеется, что полученной смесью никто не отравится...\n' \
                         f'В хранилище: {self.pet.game_pets.all_potions[self.pet.owner_id]}🧪'
                self.pet.action = None
                self.pet.send_message_action(answer)
                return -1
        else:
            answer = f'{self.pet.name} не умеет варить такие зелья'
        return answer
