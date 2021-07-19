import random

from vk_auth import *
from keyboard import *
import json
import threading


def create_keyboard(nums):
    return str(json.dumps(
        {
            "inline": True,
            "buttons": [
                [get_text_button(f'{nums[0]}', 'positive'), get_text_button(f'{nums[1]}', 'positive')],
                [get_text_button(f'{nums[2]}', 'positive'), get_text_button(f'{nums[3]}', 'positive')]
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


def multiplication (rand_min, rand_max):
    a = random.randint(rand_min, rand_max)
    b = random.randint(rand_min, rand_max)
    return [a, b, a * b]


def division(rand_min, rand_max):
    a = random.randint(rand_min, rand_max)
    b = random.randint(rand_min, rand_max)
    return [a * b, a, b]


class Games:
    texts = []
    start_keyboard = []
    end_keyboard = []
    continue_game_keyboard = []
    gamers_stats = {}
    timers = {}
    game_levels = {}

    def __init__(self):
        self.texts = [
            # 0
            'Кто это тут у нас рискнул сыграть со мной в игру?',
            # 1
            'Правила просты: я даю тебе пример, 4 варианта ответа и 5 секунд на размышления.\n'
            'Успеешь выбрать правильный - получишь следующий пример.\n'
            'Не успеешь - игра окончена.\n'
            'В игре несколько уровней, и каждый новый вносит усложнения примеров.\n'
            'Между уровнями у тебя будет время на перерыв. Рекомендую отдыхать секунд 10-20, чтобы злой VK не просил тебя ввести капчу.'
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
                "one_time": False,
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

        # Инициализация gamers_active.json TODO: сюда можно пристроить end'ы для игравших во время стопа бота
        with open("gamers_active.json", "r") as read_file:
            if len(read_file.read()) != 0:
                read_file.seek(0)
                file = json.load(read_file)
            else:
                file = {'top': {}}
            read_file.close()
        with open("gamers_active.json", "w") as write_file:
            json.dump({'stats': {}, 'top': file.get('top')}, write_file)
            write_file.close()

        # Инициализация self.gamers_stats
        with open("gamers_active.json", "r") as read_file:
            self.gamers_stats = json.load(read_file).get('stats')
            read_file.close()

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
        self.gamers_stats.update({user_id: {"answer": None, "score": 0}})
        self.save(user_id)

    def end(self, user_id):
        if user_id in self.timers.keys():
            self.timers.pop(user_id)
        vk_session.method('messages.send',
                          {'user_id': int(user_id), 'message': self.texts[2] + " Вы набрали " + str(
                              self.gamers_stats.get(user_id).get('score')) + " баллов!",
                           'random_id': 0, 'keyboard': self.end_keyboard})
        self.save(user_id, True)

    def save(self, user_id, is_delete=False):
        with open("gamers_active.json", "r") as read_file:
            file = json.load(read_file)
            read_file.close()
        with open("gamers_active.json", "w") as write_file:
            if file.get('top') is None or \
                    file.get('top').get(user_id) is None or \
                    self.gamers_stats.get(user_id).get('score') > file.get('top').get(user_id):
                file.get('top').update({user_id: self.gamers_stats.get(user_id).get('score')})
            if is_delete:
                self.gamers_stats.pop(user_id)
            json.dump({'stats': self.gamers_stats, 'top': file.get('top')}, write_file)
            write_file.close()

    def rules(self, user_id):
        vk_session.method('messages.send',
                          {'user_id': int(user_id), 'message': self.texts[1],
                           'random_id': 0, 'keyboard': self.start_keyboard})

    def game(self, user_id, answer):
        if self.gamers_stats.get(user_id).get('score') % 5 == 0 and answer.lower() == "":

            vk_session.method('messages.send',
                              {'user_id': int(user_id), 'message': "Вы перешли на уровень " + str(
                                  self.gamers_stats.get(user_id).get('score') // 5) + 
                                  "\nРекомендую отдохнуть 10-20 секунд!",
                               'random_id': 0, 'keyboard': self.continue_game_keyboard})

        elif self.gamers_stats.get(user_id).get('answer') is None:
            self.new_formula(user_id)
        elif str(self.gamers_stats.get(user_id).get('answer')) == answer:
            try:
                self.timers.get(user_id).cancel()
            except AttributeError:
                pass
            self.gamers_stats.update(
                {user_id: {'answer': None, 'score': self.gamers_stats.get(user_id).get('score') + 1}})
            vk_session.method('messages.send',
                              {'user_id': int(user_id), 'message': "Верно!\nВы дали правильных ответов: "
                                                                   + str(
                                  self.gamers_stats.get(user_id).get('score')) + "!",
                               'random_id': 0})
            self.game(user_id, "")
        else:
            self.timers.get(user_id).cancel()
            self.end(user_id)

    def new_formula(self, user_id):
        symbol = ""
        level = self.gamers_stats.get(user_id).get("score") // 5  # TODO: Подумать над делителем
        if level > 12:
            level = 12
        rand_min = self.game_levels.get(level).get("min")
        rand_max = self.game_levels.get(level).get("max")

        action = random.choice(self.game_levels.get(level).get("actions"))
        if action == plus:
            symbol = ' + '
        elif action == minus:
            symbol = ' - '
        elif action == multiplication:
            symbol = ' * '
        elif action == division:
            symbol = ' / '
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
                                                               "\nСколько будет " + str(formula[0]) + symbol +
                                                               str(formula[1]) + "?",
                           'random_id': 0, 'keyboard': create_keyboard(nums)})

        self.gamers_stats.update({user_id: {'answer': res, 'score': self.gamers_stats.get(user_id).get('score')}})

        self.timers.update({user_id: threading.Timer(5, self.end, {user_id})})
        self.timers.get(user_id).start()
