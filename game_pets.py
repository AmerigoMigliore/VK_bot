import json
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

    all_max_pets = {}
    start_max_pets = 3

    shelter = []
    shelter_price = 1
    market = {}

    def save_me(self):
        for pets in self.all_pets.values():
            for pet in pets:
                pet.stop_me()
        return self.all_pets, self.all_foods, self.all_pills, self.all_max_pets

    def load_me(self, data):
        self.all_pets = data[0]
        self.all_foods = data[1]
        self.all_pills = data[2]
        if len(data) >= 4:
            self.all_max_pets = data[3]

        for pets in self.all_pets.values():
            for pet in pets:
                pet.game_pets = self
                pet.start_me()

    def add_pet(self, owner_id: str):
        self.all_pets[owner_id] += [Pet(self, owner_id)]

    def delete_pet(self, owner_id: str, pet):
        self.all_pets[owner_id].remove(pet)

    def send_pets_page(self, user_id, page, pets_list, prefix):
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
        if last < len(self.all_pets.get(user_id, [])):
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
            if users_info.get(user_id, {}).get("balance", 0) >= 20:
                users_info[user_id]["balance"] -= 20

                name = args.replace('shelter.take.yes.', '')
                for pet in self.shelter:
                    if pet.name == name:
                        pet.start_me()
                        pet.status = 'обрел нового хозяина!'
                        pet.owner_id = user_id

                        self.all_pets[user_id] += [pet]
                        self.shelter.remove(pet)
                        self.all_foods[user_id] += 10
                        break
                answer = f'Вы забрали {name} из приюта. Дарим Вам 10🍎 для обеспечения питомца в первое время.'

            else:
                answer = f'Недостаточно 💰 для покупки.\n' \
                         f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 1)}💰\n' \
                         f'Требуется: 20💰'

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
            self.send_pets_page(user_id, 0, self.all_pets.get(user_id, []), 'shelter.give')
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
            self.send_pets_page(user_id, 0, self.all_pets.get(user_id, []), 'shelter.give')
            return
        elif args.startswith('shelter.give.page.'):
            self.send_pets_page(user_id, int(args.replace('shelter.give.page.', '')), self.all_pets.get(user_id, []),
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
                    [get_callback_button('Забрать, -20💰', 'primary', {'args': 'shelter.take'}),
                     get_callback_button('Отдать', 'secondary', {'args': 'shelter.give'})],
                    [get_callback_button('Назад', 'negative', {'args': 'shelter.back'})]
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
                elif args == 'back':
                    vk_session.method('messages.send',
                                      {'user_id': int(user_id),
                                       'message': 'Твои питомцы будут ждать тебя, хозяин!',
                                       'random_id': 0, 'keyboard': main_keyboard})
                    change_users_info(user_id, 'autoresponder')

                    # Сброс активированной кнопки, вызвавшей событие
                    vk_session.method('messages.sendMessageEventAnswer',
                                      {'event_id': event.obj.event_id,
                                       'user_id': int(user_id),
                                       'peer_id': event.obj.peer_id})
                    return
            elif method == 'store':
                self.store(user_id, event)
            elif method.startswith('Pet.process_event'):
                for x in self.all_pets.get(user_id, []):
                    if x.name == users_info[user_id]['args'].get('name'):
                        x.process_event(event)
                        break
                else:
                    self.start(user_id)

            # Сброс активированной кнопки, вызвавшей событие
            vk_session.method('messages.sendMessageEventAnswer',
                              {'event_id': event.obj.event_id,
                               'user_id': int(user_id),
                               'peer_id': event.obj.peer_id})

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

    def start(self, user_id: str):
        if self.all_pets.get(user_id) is None:
            self.all_pets[user_id] = []
        if self.all_foods.get(user_id) is None:
            self.all_foods[user_id] = 0
        if self.all_pills.get(user_id) is None:
            self.all_pills[user_id] = 0
        if self.all_max_pets.get(user_id) is None:
            self.all_max_pets[user_id] = self.start_max_pets
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
        if len(self.all_pets[user_id]) > 0:
            pets_str += ':\n'
            buttons += [[get_callback_button('Мои питомцы', 'primary', {'args': 'pets'})]]
        for x in self.all_pets[user_id]:
            pets_str += f'\n{x.get_status()}\n'

        buttons += [[get_callback_button('Склад', 'secondary', {'args': 'storage'}),
                     get_callback_button('Магазин', 'secondary', {'args': 'store'})]]
        buttons += [[get_callback_button('Приют', 'secondary', {'args': 'shelter'})]]
        buttons += [[get_callback_button('Выйти из игры', 'negative', {'args': 'back'})]]
        keyboard = str(json.dumps({
            "one_time": False,
            "buttons": buttons
        }, ensure_ascii=False))

        vk_session.method('messages.send',
                          {'user_id': int(user_id),
                           'message': f'Приветствуем Вас в домике для питомцев!\n'
                                      f'У Вас {count_pets} {pets_str}\n'
                                      f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 1)}💰\n',
                           'random_id': 0, 'keyboard': keyboard})

        change_users_info(user_id, new_method='start')

    def get_storage(self, user_id: str):
        vk_session.method('messages.send',
                          {'user_id': int(user_id),
                           'message': f'Ваш склад:\n'
                                      f'{self.all_foods.get(user_id, 0)}🍎\n'
                                      f'{self.all_pills.get(user_id, 0)}💊\n'
                                      f'Мест для питомцев:\n'
                                      f'{self.all_max_pets.get(user_id, self.start_max_pets)}🧺',
                           'random_id': 0})

    def store(self, user_id: str, event=None):
        keyboard = str(json.dumps({
            "one_time": False,
            "buttons": [
                [get_callback_button('1🐣', 'positive', {'args': 'pet'})],

                [get_callback_button('1🍎', 'positive', {'args': 'food_1'}),
                 get_callback_button('10🍎', 'positive', {'args': 'food_10'}),
                 get_callback_button('100🍎', 'positive', {'args': 'food_100'})],

                [get_callback_button('1💊', 'positive', {'args': 'pill_1'}),
                 get_callback_button('5💊', 'positive', {'args': 'pill_5'}),
                 get_callback_button('10💊', 'positive', {'args': 'pill_10'})],

                [get_callback_button('1🧺', 'positive', {'args': 'home_1'})],

                [get_callback_button('Назад', 'negative', {'args': 'back'})]
            ]
        }, ensure_ascii=False))
        if event is None:
            answer = f'Добро пожаловать в магазин "Все для питомцев"!\nВыберите желаемый товар:\n\n' \
                     f'Яйцо с питомцем:\n' \
                     f'1🐣 - 10💰\n\n' \
                     f'Еда для питомца:\n' \
                     f'1🍎 - 0.2💰\n' \
                     f'10🍎 - 1.5💰\n' \
                     f'100🍎 - 10💰\n\n' \
                     f'Лекарство для питомца:\n' \
                     f'1💊 - 5💰\n' \
                     f'5💊 - 20💰\n' \
                     f'10💊 - 30💰\n\n' \
                     f'Дополнительное место для питомца:\n' \
                     f'1🧺 - 50💰\n\n' \
                     f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 1)}💰'
        else:
            args = event.obj.payload.get('args')
            if args == 'pet':
                if len(self.all_pets.get(user_id)) < self.all_max_pets.get(user_id, self.start_max_pets):
                    if users_info.get(user_id, {}).get("balance", 0) >= 10:
                        users_info[user_id]["balance"] -= 10
                        self.add_pet(user_id)
                        answer = 'Вы приобрели нового питомца. Он доступен в главном меню'
                    else:
                        answer = f'Недостаточно 💰 для покупки.\n' \
                                 f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 1)}💰\n' \
                                 f'Требуется: 10💰'
                else:
                    answer = 'У Вас имеется максимально допустимое количество питомцев'

            elif args == 'food_1':
                if users_info.get(user_id, {}).get("balance", 0) >= 0.2:
                    users_info[user_id]["balance"] -= 0.2
                    self.all_foods[user_id] += 1
                    answer = f'Вы приобрели 1🍎.\nВ хранилище: {self.all_foods[user_id]}🍎'
                else:
                    answer = f'Недостаточно 💰 для покупки.\n' \
                             f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 1)}💰\n' \
                             f'Требуется: 0.2💰'
            elif args == 'food_10':
                if users_info.get(user_id, {}).get("balance", 0) >= 1.5:
                    users_info[user_id]["balance"] -= 1.5
                    self.all_foods[user_id] += 10
                    answer = f'Вы приобрели 10🍎.\nВ хранилище: {self.all_foods[user_id]}🍎'
                else:
                    answer = f'Недостаточно 💰 для покупки.\n' \
                             f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 1)}💰\n' \
                             f'Требуется: 1.5💰'
            elif args == 'food_100':
                if users_info.get(user_id, {}).get("balance", 0) >= 10:
                    users_info[user_id]["balance"] -= 10
                    self.all_foods[user_id] += 100
                    answer = f'Вы приобрели 100🍎.\nВ хранилище: {self.all_foods[user_id]}🍎'
                else:
                    answer = f'Недостаточно 💰 для покупки.\n' \
                             f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 1)}💰\n' \
                             f'Требуется: 10💰'

            elif args == 'pill_1':
                if users_info.get(user_id, {}).get("balance", 0) >= 5:
                    users_info[user_id]["balance"] -= 5
                    self.all_pills[user_id] += 1
                    answer = f'Вы приобрели 1💊.\nВ аптечке: {self.all_pills[user_id]}💊'
                else:
                    answer = f'Недостаточно 💰 для покупки.\n' \
                             f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 1)}💰\n' \
                             f'Требуется: 5💰'
            elif args == 'pill_5':
                if users_info.get(user_id, {}).get("balance", 0) >= 20:
                    users_info[user_id]["balance"] -= 20
                    self.all_pills[user_id] += 5
                    answer = f'Вы приобрели 5💊.\nВ аптечке: {self.all_pills[user_id]}💊'
                else:
                    answer = f'Недостаточно 💰 для покупки.\n' \
                             f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 1)}💰\n' \
                             f'Требуется: 20💰'
            elif args == 'pill_10':
                if users_info.get(user_id, {}).get("balance", 0) >= 30:
                    users_info[user_id]["balance"] -= 30
                    self.all_pills[user_id] += 10
                    answer = f'Вы приобрели 10💊.\nВ аптечке: {self.all_pills[user_id]}💊'
                else:
                    answer = f'Недостаточно 💰 для покупки.\n' \
                             f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 1)}💰\n' \
                             f'Требуется: 30💰'

            elif args == 'home_1':
                if users_info.get(user_id, {}).get("balance", 0) >= 50:
                    users_info[user_id]["balance"] -= 50
                    self.all_max_pets[user_id] += 1
                    answer = f'Вы приобрели 1🧺.\nВсего доступно: {self.all_max_pets[user_id]}🧺'
                else:
                    answer = f'Недостаточно 💰 для покупки.\n' \
                             f'Ваш баланс: {round(users_info.get(user_id, {}).get("balance", 0), 1)}💰\n' \
                             f'Требуется: 50💰'

            elif args == 'back':
                self.start(user_id)
                return
            else:
                answer = 'В магазине нет данного товара'

        vk_session.method('messages.send',
                          {'user_id': int(user_id),
                           'message': answer,
                           'random_id': 0, 'keyboard': keyboard})


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
                        'Грут': [FloraColossus, (2, 30, 80, 30, 80, 30, 30, 0, False)],
                        'Вампир': [Vampire, (2, 50, 20, 30, 60, 30, 30, 0, True)]
                        # 'Ведьма': [Witch, (1.5, 30, 80, 30, 80, 30, 30, 0, False)],  # TODO: Проработать характеристики
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
            'Простуда': {'treatment': 2, 'effects': self.get_features(health=5, speed=5, industriousness=5)},
            'Депрессия': {'treatment': 2, 'effects': self.get_features(food_per_meal=-3, industriousness=100)},
            'Ожирение': {'treatment': 3, 'effects': self.get_features(food_per_meal=-5, health=5, speed=10)},
            'Вывих ноги': {'treatment': 4, 'effects': self.get_features(health=5, power=100, speed=100)},
            'Грипп': {'treatment': 3, 'effects': self.get_features(health=10, speed=10, industriousness=10)}
        }  # TODO: Заполнить!
        self.works = {'Наладчик бота': {'skills': {'intellect': 60, 'industriousness': 30, 'neatness': 30},
                                        'salary_per_min': 0.2, 'salary_in': 'money'},
                      'Переворачиватель пингвинов': {'skills': {'power': 30, 'industriousness': 50},
                                                     'salary_per_min': 0.1, 'salary_in': 'money'}}  # TODO: Заполнить!

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
    features: dict

    timer_age = None
    time_finish_age: datetime

    timer_satiety = None

    action = None
    work_name: str
    timer_action = None
    time_start_action: datetime
    time_finish_action: datetime

    bones = 0
    max_bones = 5
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
        self.features = self.get_features(*self.level.get(self.type)[1])

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
        if self.type == 'Флора колосс':
            self.type = 'Грут'
        if datetime.utcfromtimestamp(self.time_finish_age.timestamp()) > datetime.utcfromtimestamp(
                datetime.now(tz=tz).timestamp()):
            self.timer_age = threading.Timer((datetime.utcfromtimestamp(
                self.time_finish_age.timestamp()) - datetime.utcfromtimestamp(
                datetime.now(tz=tz).timestamp())).seconds, self.next_age)
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
        buttons = [[get_callback_button('1🍎', 'positive', {'args': 'give_food_1'}),
                    get_callback_button('10🍎', 'positive', {'args': 'give_food_10'}),
                    get_callback_button('100🍎', 'positive', {'args': 'give_food_100'})]]
        if self.game_pets.all_foods.get(self.owner_id, 0) > 0:
            buttons += [[get_callback_button(
                f'{self.game_pets.all_foods.get(self.owner_id)}🍎',
                'positive', {'args': 'give_food_all'}
            )]]
        buttons += [[get_callback_button('Назад', 'negative', {'args': 'back'})]]
        return str(json.dumps({"one_time": False, "buttons": buttons}, ensure_ascii=False))

    def give_food(self, event=None):
        keyboard = None
        if event is None:
            keyboard = self.get_food_keyboard()
            answer = 'Выберите количество еды для питомца'
        else:
            args = event.obj.payload.get('args')
            if args == 'give_food_1':
                if self.game_pets.all_foods[self.owner_id] >= 1:
                    self.game_pets.all_foods[self.owner_id] -= 1
                    self.food += 1
                    answer = f'Вы дали питомцу 1🍎.\n' \
                             f'У него в кормушке: {round(self.food, 1)}🍎\n' \
                             f'У Вас в хранилище: {self.game_pets.all_foods[self.owner_id]}🍎'
                    keyboard = self.get_food_keyboard()
                else:
                    answer = f'Недостаточно 🍎.\n' \
                             f'У Вас в хранилище: {self.game_pets.all_foods[self.owner_id]}🍎'
            elif args == 'give_food_10':
                if self.game_pets.all_foods[self.owner_id] >= 10:
                    self.game_pets.all_foods[self.owner_id] -= 10
                    self.food += 10
                    answer = f'Вы дали питомцу 10🍎.\n' \
                             f'У него в кормушке: {round(self.food, 1)}🍎\n' \
                             f'У Вас в хранилище: {self.game_pets.all_foods[self.owner_id]}🍎'
                    keyboard = self.get_food_keyboard()
                else:
                    answer = f'Недостаточно 🍎.\n' \
                             f'У Вас в хранилище: {self.game_pets.all_foods[self.owner_id]}🍎'
            elif args == 'give_food_100':
                if self.game_pets.all_foods[self.owner_id] >= 100:
                    self.game_pets.all_foods[self.owner_id] -= 100
                    self.food += 100
                    answer = f'Вы дали питомцу 100🍎.\n' \
                             f'У него в кормушке: {round(self.food, 1)}🍎\n' \
                             f'У Вас в хранилище: {self.game_pets.all_foods[self.owner_id]}🍎'
                    keyboard = self.get_food_keyboard()
                else:
                    answer = f'Недостаточно 🍎.\n' \
                             f'У Вас в хранилище: {self.game_pets.all_foods[self.owner_id]}🍎'
            elif args == 'give_food_all':
                self.food += self.game_pets.all_foods.get(self.owner_id)
                answer = f'Вы дали питомцу {self.game_pets.all_foods.get(self.owner_id)}🍎.\n' \
                         f'У него в кормушке: {round(self.food, 1)}🍎\n' \
                         f'У Вас в хранилище: 0🍎'
                self.game_pets.all_foods[self.owner_id] = 0
                keyboard = self.get_food_keyboard()
            elif args == 'back':
                change_users_info(self.owner_id, new_method='Pet.process_event',
                                  new_args=users_info.get(self.owner_id, {}).get('args'))
                answer = 'Вы закончили кормление питомца'
                keyboard = self.get_main_keyboard()
            else:
                answer = f'Выберите количество еды для питомца\n' \
                         f'У него в кормушке: {round(self.food, 1)}🍎\n' \
                         f'У Вас в хранилище: {self.game_pets.all_foods[self.owner_id]}🍎'

        vk_session.method('messages.send',
                          {'user_id': int(self.owner_id),
                           'message': answer,
                           'random_id': 0, 'keyboard': keyboard})

    def update_satiety(self):
        if self.bones > 0:
            self.food += self.food_from_bone * self.bones

        if self.satiety >= 5:
            self.satiety -= 5
        else:
            self.satiety = 0

        while self.food >= self.features.get('food_per_meal', 2):
            if self.satiety < 100:
                self.food -= self.features.get('food_per_meal', 2)
                if self.satiety <= 95:
                    self.satiety += 5
                else:
                    self.satiety = 100
                self.status = f'покушал{"" if self.is_male() else "a"}'
            else:
                break
        else:
            self.status = 'голодает'

        if self.satiety == 0:
            if self.disease is None:
                self.fall_ill()
            else:
                self.lives -= (100 - self.features.get('health', 0)) / 10

            if self.lives <= 0:
                self.leave(False)
                return

        elif self.satiety == 100 and self.lives < 100:
            self.lives += self.features.get('health', 0) / 10
            if self.lives > 100:
                self.lives = int(100)

        self.timer_satiety = threading.Timer(self.time_between_satiety, self.update_satiety)
        self.timer_satiety.start()

    def fall_ill(self):
        self.disease = random.choice(list(self.diseases))
        self.status = f'заболел{"" if self.is_male() else "a"} ({self.disease})'
        for x in self.diseases.get(self.disease).get('effects').items():
            if self.features.get(x[0]) is None:
                self.features[x[0]] = self.get_features(*self.level.get(self.type)[1]).get(x[0])
            self.features[x[0]] -= x[1] if self.features[x[0]] > x[1] else self.features[x[0]]

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
            self.features = self.get_features(*self.level.get(self.type)[1])
            self.lives = 100
            self.status = f'недавно вылечил{"ся" if self.is_male() else "aсь"}'
        else:
            answer = f'Недостаточно 💊 для лечения.\n' \
                     f'У Вас в аптечке: {self.game_pets.all_pills.get(self.owner_id)}💊\n' \
                     f'Требуется: {treatment}💊'
        return answer

    def get_status(self):
        return f'{self.name} {self.status}\nДействие: ' \
               f'{self.action if self.action is not None else "Свободен" if self.is_male() else "Свободна"}'

    def get_info(self, is_all):
        if self.age == 0:
            return (f'\n'
                    f'~Информация о питомце~\n'
                    f'Имя: {self.name}\n'
                    f'Возраст: {list(self.ages.keys())[self.age]}\n'
                    f'Статус: {self.status}\n'
                    f'Еда в кормушке: {round(self.food, 1)}\n\n')
        elif not is_all:
            return (f'\n'
                    f'~Информация о питомце~\n'
                    f'Имя: {self.name}\n'
                    f'Возраст: {list(self.ages.keys())[self.age]}\n'
                    f'Статус: {self.status}\n'
                    f'Жизни: {round(self.lives, 1)}/100\n'
                    f'Болезнь: {"Нет" if self.disease is None else self.disease}\n'
                    f'Сытость: {self.satiety}/100\n'
                    f'Еда в кормушке: {round(self.food, 1)}\n\n')
        else:
            return (f'\n'
                    f'~Информация о питомце~\n'
                    f'Имя: {self.name}\n'
                    f'Возраст: {list(self.ages.keys())[self.age]}\n'
                    f'Пол: {self.sex}\n'
                    f'Тип: {self.type}\n'
                    f'Статус: {self.status}\n'
                    f'Жизни: {round(self.lives, 1)}/100\n'
                    f'Болезнь: {"Нет" if self.disease is None else self.disease}\n'
                    f'Сытость: {self.satiety}/100\n'
                    f'Еда в кормушке: {round(self.food, 1)}\n\n'

                    f'Характеристики:\n'
                    f'{self.get_string_features(self.features)}')

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

        if self.age >= list(self.ages.keys()).index('Детство'):
            buttons += [[get_callback_button('Посадить косточку, -1🍎, 1мин', 'secondary', {'args': 'plant_bone'})]]
        if self.age >= list(self.ages.keys()).index('Юность'):
            buttons += [[get_callback_button('Соревнования, -0.5💰, 30мин', 'secondary', {'args': 'competition'})]]
        if self.age >= list(self.ages.keys()).index('Молодость'):
            if self.action is not None and self.action.startswith('работает'):
                buttons += [[get_callback_button('Вернуться с работы', 'negative', {'args': 'work.finish'})]]
            else:
                buttons += [[get_callback_button('Идти на работу', 'secondary', {'args': 'work'})]]

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

        if event is None:
            keyboard = self.get_actions_keyboard()

        elif event.type == VkBotEventType.MESSAGE_EVENT:
            args = event.obj.payload.get('args')
            if args == 'back':
                change_users_info(self.owner_id, new_method='Pet.process_event',
                                  new_args=users_info.get(self.owner_id, {}).get('args'))
                self.process_event()
                return
            elif self.action is not None and args != 'work.finish':
                answer = f'{self.name} {self.action} и не может выполнить еще одно действие.\n' \
                         f'{self.get_time_to_finish_action()}'
                keyboard = None
            else:
                answer = self.check_action(args)
                if answer is None:
                    answer = self.identified_pet.check_action(args)
                    if answer is None:
                        answer = f'{self.name} еще не умеет это делать'
                    else:
                        keyboard = self.get_actions_keyboard()
        if answer != -1:
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
            if bool(random.randint(0, 1)):
                self.bones += 1
                answer = f'{self.name} посадил{"" if self.is_male() else "a"} косточку!'
            else:
                answer = f'{self.name} посадил{"" if self.is_male() else "a"} косточку, но она не прижилась.'
            answer += f'\nВсего посажено {self.bones}🌳\n' \
                      f'Они приносят {round(self.bones * self.food_from_bone, 1)}🍎/{int(self.time_between_satiety / 60)}мин'
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
                  f'Они приносят {round(self.bones * self.food_from_bone, 1)}🍎/{int(self.time_between_satiety / 60)}мин'

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
                              f'Ваш баланс: {round(users_info.get(self.owner_id, {}).get("balance", 0), 1)}💰\n' \
                              f'Требуется: 0.5💰'
            else:
                if random.randint(1, 110) <= success:
                    users_info[self.owner_id]["balance"] += 5
                    answer_ = f'{self.name} выиграл{"" if self.is_male() else "a"} соревнования по {text_competition} ' \
                              f'и заработал{"" if self.is_male() else "a"} 5💰'
                else:
                    if self.features.get('luck', 0) > 0 and random.randint(0, 200) <= self.features.get('luck'):
                        users_info[self.owner_id]["balance"] += 3
                        answer_ = f'{self.name} ничего не выиграл{"" if self.is_male() else "a"} на соревнованиях ' \
                                  f'по {text_competition}, но удача оказалась на {"его" if self.is_male() else "ее"} ' \
                                  f'стороне, и спонсоры выдали поощрительный приз 3💰'
                    else:
                        answer_ = f'{self.name} занял{"" if self.is_male() else "a"} {random.randint(2, 100)} место ' \
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
                         f'Ваш баланс: {round(users_info.get(self.owner_id, {}).get("balance", 0), 1)}💰\n' \
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
            success = self.features.get('intellect', 0)
            text_competition = 'науке'
        elif args == 'competition.tug_of_war':
            success = self.features.get('intellect', 0) * 0.2 + \
                      self.features.get('power', 0) * 0.8
            text_competition = 'перетягиванию каната'
        elif args == 'competition.running':
            success = self.features.get('speed', 0)
            text_competition = 'бегу'
        elif args == 'competition.origami':
            success = self.features.get('neatness', 0)
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

        if (self.features.get('work_time_night') and
                datetime_time(hour=9) <= datetime.now(tz=tz).time() < datetime_time(hour=21)):
            self.action = None
            self.send_message_action(f'{self.name} работает только с 21:00 до 9:00')
            return -1
        elif (not self.features.get('work_time_night') and
              (datetime_time(hour=21) <= datetime.now(tz=tz).time() <= datetime_time(hour=23, minute=59, second=59) or
               datetime_time(hour=0) <= datetime.now(tz=tz).time() < datetime_time(hour=9))):
            self.action = None
            self.send_message_action(f'{self.name} работает только с 9:00 до 21:00')
            return -1
        else:
            all_works = {**self.works, **self.identified_pet.works}
            if args == 'work':
                buttons = []
                for work_name in list(all_works.keys()):
                    skills = all_works.get(work_name).get('skills')
                    for skill in list(skills.keys()):
                        if skills.get(skill) > self.features.get(skill):
                            break
                    else:
                        buttons += [[get_callback_button(
                            f'{work_name}, '
                            f'{all_works.get(work_name).get("salary_per_min")}'
                            f'{"💰" if all_works.get(work_name).get("salary_in") == "money" else "🍎"} в мин',
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
                    salary = round(floor((datetime.now(tz=tz) - self.time_start_action).seconds / 60) *
                                   all_works.get(self.work_name).get('salary_per_min'), 1)

                    answer = f'{self.name} вернул{"ся" if self.is_male() else "aсь"} с работы\n' \
                             f'Заработано: {salary}'
                    if all_works.get(self.work_name).get('salary_in') == 'money':
                        users_info[self.owner_id]["balance"] += salary
                        answer += '💰'
                    else:
                        self.food += salary
                        answer += '🍎'
                else:
                    self.work_name = args.replace('work.', '')
                    self.action = f'работает ({self.work_name})'
                    self.time_start_action = datetime.now(tz=tz)

                    now = datetime.now(tz=tz)
                    if self.features.get('work_time_night'):
                        self.time_finish_action = datetime(year=now.year, month=now.month, day=now.day, hour=9,
                                                           tzinfo=tz)
                        if now.time() <= datetime_time(hour=23, minute=59, second=59):
                            self.time_finish_action += timedelta(days=1)
                    else:
                        self.time_finish_action = datetime(year=now.year, month=now.month, day=now.day, hour=21,
                                                           tzinfo=tz)
                    self.timer_action = threading.Timer((self.time_finish_action - now).seconds,
                                                        function=self.work, args=['work.finish'])
                    self.timer_action.start()
                    answer = f'{self.name} начал{"" if self.is_male() else "a"} работать ({self.work_name})'
            else:
                answer = 'В настоящий момент данная работа недоступна'

            self.send_message_action(answer)
            return -1


class Minion:
    pet: Pet
    works: dict

    def __init__(self, pet: Pet):
        self.pet = pet
        self.works = {'Помощник главного злодея': {'skills': {'power': 20, 'industriousness': 70},
                                                   'salary_per_min': 1, 'salary_in': 'food'}}

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
            money = round(random.uniform(0.5, max(5, users_info.get(self.pet.owner_id, {}).get("balance", 0) / 10)), 1)
            price = round(random.uniform(0.0, 0.5), 2)
            food = int(money / max(price, 0.05))
            answer += f'украл{"" if self.pet.is_male() else "a"} у Вас {money}💰 и ' \
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
                      f'Сейчас жизней: {round(self.pet.lives, 1)}'
        elif action == 3:
            count = random.randint(30, 50)
            if self.pet.food >= count:
                self.pet.food -= count
                self.pet.features['power'] = 100
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
                          f'У Вас пополнение на {money}💰'
            else:
                money = round(random.uniform(0, min(users_info.get(self.pet.owner_id, {}).get("balance", 0), 10)), 1)
                users_info[self.pet.owner_id]["balance"] -= money
                answer += f'выкопал{"" if self.pet.is_male() else "a"} яму на дороге, в которую влетела ' \
                          f'полицейская машина.\n' \
                          f'У Вас штраф на {money}💰'
        else:
            answer = 'Что-то ничего не получилось'

        return answer


class FloraColossus:
    pet: Pet
    works: dict

    def __init__(self, pet: Pet):
        self.pet = pet
        self.works = {'Работник Call-центра': {'skills': {'intellect': 20, 'industriousness': 30},
                                               'salary_per_min': 1, 'salary_in': 'food'}}

    def get_action_buttons(self):
        # 'Яйцо': 60 * 10, 'Младенчество': 60 * 20, 'Детство': 60 * 60 * 24, 'Юность': 60 * 60 * 24 * 2,
        # 'Молодость': 60 * 60 * 24 * 7, 'Зрелость': 60 * 60 * 24 * 21, 'Старость': 0
        buttons = []
        if self.pet.age >= list(self.pet.ages.keys()).index('Детство'):
            if self.pet.features.get('health') == self.pet.features.get('power') == 100:
                buttons += [
                    [get_callback_button('Вырастить еду на себе, +20-40🍎', 'primary', {'args': 'to_small_tree'})]]
            else:
                buttons += [[get_callback_button('Стать большим деревом, -30🍎', 'primary', {'args': 'to_big_tree'})]]
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
                if self.pet.features.get('health') == self.pet.features.get('power') == 100:
                    answer = f'{self.pet.name} уже большой'
                else:
                    if self.pet.food < 30:
                        answer = f'Недостаточно 🍎 для роста.\n' \
                                 f'В кормушке: {self.pet.food}🍎\n' \
                                 f'Требуется: 30🍎'
                    else:
                        self.pet.food -= 30
                        self.pet.features['health'] = 100
                        self.pet.features['power'] = 100
                        self.pet.features['speed'] = 10
                        self.pet.features['industriousness'] = 10
                        self.pet.features['neatness'] = 10
                        answer = f'{self.pet.name} стал{"" if self.pet.is_male() else "a"} больше и ' \
                                 f'увеличил{"" if self.pet.is_male() else "a"} показатели здоровья и силы до 100/100, ' \
                                 f'однако скорость, трудолюбие и аккуратность стали всего 10/100\n' \
                                 f'Будьте внимательны: лекарства возвращают показатели в первоначальное состояние!'

        else:
            if self.pet.disease is not None:
                answer = f'{self.pet.name} болеет и не может выращивать еду'
            else:
                if self.pet.features.get('health') < 100 or self.pet.features.get('power') < 100:
                    answer = f'{self.pet.name} мал для выращивания еды'
                else:
                    food = random.randint(20, 40)
                    self.pet.food += food
                    self.pet.features = self.pet.get_features(*self.pet.level.get(self.pet.type)[1])
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
            pills = random.randint(0, 2)
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
            for pet in self.pet.game_pets.all_pets.get(self.pet.owner_id):
                if pet.action is None:
                    if bool(random.randint(0, 1)):
                        pet.features['intellect'] = 100
                    else:
                        pet.fall_ill()
            answer += f'прочитал{"" if self.pet.is_male() else "a"} всем незанятым питомцам лекцию по квантовой физике. ' \
                      f'Кто-то что-то понял и повысил показатели интеллекта до 100/100, а кто-то сошел с ума, заболел ' \
                      f'и требует Вашего внимания.\n' \
                      f'{self.pet.name} сказал{"" if self.pet.is_male() else "a"}, что ' \
                      f'он{"" if self.pet.is_male() else "a"} тут не при чем, это просто неокрепший мозг!'
        elif action == 3:
            answer += f'подсмотрел{"" if self.pet.is_male() else "a"} у Вашего Миньона рецепт зелья силы и ' \
                      f'усовершенствовал{"" if self.pet.is_male() else "a"} его: приготовленное зелье не затратило 🍎.\n'
            if bool(random.randint(0, 1)):
                for pet in self.pet.game_pets.all_pets.get(self.pet.owner_id):
                    if pet.action is None:
                        if bool(random.randint(0, 1)):
                            pet.features['power'] = 50
                        else:
                            pet.fall_ill()
                answer += 'Однако получился странный эффект: оно не увеличивает силу, а устанавливает ее ровно на ' \
                          '50/100.\n'
            else:
                feature = random.choice(['health', 'intellect', 'speed', 'industriousness', 'neatness'])
                new_value = random.randint(20, 80)
                for pet in self.pet.game_pets.all_pets.get(self.pet.owner_id):
                    if pet.action is None:
                        if bool(random.randint(0, 1)):
                            pet.features[feature] = new_value
                        else:
                            pet.fall_ill()
                answer += f'К сожалению, что-то пошло не так, и вместо силы зелье меняет параметр ' \
                          f'{self.pet.translate(feature)} до {new_value}/100.\n'
            answer += 'Тем не менее, все незанятые питомцы получили свою дозу! ' \
                      'Кому-то, правда, зелье не пошло и появились признаки болезни...'
        elif action == 4:
            money = random.randint(1, 15)
            users_info[self.pet.owner_id]["balance"] += money
            answer += f'выиграл{"" if self.pet.is_male() else "a"} международную олимпиаду по математическому ' \
                      f'описанию физической модели биотехнофилософского обоснования возможности существования расы ' \
                      f'Флора Колосс, так как является представителем данной рассы, и ' \
                      f'заработал{"" if self.pet.is_male() else "a"} {money * 10}💰, ' \
                      f'большая часть которых ушла на оплату проезда и вступительного взноса.' \
                      f'Заработано: {money}💰'
            if bool(random.randint(0, 1)):
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
                                                  'salary_per_min': 0.1, 'salary_in': 'money'},
                      f'Дояр{"" if self.pet.is_male() else "кa"} насосавшихся комаров': {
                          'skills': {'speed': 20, 'industriousness': 30, 'neatness': 30},
                          'salary_per_min': 2, 'salary_in': 'food'}}

    def get_action_buttons(self):
        # 'Яйцо': 60 * 10, 'Младенчество': 60 * 20, 'Детство': 60 * 60 * 24, 'Юность': 60 * 60 * 24 * 2,
        # 'Молодость': 60 * 60 * 24 * 7, 'Зрелость': 60 * 60 * 24 * 21, 'Старость': 0
        buttons = []
        if self.pet.age >= list(self.pet.ages.keys()).index('Детство'):
            buttons += [[get_callback_button('Использовать регенерацию', 'primary', {'args': 'use_regeneration'})]]
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
            answer = f'{self.pet.name} избавился от болезней и полностью восстановил жизни'
        else:
            self.pet.action = 'использует навык регенерации'
            self.pet.timer_action = threading.Timer(60 * 5, function=self.use_regeneration, args=[True])
            self.pet.timer_action.start()
            self.pet.time_finish_action = datetime.now(tz=tz) + timedelta(seconds=60 * 5)
            answer = f'{self.pet.name} начал{"" if self.pet.is_male() else "a"} регенерироваться.'
        return answer

    def eat_garlic(self):
        self.pet.fall_ill()
        answer = f'{self.pet.name} отравился и заболел. А Вы чего хотели?'
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
                    pet.features = pet.get_features(*pet.level.get(pet.type)[1])
                    pet.status = 'стал вампиром'
                    break
            answer = f'{self.pet.name} обратил питомца {name} в вампира'

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
            answer += 'Он потерял все жизни!'
            leave = True
        else:
            self.pet.fall_ill()
            answer += 'Он заболел! И хорошо, что только заболел.'

        vk_session.method('messages.send',
                          {'user_id': int(self.pet.owner_id),
                           'message': answer,
                           'random_id': 0})
        if leave:
            self.pet.leave(False)

    def use_hypnosis(self):
        pass
