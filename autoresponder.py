from game_math import GameMath
from vk_auth import *
from keyboard import *
from data import game_math_stats
import threading
import json
import random


def is_command(msg):
    return msg[0] == '!'


def is_correct_character(character):
    return str.isalpha(character) or character == ' '


class Autoresponder:
    """Класс ответов на сообщения пользователей"""
    answers = {}
    commands = {}
    errors = {}
    user_id = 0  # TODO: Нехорошо так хранить
    game_math_class = GameMath()

    is_stickers_active = False

    def __init__(self):
        with open("answers.json", "r") as read_file:
            if len(read_file.read()) == 0:
                arg = "Привет\nПривет, мой друг!"
                self.addResponse(arg)
            else:
                read_file.seek(0)
                self.answers = json.load(read_file)
            read_file.close()

        self.commands = {'!добавить': [self.addResponse, "\nЗапрос\nОтвет\nОтвет\n..."],
                         '!удалить запрос': [self.deleteAllResponses, "\nЗапрос"],
                         '!удалить ответы': [self.deleteResponse, "\nЗапрос\nОтвет\nОтвет\n..."],
                         '!все запросы': [self.getAllRequests, ""],
                         '!все команды': [self.getAllCommands, ""],
                         '!стикеры': [self.stickers, "\n1 - включить; 0 - выключить"],
                         '!играть': [self.game_math_start, ""],
                         '!рейтинг': [self.game_math_class.get_top, ""],
                         '!таймер': [self.timer, "\nЧисло секунд"]
                         }
        self.errors = [
            # 0
            'Я пока что не знаю этой фразы ;o\nВы можете обучить меня, введя команду !добавить'
            '\nУзнать все доступные запросы: !все запросы',
            # 1
            'Неизвестная команда.\nУзнать список доступных команд и их синтаксис: !все команды',
            # 2
            'Неверные аргументы.\nУзнать список доступных команд и их синтаксис: !все команды',
            # 3
            'Длина ответа не может быть меньше 2']

    def respond(self, user_id, msg):
        self.user_id = user_id

        # Если пользователь НЕ играет, обработать его сообщение как запрос
        if str(user_id) not in game_math_stats.keys():
            keyboard = {
                "one_time": False,
                "buttons": [
                    [get_text_button('!Все запросы', 'primary'), get_text_button('!Все команды', 'primary')]
                ]
            }
            keyboard = str(json.dumps(keyboard, ensure_ascii=False))

            if msg == "" or not is_command(msg):
                # Удаление лишних небуквенных символов
                msg = "".join(filter(is_correct_character, msg))
                if msg != "":
                    # Получение списка всех возможных ответов на данный запрос
                    answer = self.answers.get(msg.lower())
                    if answer is None:
                        answer = self.errors[0]
                    else:
                        # Случайный выбор ответа из полученного списка
                        answer = answer[random.randint(0, len(answer) - 1)]
                else:
                    answer = self.errors[0]

                # Если ответ - стикер (формат: ##ID, где ID - id стикера)
                if answer[0:2] == "##":
                    vk_session.method('messages.send',
                                      {'user_id': user_id, 'sticker_id': answer[2:], 'random_id': 0,
                                       'keyboard': keyboard})
                # Если ответ - не стикер
                else:
                    vk_session.method('messages.send',
                                      {'user_id': user_id, 'message': answer, 'random_id': 0, 'keyboard': keyboard})

                    # Выбор случайного стикера из диапазона id: 1..100, если включен ответ со случайными стикерами
                    if self.is_stickers_active:
                        flag = True
                        while flag:
                            rand = random.randint(1, 100)
                            try:
                                vk_session.method('messages.send',
                                                  {'user_id': user_id, 'random_id': 0, 'keyboard': keyboard,
                                                   'sticker_id': rand})
                                flag = False
                            except:
                                print('Недоступно: ' + str(rand))
                                flag = True
            # Если полученное сообщение - команда (формат: !команда, где команда - текст команды)
            else:
                message = self.readCommand(msg)
                if message is None:
                    return
                vk_session.method('messages.send',
                                  {'user_id': user_id, 'message': message, 'random_id': 0,
                                   'keyboard': keyboard})
        # Если пользователь играет - переадресовать сообщение методу GameMath.handler
        else:
            self.game_math_class.handler(user_id, msg)

    def readCommand(self, msg):
        cmd = msg.split('\n')[0].strip().lower()
        arg = msg.replace(cmd, '', 1).strip()
        if cmd in self.commands:
            return self.commands.get(cmd)[0](arg)
        else:
            return self.errors[1]

    def addResponse(self, arg):
        # Проверка на пустоту аргумента запроса и ответов
        if arg.count('\n') == 0:
            return self.errors[2]

        # Разделение аргумента по строкам. Первая строка - запрос; последующие - ответы
        split = arg.split('\n')

        # Извлечение запроса и удаление лишних небуквенных символов
        request = "".join(filter(is_correct_character, split[0].strip().lower()))

        # Проверка запроса на корректность
        if len(request) == 0:
            return self.errors[2]

        responses = list()
        string_added_responses = str()
        string_invalid_responses = str()

        # Проход по всем ответам и их запись в словарь ответов и строку для ответа пользователю
        for i in range(1, len(split)):
            if len(split[i].strip()) < 2 or \
                    (self.answers.get(request) is not None and split[i].strip() in self.answers.get(request)):
                string_invalid_responses += '\n\"' + split[i].strip() + '\"'
            else:
                responses.append(split[i].strip())
                string_added_responses += '\n\"' + split[i].strip() + '\"'

        # Получение уже имеющихся ответов по данному запросу и добавление новых ответов
        allResponses = self.answers.get(request)
        if allResponses is None:
            allResponses = list()
        allResponses.extend(responses)
        self.answers.update({request: allResponses})

        # Сохранение нового словаря в answers.json
        with open("answers.json", "w") as write_file:
            json.dump(self.answers, write_file)
            write_file.close()
        return "На запрос \"" + request.capitalize() + "\" добавлены ответы: " + string_added_responses + \
               "\n\n Проигнорированы ответы: " + string_invalid_responses

    def deleteResponse(self, arg):
        if arg.count('\n') == 0:
            return self.errors[2]

        split = arg.split('\n')
        request = split[0].strip().lower()
        if len(request) == 0:
            return self.errors[2]

        if request not in self.answers:
            return "Запрос \"" + request.capitalize() + "\" не найден в словаре ответов"

        allResponses = self.answers.get(request)
        stringResponses = str()
        for i in range(1, len(split)):
            if split[i].strip() not in allResponses:
                stringResponses += "Для запроса \"" + request + "\" не найден ответ \"" + split[i].strip() + "\"\n"
            else:
                allResponses.remove(split[i].strip())
                stringResponses += "Ответ \"" + split[i].strip() + "\" для запроса \"" + request + "\" успешно удален\n"

        if len(allResponses) == 0:
            self.answers.pop(request)
            stringResponses += "Запрос \"" + request.capitalize() + "\" удален из словаря ответов"
        else:
            self.answers.update({request: allResponses})

        with open("answers.json", "w") as write_file:
            json.dump(self.answers, write_file)
        return stringResponses

    def deleteAllResponses(self, arg):
        if arg.count('\n') != 0:
            return self.errors[2]

        request = arg.strip().lower()
        if len(request) == 0:
            return self.errors[2]

        if request not in self.answers:
            return "Запрос \"" + request.capitalize() + "\" не найден в словаре ответов"

        self.answers.pop(request)
        with open("answers.json", "w") as write_file:
            json.dump(self.answers, write_file)
        return "Запрос \"" + request.capitalize() + "\" удален из словаря ответов"

    def getAllRequests(self, arg=None):
        stringRequests = str()
        for request in self.answers.keys():
            stringRequests += request.capitalize() + '\n'

            # Показ всех ответов на запросы
            if arg == "admin":
                allResponses = self.answers.get(request)
                for response in allResponses:
                    if response[0:2] == "##":
                        response = "Стикер №" + response[2:]
                    stringRequests += "-" + response + "\n"
                stringRequests += "\n"

        return stringRequests

    def getAllCommands(self, arg=None):
        allCommands = str()
        number = 1
        for command in self.commands.items():
            allCommands += str(number) + ". " + command[0].capitalize() + command[1][1] + "\n\n"
            number += 1
        return allCommands

    def stickers(self, arg):
        if arg != '0' and arg != '1':
            return self.errors[2]
        self.is_stickers_active = int(arg)
        if int(arg):
            return "Стикеры включены"
        return "Стикеры выключены"

    def timer(self, arg, count=None, message=None):
        if not arg.isdigit():
            return self.errors[2]

        if count is None:
            count = 0
            message = vk_session.method('messages.send',
                                        {'user_id': self.user_id, 'message': '\\', 'random_id': 0})

        else:
            if count >= int(arg):
                vk_session.method('messages.send',
                                  {'peer_id': self.user_id, 'message_id': message,
                                   'message': 'Я подождал ' + str(int(arg)) + ' секунд!',
                                   'random_id': 0})
                vk_session.method('messages.delete',
                                  {'peer_id': self.user_id, 'message_ids': message,
                                   'delete_for_all': 1, 'random_id': 0})

                return
            if count % 4 == 0:
                vk_session.method('messages.edit',
                                  {'peer_id': self.user_id, 'message_id': message, 'message': '\\', 'random_id': 0})
            elif count % 4 == 1:
                vk_session.method('messages.edit',
                                  {'peer_id': self.user_id, 'message_id': message, 'message': '|', 'random_id': 0})
            elif count % 4 == 2:
                vk_session.method('messages.edit',
                                  {'peer_id': self.user_id, 'message_id': message, 'message': '/', 'random_id': 0})
            elif count % 4 == 3:
                vk_session.method('messages.edit',
                                  {'peer_id': self.user_id, 'message_id': message, 'message': '-', 'random_id': 0})
        count += 1
        threading.Timer(1, self.timer, args=[arg, count, message]).start()

    def game_math_start(self, arg=None):
        self.game_math_class.start(self.user_id)
