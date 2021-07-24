import random
from vk_auth import *
from keyboard import *
from data import game_math_stats, game_math_top
import json
import threading


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
    end_keyboard = None
    continue_game_keyboard = None
    timers = {}

    def __init__(self):
        self.texts = [
            # 0
            'Кто это тут у нас рискнул сыграть со мной в игру?',
            # 1
            'Правила просты: я даю тебе пример, 4 варианта ответа и 5 секунд на размышления.\n'
            'Успеешь выбрать правильный - получишь следующий пример.\n'
            'Не успеешь - игра окончена.\n'
            'В игре несколько уровней, и каждый новый вносит усложнения примеров.\n'
            'Между уровнями у тебя будет время на перерыв.\n'
            'Рекомендую отдыхать секунд 10-20, чтобы злой VK не просил тебя ввести капчу. '
            'Ну, и чтобы я успел составить еще примерчиков!\n\n'
            'Если все понятно - жми кнопку и погнали!',
            # 2
            'Игра окончена!']

        self.game_levels = {
            0: {"min": 10, "max": 20, "actions": [plus]},
            1: {"min": 10, "max": 50, "actions": [plus]},
            2: {"min": 10, "max": 99, "actions": [plus]},

            3: {"min": 10, "max": 20, "actions": [plus, minus]},
            4: {"min": 10, "max": 50, "actions": [plus, minus]},
            5: {"min": 10, "max": 99, "actions": [plus, minus]},

            6: {"min": 5, "max": 10, "actions": [multiplication]},
            7: {"min": 5, "max": 20, "actions": [multiplication]},
            8: {"min": 5, "max": 50, "actions": [multiplication]},

            9: {"min": 5, "max": 10, "actions": [multiplication, division]},
            10: {"min": 5, "max": 20, "actions": [multiplication, division]},
            11: {"min": 5, "max": 50, "actions": [multiplication, division]},

            12: {"min": 1000, "max": 5000, "actions": [plus, minus, multiplication, division]},
        }

        self.start_keyboard = str(json.dumps(
            {
                "inline": True,
                "buttons": [
                    [get_text_button('Правила', 'primary'), get_text_button('Начать', 'positive')]
                ]
            },
            ensure_ascii=False))

        self.end_keyboard = str(json.dumps(
            {
                "inline": True,
                "buttons": [
                    [get_text_button('!Играть', 'positive'), get_text_button('!Рейтинг', 'primary')]
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

        # Инициализация gamers_active.json TODO: сюда можно пристроить self.end() для игравших во время стопа бота
        with open("gamers_active.json", "r", encoding='utf-8') as read_file:
            if len(read_file.read()) != 0:
                read_file.seek(0)
                file = json.load(read_file)
            else:
                file = {'top': {}}
            read_file.close()
        with open("gamers_active.json", "w") as write_file:
            json.dump({'stats': {}, 'top': file.get('top')}, write_file)
            write_file.close()

    def handler(self, user_id, message):
        user_id = str(user_id)
        if message.lower() == 'правила':
            self.rules(user_id)
        elif message.lower() == 'начать' or message.lower() == 'продолжить' or \
                message.isdigit() or (len(message) > 1 and message[1:].isdigit()):
            self.game(user_id, message)
        else:
            self.end(user_id)

    def start(self, user_id):
        user_id = str(user_id)
        vk_session.method('messages.send',
                          {'user_id': int(user_id), 'message': self.texts[0],
                           'random_id': 0, 'keyboard': self.start_keyboard})
        game_math_stats.update({user_id: {"answer": None, "score": 0}})
        self.save(user_id)

    def end(self, user_id):
        if user_id in self.timers.keys():
            self.timers.pop(user_id)
        vk_session.method('messages.send',
                          {'user_id': int(user_id), 'message': "{}\nВы дали правильных ответов: {}"  # TODO: Добавить "Ваш рекорд"
                                                    .format(self.texts[2], game_math_stats.get(user_id).get('score')),
                           'random_id': 0, 'keyboard': self.end_keyboard})
        self.save(user_id, True)

    @staticmethod
    def save(user_id, is_delete=False):
        if game_math_top == {} or \
                game_math_top.get(user_id) is None or \
                game_math_stats.get(user_id).get('score') > game_math_top.get(user_id).get('record'):
            user = vk_session.method('users.get', {'user_ids': int(user_id)})[0]
            name = user.get('first_name') + ' ' + user.get('last_name')
            game_math_top.update({user_id: {'name': name, 'record': game_math_stats.get(user_id).get('score')}})
        if is_delete:
            game_math_stats.pop(user_id)

    def rules(self, user_id):
        vk_session.method('messages.send',
                          {'user_id': int(user_id), 'message': self.texts[1],
                           'random_id': 0, 'keyboard': self.start_keyboard})

    def game(self, user_id, answer):
        user_id = str(user_id)
        answer = str(answer)

        if game_math_stats.get(user_id).get('score') % 5 == 0 and answer.lower() == "":

            vk_session.method('messages.send',
                              {'user_id': int(user_id), 'message': "Вы перешли на уровень {}"
                                                                   "\nРекомендую отдохнуть 10-20 секунд!"
                                                        .format(game_math_stats.get(user_id).get('score') // 5),
                               'random_id': 0, 'keyboard': self.continue_game_keyboard})

        elif game_math_stats.get(user_id).get('answer') is None:
            self.new_formula(user_id)

        elif str(game_math_stats.get(user_id).get('answer')) == answer:
            try:
                self.timers.get(user_id).cancel()
            except AttributeError:
                pass
            game_math_stats.update(
                {user_id: {'answer': None, 'score': game_math_stats.get(user_id).get('score') + 1}})
            vk_session.method('messages.send',
                              {'user_id': int(user_id), 'message': "Ваш ответ {} верный!\nВсего правильных ответов: {}!"
                                                        .format(answer, game_math_stats.get(user_id).get('score')),
                               'random_id': 0})
            self.game(user_id, "")

        else:
            self.timers.get(user_id).cancel()
            vk_session.method('messages.send',
                              {'user_id': int(user_id), 'message': "Ваш ответ {} неверный!\nВерный ответ: {}!"
                                                        .format(answer, game_math_stats.get(user_id).get('answer')),
                               'random_id': 0})
            self.end(user_id)

    def new_formula(self, user_id):
        symbol = ""
        level = game_math_stats.get(user_id).get("score") // 5  # 5 примеров на каждом уровне
        if level > 12:
            level = 12
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
                          {'user_id': int(user_id), 'message': "Уровень " + str(level) +
                                                               "\nСколько будет {} {} {}?"
                                                    .format(formula[0], symbol, formula[1]),
                           'random_id': 0, 'keyboard': create_keyboard(nums)})

        game_math_stats.update({user_id: {'answer': res, 'score': game_math_stats.get(user_id).get('score')}})

        self.timers.update({user_id: threading.Timer(5, self.end, {user_id})})
        self.timers.get(user_id).start()

    @staticmethod
    def get_top(arg=None):
        with open("gamers_active.json", "r", encoding='utf-8') as read_file:
            top = json.load(read_file).get('top')
            read_file.close()
        top_sort = []
        for gamer in top:
            top_sort.append([top.get(gamer).get('name'), top.get(gamer).get('record')])
        top_sort.sort(key=get_points, reverse=True)

        string_top = str()
        num = 0
        for gamer in top_sort:
            num += 1
            string_top += "{}. {}:\n Верных ответов: {}\n\n".format(num, gamer[0], gamer[1])
        # Минутка хвастовства
        if top_sort[0][0] == "Александр Березин":
            string_top += "О, мой хозяин на первом месте!&#128526;"
        return string_top
