import random
import json
import threading
from vk_auth import vk_session, VkBotEventType
from keyboard import *
from data import game_math_stats, game_math_top, users_info, change_class


def create_keyboard(nums):
    return str(json.dumps(
        {
            "inline": True,
            "buttons": [
                [get_callback_button(f'{nums[0]}', 'positive', {"method": "GameMath.game", "args": nums[0]}),
                 get_callback_button(f'{nums[1]}', 'positive', {"method": "GameMath.game", "args": nums[1]})],

                [get_callback_button(f'{nums[2]}', 'positive', {"method": "GameMath.game", "args": nums[2]}),
                 get_callback_button(f'{nums[3]}', 'positive', {"method": "GameMath.game", "args": nums[3]})]
            ]
        },
        ensure_ascii=False))


def plus(rand_min, rand_max):
    a = random.randint(rand_min, rand_max)
    b = random.randint(rand_min, rand_max)
    return [a, b, a + b]


def minus(rand_min, rand_max):
    a = random.randint(rand_min, rand_max)
    b = random.randint(rand_min, rand_max)
    return [a, b, a - b]


def multiplication(rand_min, rand_max):
    a = random.randint(rand_min, rand_max)
    b = random.randint(rand_min, rand_max)
    return [a, b, a * b]


def division(rand_min, rand_max):
    a = random.randint(rand_min, rand_max)
    b = random.randint(rand_min, rand_max)
    return [a * b, a, b]


def get_points(gamer):
    return gamer[1]


class GameMath:
    texts = None
    game_levels = None
    start_keyboard = None
    end_keyboard_without_lives = None
    end_keyboard_with_lives = None
    end_keyboard = None
    continue_game_keyboard = None
    timers = {}

    def __init__(self):
        self.texts = [  # TODO: Поменять на что-то нормальное
            # 0
            'Приветствую тебя, математик великий! Сыграть в игру захотел со мной?',
            # 1
            'Правила просты: я даю тебе пример, 4 варианта ответа и 5 секунд на размышления.\n'
            'Успеешь выбрать правильный - получишь следующий пример.\n'
            'Не успеешь - игра окончена.\n\n'
            'В игре несколько уровней, и каждый новый вносит усложнения примеров.\n'
            'Между уровнями у тебя будет время на перерыв.\n'
            'Рекомендую отдыхать секунд 10-20, чтобы освежить свой разум.'
            'Ну, и чтобы я успел составить еще примерчиков!\n\n'
            'Если у тебя есть ❤, ты можешь продолжить игру с момента своего поражения!\n'
            'Бонус для новых игроков: 5❤.\n'
            'За первое достижение каждых 15 верных ответов (15, 30, 45, ...) ты получишь дополнительные 3❤ по окончании игры.\n'
            'За достижение 5 уровня и каждого последующего ты получишь дополнительное ❤.\n\n'
            'Если все понятно - жми кнопку и погнали!',
            # 2
            'Игра окончена!']

        self.game_levels = {
            0: {"min": 0, "max": 10, "actions": [plus]},
            1: {"min": 0, "max": 20, "actions": [plus]},
            2: {"min": 0, "max": 50, "actions": [plus]},

            3: {"min": 0, "max": 5, "actions": [multiplication]},
            4: {"min": 0, "max": 10, "actions": [multiplication]},
            5: {"min": 0, "max": 20, "actions": [multiplication]},

            6: {"min": 0, "max": 10, "actions": [minus]},
            7: {"min": 0, "max": 20, "actions": [minus]},
            8: {"min": 0, "max": 50, "actions": [minus]},

            9: {"min": 0, "max": 5, "actions": [division]},
            10: {"min": 0, "max": 10, "actions": [division]},
            11: {"min": 0, "max": 20, "actions": [division]},

            12: {"min": -10, "max": 10, "actions": [plus]},
            13: {"min": -20, "max": 20, "actions": [plus]},
            14: {"min": -50, "max": 50, "actions": [plus]},

            15: {"min": -5, "max": 5, "actions": [multiplication]},
            16: {"min": -10, "max": 10, "actions": [multiplication]},
            17: {"min": -20, "max": 20, "actions": [multiplication]},

            18: {"min": -10, "max": 10, "actions": [minus]},
            19: {"min": -20, "max": 20, "actions": [minus]},
            20: {"min": -50, "max": 50, "actions": [minus]},

            21: {"min": -5, "max": 5, "actions": [division]},
            22: {"min": -10, "max": 10, "actions": [division]},
            23: {"min": -20, "max": 20, "actions": [division]},

            24: {"min": 100, "max": 150, "actions": [plus, minus]},
            25: {"min": 100, "max": 200, "actions": [plus, minus]},
            26: {"min": 100, "max": 300, "actions": [plus, minus]},

            27: {"min": 0, "max": 50, "actions": [multiplication, division]},
            28: {"min": 0, "max": 100, "actions": [multiplication, division]},
            29: {"min": 0, "max": 150, "actions": [multiplication, division]},

            30: {"min": 1000, "max": 5000, "actions": [plus, minus, multiplication, division]},
        }

        self.start_keyboard = str(json.dumps(
            {
                "one_time": True,
                "buttons": [
                    [get_text_button('Правила', 'primary'), get_text_button('Начать', 'positive')],
                    [get_text_button('Обменять 5❤ на 1💰', 'primary')],
                    [get_text_button('Рейтинг математики', 'secondary')],
                    [get_text_button('Завершить игру', 'negative')]
                ]
            },
            ensure_ascii=False))

        self.end_keyboard = str(json.dumps({
                "one_time": False,
                "buttons": [
                    [get_text_button('!Все запросы', 'primary'), get_text_button('!Все команды', 'primary')]
                ]
            }, ensure_ascii=False))

        self.end_keyboard_without_lives = str(json.dumps(
            {
                "inline": True,
                "buttons": [
                    [get_text_button('Новая игра', 'primary'), get_text_button('Завершить игру', 'negative')],
                    [get_text_button('Рейтинг математики', 'secondary')]
                ]
            },
            ensure_ascii=False))

        self.end_keyboard_with_lives = str(json.dumps(
            {
                "inline": True,
                "buttons": [
                    [get_callback_button('Использовать ❤', 'positive', {"method": "GameMath.use_lives", "args": None})],
                    [get_text_button('Новая игра', 'primary'), get_text_button('Завершить игру', 'negative')],
                    [get_text_button('Рейтинг математики', 'secondary')]
                ]
            },
            ensure_ascii=False))

        self.continue_game_keyboard = str(json.dumps(
            {
                "inline": True,
                "buttons": [
                    [get_text_button('Продолжить', 'positive')]
                ]
            },
            ensure_ascii=False))

    def process_event(self, event):
        """ Обработка сообщений от пользователя для игры "Математика"

        :param event: событие, пришедшее в VkBotLongPoll
        :type event: :class:`Event`
        """
        if event is None:
            return

        if event.type == VkBotEventType.MESSAGE_EVENT:
            user_id = str(event.obj.user_id)

            method = event.obj.payload.get('method')
            if method == "GameMath.game":
                if self.cancel_timer(user_id):
                    self.game(user_id, event.obj.payload.get('args'))
            elif method == "GameMath.use_lives":
                self.use_live(user_id)

            vk_session.method('messages.sendMessageEventAnswer',
                              {'event_id': event.obj.event_id,
                               'user_id': int(user_id),
                               'peer_id': event.obj.peer_id})

        elif event.type == VkBotEventType.MESSAGE_NEW:
            user_id = str(event.obj.from_id)
            message = event.obj.text.lower()

            if message == 'начать' or message == 'продолжить':
                self.cancel_timer(user_id)
                self.game(user_id, message)
            elif message == 'новая игра':
                self.cancel_timer(user_id)
                self.start(user_id)
            elif message == 'правила':
                self.rules(user_id)
            elif message == 'рейтинг математики':
                self.get_top(user_id)
            elif message == 'завершить игру':
                self.end(user_id, True)
            elif message == 'обменять 5❤ на 1💰':
                self.exchange_lives_for_balance(user_id)
            else:
                self.end(user_id)

    def start(self, user_id):
        user_id = str(user_id)
        if game_math_stats.get(user_id) is None:
            # Регистрация нового ирока
            game_math_stats.update({user_id: {'is_active': True, 'lives': 5, 'answer': None, 'score': 0}})
        else:
            # Начало игры с уже существующим игроком
            game_math_stats.update({user_id: {'is_active': True, 'lives': game_math_stats.get(user_id).get('lives'),
                                              'answer': None, 'score': 0}})

        vk_session.method('messages.send',
                          {'user_id': int(user_id), 'message': self.texts[0] +
                              f'\nНа счету {game_math_stats.get(user_id).get("lives")}❤',
                           'random_id': 0, 'keyboard': self.start_keyboard})

    def end(self, user_id, back=False):
        user_id = str(user_id)
        self.cancel_timer(user_id)

        # Обновление рейтинга, если надо
        if game_math_stats.get(user_id, {}).get('score', 0) > game_math_top.get(user_id, {}).get('record', 0):
            # Начисление бонусных жизней, если игрок побил личный рекорд, но >= 15 очков
            for score in range(15, game_math_stats.get(user_id).get('score'), 15):
                if game_math_top.get(user_id, {}).get('record', 0) < score:
                    game_math_stats[user_id]['lives'] += 3
                    vk_session.method('messages.send',
                                      {'user_id': int(user_id),
                                       'message': f'Вы впервые дали более {score} верных ответов и зарабатываете 3❤!\n'
                                                  f'На счету {game_math_stats.get(user_id).get("lives")}❤',
                                       'random_id': 0})

            # Получение имени и фамилии игрока
            user = vk_session.method('users.get', {'user_ids': int(user_id)})[0]
            name = f"{user.get('first_name')} {user.get('last_name')}"

            # Запись нового рекорда в рейтинг
            game_math_top.update({user_id: {'name': name, 'record': game_math_stats.get(user_id).get('score')}})

        if back:
            # Если пользователь хочет закончить игру
            vk_session.method('messages.send',
                              {'user_id': int(user_id),
                               'message': 'Спасибо за игру!\nПомни, что ты всегда можешь побить свой рекорд!',
                               'random_id': 0, 'keyboard': self.end_keyboard})

            game_math_stats[user_id]['score'] = 0
            change_class(user_id, 'autoresponder')

        elif game_math_stats.get(user_id).get('lives') > 0 and game_math_stats.get(user_id).get('is_active'):
            # Если есть жизни
            vk_session.method('messages.send',
                              {'user_id': int(user_id),
                               'message': f'Вы дали правильных ответов: {game_math_stats.get(user_id).get("score")}\n'
                                          f'Ваш рекорд: {game_math_top.get(user_id).get("record")}\n'
                                          f'На счету {game_math_stats.get(user_id).get("lives")}❤\n'
                                          f'Желаете продолжить игру?',
                               'random_id': 0, 'keyboard': self.end_keyboard_with_lives})
        else:
            # Если нет жизней
            vk_session.method('messages.send',
                              {'user_id': int(user_id),
                               'message': f'Вы дали правильных ответов: {game_math_stats.get(user_id).get("score")}\n'
                                          f'Ваш рекорд: {game_math_top.get(user_id).get("record")}\n'
                                          f'На счету {game_math_stats.get(user_id).get("lives")}❤\n'
                                          f'Сыграем еще раз?',
                               'random_id': 0, 'keyboard': self.end_keyboard_without_lives})

        # Обновление значений
        game_math_stats[user_id]['is_active'] = False
        game_math_stats[user_id]['answer'] = None

    def rules(self, user_id):
        vk_session.method('messages.send',
                          {'user_id': int(user_id), 'message': self.texts[1],
                           'random_id': 0, 'keyboard': self.start_keyboard})

    def game(self, user_id, answer):
        user_id = str(user_id)
        answer = str(answer)

        self.cancel_timer(user_id)

        if not game_math_stats.get(user_id).get('is_active'):
            if answer == "":
                self.start(user_id)
            return

        # Если дано кратно 5 верных ответов -> переход на новый уровень
        if answer == "" and game_math_stats.get(user_id).get('score') % 5 == 0:

            if game_math_stats.get(user_id).get('score') >= 25:
                game_math_stats[user_id]['lives'] += 1
                vk_session.method('messages.send',
                                  {'user_id': int(user_id),
                                   'message': f'Вы достигли больших результатов и зарабатываете ❤!\n'
                                              f'На счету {game_math_stats.get(user_id).get("lives")}❤',
                                   'random_id': 0})

            vk_session.method('messages.send',
                              {'user_id': int(user_id),
                               'message': f'Вы перешли на уровень {game_math_stats.get(user_id).get("score") // 5}\n'
                                          f'Рекомендую отдохнуть 10-20 секунд!',
                               'random_id': 0, 'keyboard': self.continue_game_keyboard})

        # Если не ожидается никакого ответа -> создать новый пример
        elif game_math_stats.get(user_id).get('answer') is None:
            self.new_formula(user_id)

        # Проверка ответа на правильность
        elif str(game_math_stats.get(user_id).get('answer')) == answer:
            game_math_stats.update(
                {user_id: {'is_active': True, 'lives': game_math_stats.get(user_id).get('lives'),
                           'answer': None, 'score': game_math_stats.get(user_id).get('score') + 1}})
            vk_session.method('messages.send',
                              {'user_id': int(user_id),
                               'message': f'Ваш ответ "{answer}" верный!\n'
                                          f'Всего правильных ответов: "{game_math_stats.get(user_id).get("score")}"!',
                               'random_id': 0})
            self.game(user_id, "")

        # Окончание игры
        else:
            vk_session.method('messages.send',
                              {'user_id': int(user_id),
                               'message': f'Ваш ответ "{answer}" неверный!\n'
                                          f'Верный ответ: "{game_math_stats.get(user_id).get("answer")}"!',
                               'random_id': 0})
            self.end(user_id)

    def new_formula(self, user_id):
        symbol = ""
        level = game_math_stats.get(user_id).get("score") // 5  # 5 примеров на каждом уровне
        if level >= len(self.game_levels):
            level = len(self.game_levels) - 1
        rand_min = self.game_levels.get(level).get("min")
        rand_max = self.game_levels.get(level).get("max")

        action = random.choice(self.game_levels.get(level).get("actions"))
        if action == plus:
            symbol = '+'
        elif action == minus:
            symbol = '-'
        elif action == multiplication:
            symbol = '*'
        elif action == division:
            symbol = '/'
        formula = action(rand_min, rand_max)
        num2 = num3 = num4 = res = formula[2]

        while num2 == res or num3 == res or num4 == res or num2 == num3 or num2 == num4 or num3 == num4:
            num2 = random.randint(res - 10, res + 10)
            num3 = random.randint(res - 10, res + 10)
            num4 = random.randint(res - 10, res + 10)

        nums = [res, num2, num3, num4]
        random.shuffle(nums)

        vk_session.method('messages.send',
                          {'user_id': int(user_id), 'message': "Уровень {}\nСколько будет {} {} {}?"
                                                    .format(str(level), formula[0], symbol, formula[1]),
                           'random_id': 0, 'keyboard': create_keyboard(nums)})

        game_math_stats.update(
            {user_id: {'is_active': True, 'lives': game_math_stats.get(user_id).get('lives'),
                       'answer': res, 'score': game_math_stats.get(user_id).get('score')}})

        self.start_timer(user_id)

    def start_timer(self, user_id):
        self.timers.update({user_id: threading.Timer(5, self.end, {user_id})})
        self.timers.get(user_id).start()

    def cancel_timer(self, user_id):
        if self.timers.get(user_id) is not None:
            self.timers.get(user_id).cancel()
            return True
        return False

    def use_live(self, user_id):
        """ Использование жизни для продолжения игры.
        Если пользователь сейчас играет или у него нет жизней, запрос игнорируется.

        :param user_id: ID пользователя, вызвавшего команду.
        :type user_id: int или str.

        :return: None.
        """
        user_id = str(user_id)
        if not game_math_stats.get(user_id, {}).get('is_active', True) and \
                game_math_stats.get(user_id, {}).get('lives', 0) > 0:
            game_math_stats[user_id]['is_active'] = True
            game_math_stats[user_id]['lives'] -= 1
            self.game(user_id, None)

    def get_top(self, user_id):
        """ Предоставление списка рейтинга игры "Математика".

        :param user_id: ID пользователя, вызвавшего команду.
        :type user_id: int или str.
        """
        top_sort = []
        for gamer in game_math_top.values():
            top_sort.append([gamer.get('name'), gamer.get('record')])
        top_sort.sort(key=get_points, reverse=True)

        string_top = str()
        num = 0
        for gamer in top_sort:
            num += 1
            string_top += "{}. {}:\n Верных ответов: {}\n\n".format(num, gamer[0], gamer[1])

        # Минутка хвастовства
        if top_sort[0][0] == "Александр Березин":
            string_top += "О, мой хозяин на первом месте!&#128526;"

        if game_math_stats[str(user_id)]['is_active']:
            vk_session.method('messages.send',
                              {'user_id': int(user_id), 'message': string_top, 'random_id': 0,
                               'keyboard': self.start_keyboard})
        else:
            vk_session.method('messages.send',
                              {'user_id': int(user_id), 'message': string_top, 'random_id': 0})

    def exchange_lives_for_balance(self, user_id):
        user_id = str(user_id)

        if game_math_stats.get(user_id, {}).get('lives', 0) >= 5:
            users_info[user_id]['balance'] += 1
            game_math_stats[user_id]['lives'] -= 5

            message = f'Вы обменяли 5❤ на 1💰\n'\
                      f'На счету {game_math_stats.get(user_id).get("lives")}❤\n'\
                      f'Ваш баланс: {users_info[user_id]["balance"]}💰'

        else:
            message = f'Недостаточно ❤ для совершения обмена\n' \
                      f'На счету {game_math_stats.get(user_id).get("lives")}❤\n'

        keyboard = None
        if game_math_stats[user_id]['is_active']:
            keyboard = self.start_keyboard

        vk_session.method('messages.send',
                          {'user_id': int(user_id), 'message': message, 'random_id': 0,
                           'keyboard': keyboard})
