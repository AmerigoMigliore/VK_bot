from all_games import *


class Autoresponder:
    """Класс ответов на сообщения пользователей"""
    answers = {}
    commands = {}
    errors = {}

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
                         '!математика': [self.game_math_start, ""],
                         '!рейтинг математики': [self.get_top_math, ""]
                         }
        self.errors = [  # TODO: Поменять на что-то нормальное
            # 0
            'Я пока что не знаю этой фразы ;o\nВы можете обучить меня, введя команду !добавить'
            '\nУзнать все доступные запросы: !все запросы',
            # 1
            'Неизвестная команда.\nУзнать список доступных команд и их синтаксис: !все команды',
            # 2
            'Неверные аргументы.\nУзнать список доступных команд и их синтаксис: !все команды',
            # 3
            'Длина ответа не может быть меньше 2',
            # 4
            'Рейтинг доступен только при наличии активной игровой сессии.'
            'Используйте команду \"!играть\" для запуска игровой сессии']

    def process_event(self, event):
        user_id = str(event.obj.from_id)
        msg = event.obj.text

        keyboard = {
            "one_time": False,
            "buttons": [
                [get_text_button('!Все запросы', 'primary'), get_text_button('!Все команды', 'primary')]
            ]
        }
        keyboard = str(json.dumps(keyboard, ensure_ascii=False))

        if msg == "" or not self.is_command(msg):

            # Удаление лишних небуквенных символов
            msg = "".join(filter(self.is_correct_character, msg))

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
                                  {'user_id': int(user_id), 'sticker_id': answer[2:], 'random_id': 0,
                                   'keyboard': keyboard})

            # Если ответ - не стикер
            else:
                vk_session.method('messages.send',
                                  {'user_id': int(user_id), 'message': answer, 'random_id': 0, 'keyboard': keyboard})

                # Выбор случайного стикера из диапазона id: 1..100, если включен ответ со случайными стикерами
                if self.is_stickers_active:
                    flag = True
                    while flag:
                        rand = random.randint(1, 100)
                        try:
                            vk_session.method('messages.send',
                                              {'user_id': int(user_id), 'random_id': 0, 'keyboard': keyboard,
                                               'sticker_id': rand})
                            flag = False
                        except:
                            print('Недоступно: ' + str(rand))
                            flag = True

        # Если полученное сообщение - команда (формат: !команда, где команда - текст команды)
        else:
            message = self.readCommand(msg, user_id)
            if message is None:
                return
            else:
                vk_session.method('messages.send',
                                  {'user_id': int(user_id), 'message': message, 'random_id': 0,
                                   'keyboard': keyboard})

    def readCommand(self, msg, user_id):
        cmd = msg.split('\n')[0].strip().lower()
        arg = msg.replace(cmd, '', 1).strip()
        if cmd in self.commands:
            return self.commands.get(cmd)[0](arg, user_id)
        else:
            return self.errors[1]

    def addResponse(self, arg, user_id=None):
        # Проверка на пустоту аргумента запроса и ответов
        if arg.count('\n') == 0:
            return self.errors[2]

        # Разделение аргумента по строкам. Первая строка - запрос; последующие - ответы
        split = arg.split('\n')

        # Извлечение запроса и удаление лишних небуквенных символов
        request = "".join(filter(self.is_correct_character, split[0].strip().lower()))

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

    def deleteResponse(self, arg, user_id=None):
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

    def deleteAllResponses(self, arg, user_id=None):
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

    def getAllRequests(self, arg=None, user_id=None):
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

    def getAllCommands(self, arg=None, user_id=None):
        allCommands = str()
        number = 1
        for command in self.commands.items():
            allCommands += str(number) + ". " + command[0].capitalize() + command[1][1] + "\n\n"
            number += 1
        return allCommands

    def stickers(self, arg, user_id=None):
        if arg != '0' and arg != '1':
            return self.errors[2]
        self.is_stickers_active = int(arg)
        if int(arg):
            return "Стикеры включены"
        return "Стикеры выключены"

    @staticmethod
    def get_top_math(arg=None, user_id=None):
        game_math_class.get_top(user_id)

    @staticmethod
    def game_math_start(arg=None, user_id=None):
        where_are_users.update({user_id: "game_math"})
        game_math_class.start(str(user_id))

    @staticmethod
    def is_command(msg):
        return msg[0] == '!'

    @staticmethod
    def is_correct_character(character):
        return str.isalpha(character) or character == ' '
