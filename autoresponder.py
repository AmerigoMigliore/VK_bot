from all_games import *
from data import answers


class Autoresponder:
    """ Класс ответов на сообщения пользователей """
    commands = {}
    errors = {}

    def __init__(self):
        self.commands = {'!добавить': [self.addResponse, "Запрос\nОтвет\nОтвет\n..."],
                         '!удалить ответы': [self.deleteResponse, "Запрос\nОтвет\nОтвет\n..."],
                         '!удалить запрос': [self.deleteAllResponses, "Запрос"],
                         '!все запросы': [self.getAllRequests, ""],
                         '!все ответы': [self.getAllResponses, "Запрос"],
                         '!все команды': [self.getAllCommands, ""],
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
        """ Обработка сообщений от пользователя двух типов:
        1. Сообщение-запрос.
            - Формат сообщения: любой текст, не начинающийся с символа '!'.
            - Действия при получении сообщения: нет.
            - Ответ на сообщение: выбирается случайный ответ из словаря всех ответов, сформированного для каждого
            пользователя отдельно. При первом формировании словаря, в него записывается стандартный набор ответов,
            созданный администраторами бота.

        2. Сообщение-команда.
            - Формат сообщения: символ '!', тело команды, символ '/n', аргументы команды, разделенные символами '/n'.
            - Действия при получении сообщения: передать сообщение в метод read_command.
            - Ответ на сообщение: нет или пришедшая после обработки сообщения в read_command строка.

        :param event: событие, пришедшее в VkBotLongPoll
        :type event: :class:`Event`
        """
        user_id = str(event.obj.from_id)
        msg = event.obj.text

        keyboard = {
            "one_time": False,
            "buttons": [
                [get_text_button('!Все запросы', 'primary'), get_text_button('!Все команды', 'primary')]
            ]
        }
        keyboard = str(json.dumps(keyboard, ensure_ascii=False))

        # Проверка пользователя на наличие его ID в словаре.
        # Если пользователя нет, добавить его и дать базовый набор запросов и ответов
        # TODO: Сделать проверку при регистрации пользователя и только
        if user_id not in answers.keys():
            answers[user_id] = {}

        if msg == "" or not self.is_command(msg):
            msg = msg.lower()

            # Удаление лишних небуквенных символов
            msg = "".join(filter(self.is_correct_character, msg))

            if msg != "":
                # Получение списка всех возможных ответов на данный запрос
                answer = answers.get("global").get(msg, []) + answers.get(user_id).get(msg, [])
                if len(answer) == 0:
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

        # Если полученное сообщение - команда (формат: !команда, где команда - текст команды)
        else:
            message = self.readCommand(msg, user_id)

            # Формирование ответа, пришедшего после выполнения команды
            if message is None:
                return
            else:
                vk_session.method('messages.send',
                                  {'user_id': int(user_id), 'message': message, 'random_id': 0,
                                   'keyboard': keyboard})

    def readCommand(self, msg, user_id):
        """ Обработка команд по шаблону:
            - Первая строка: !команда.
            - Последующие строки: аргумент(-ы) команды.

        Примечания:
            - Строки разделяются символом '\n'.
            - Некоторые команды допускают несколько аргументов, разделенные символом '\n'.

        Функции, обрабатывающие команду, должны принимать 2 аргумента:
            - arg:     аргументы команды.
            - user_id: ID пользователя, вызвавшего команду.

            - При возникновении ошибки при чтении команды следует вернуть сообщение об ошибке в виде строки,
            которая будет отправлена пользователю.

        :param msg: сообщение с командой и аргументами по шаблону.
        :type msg: str.

        :param user_id: ID пользователя, вызвавшего команду.
        :type user_id: int или str.
        """
        cmd = msg.split('\n')[0].strip().lower()
        arg = msg.replace(cmd, '', 1).strip()
        if cmd in self.commands:
            return self.commands.get(cmd)[0](arg, user_id)
        else:
            return self.errors[1]

    def addResponse(self, arg, user_id):
        """ Добавление нового запроса или новых ответов к уже существующему запросу для данного пользователя.

        :param arg: сообщение от пользователя по шаблону:
            - Первая строка: запрос.
            - Последующие строки: ответ.

            Примечания:
                - Строки разделяются символом '\n'.
                - На запрос можно добавить 1 и более ответов, разделенных между собой символом '\n'.
        :type arg: str.

        :param user_id: ID пользователя, вызвавшего команду.
        :type user_id: int или str.

        :return: сообщение об ошибке или сообщение об ответах, которые добавлены и недобавлены на данный запрос.
        """
        user_id = str(user_id)
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

        # Получение уже имеющихся ответов по данному запросу из словаря для данного пользователя
        all_responses = answers.get(user_id).get(request, [])

        return_added_responses = str()
        return_invalid_responses = str()

        # Проход по всем ответам и их запись в список ответов на данный запрос и строку для ответа пользователю
        for response in split[1:]:
            response.split()
            if response in answers.get(user_id).get(request, []) or \
                    (response[0:2] == "##" and not response[2:].isalpha()):
                return_invalid_responses += "\n\"{}\"".format(response)
            else:
                all_responses.append(response)
                return_added_responses += "\n\"{}\"".format(response)

        # Обновление списка ответов на данный запрос для данного пользователя
        answers[user_id][request] = all_responses

        # Возврат сообщения о завершении добавления ответов
        return "На запрос \"{}\" добавлены ответы: {}\n\n Проигнорированы ответы: {}"\
            .format(request.capitalize(), return_added_responses, return_invalid_responses)

    def deleteResponse(self, arg, user_id):
        """ Выборочное удаление ответов на запрос для данного пользователя.

        :param arg: сообщение от пользователя по шаблону:
            - Первая строка: запрос.
            - Последующие строки: ответ.

            Примечания:
                - Строки разделяются символом '\n'.
                - У запроса можно удалить 1 и более ответов, разделенных между собой символом '\n'.
        :type arg: str.

        :param user_id: ID пользователя, вызвавшего команду.
        :type user_id: int или str.

        :return: сообщение об ошибке или сообщение об ответах, которые удалены и неудалены для данного запроса.
        """
        user_id = str(user_id)

        # Проверка аргумента на пустоту
        if arg.count('\n') == 0:
            return self.errors[2]

        # Разделение аргумента по строкам. Первая строка - запрос; последующие - ответы
        split = arg.split('\n')

        # Извлечение запроса и удаление лишних небуквенных символов
        request = "".join(filter(self.is_correct_character, split[0].strip().lower()))

        # Проверка запроса на корректность
        if len(request) == 0:
            return self.errors[2]

        # Проверка запроса на существование в словаре ответов для данного пользователя
        if request not in answers.get(user_id):
            return "Запрос \"{}\" не найден в Вашем словаре ответов".format(request.capitalize())

        # Получение уже имеющихся ответов по данному запросу из словаря для данного пользователя
        all_responses = answers.get(user_id).get(request, [])
        return_deleted_responses = str()
        return_invalid_responses = str()
        is_deleted_all = False

        for response in split[1:]:
            response.strip()
            if response not in all_responses:
                return_invalid_responses += "\n\"{}\"".format(response)
            else:
                all_responses.remove(response)
                return_deleted_responses += "\n\"{}\"".format(response)

        # Проверка запроса на наличие ответов и удаление необходимых ответов из словаря для данного пользователя
        if len(all_responses) == 0:
            answers.get(user_id).pop(request)
            is_deleted_all = True
        else:
            answers[user_id][request] = all_responses

        # Возврат сообщения о завершении удаления ответов
        if is_deleted_all:
            return "Запрос \"{}\" полностью удален из Вашего словаря ответов".format(request.capitalize())
        else:
            return "На запрос \"{}\" удалены ответы: {}\n\n Проигнорированы ответы: {}"\
                .format(request.capitalize(), return_deleted_responses, return_invalid_responses)

    def deleteAllResponses(self, arg, user_id):
        """ Удаление всего запроса для данного пользователя.

        :param arg: сообщение от пользователя по шаблону:
            - Первая строка: запрос.
        :type arg: str.

        :param user_id: ID пользователя, вызвавшего команду.
        :type user_id: int или str.

        :return: сообщение об ошибке или сообщение об удалении данного запроса.
        """
        user_id = str(user_id)

        # Извлечение запроса и удаление лишних небуквенных символов
        request = "".join(filter(self.is_correct_character, arg.strip().lower()))

        # Проверка запроса на корректность
        if len(request) == 0:
            return self.errors[2]

        # Проверка запроса на существование в словаре ответов для данного пользователя
        if request not in answers.get(user_id):
            return "Запрос \"{}\" не найден в Вашем словаре ответов".format(request.capitalize())

        # Удаление всего запроса из словаря ответов для данного пользователя
        answers.get(user_id).pop(request)

        # Возврат сообщения о завершении удаления ответов
        return "Запрос \"{}\" полностью удален из Вашего словаря ответов".format(request.capitalize())

    @staticmethod
    def getAllRequests(arg, user_id):
        """ Предоставление списка всех доступных запросов.

        :param arg: None.
        :type arg: None.

        :param user_id: ID пользователя, вызвавшего команду.
        :type user_id: int или str.

        :return: сообщение со списком всех доступных запросов.
        """
        string_requests = str()

        # Получение всех глобальных запросов и их запись в сообщение для ответа
        string_requests += "Глобальные запросы:\n"
        for request in answers.get("global").keys():
            string_requests += "\n{}".format(request.capitalize())

        # Получение всех локальных запросов и их запись в сообщение для ответа
        string_requests += "\n\nВаши запросы:\n"
        for request in answers.get(user_id).keys():
            string_requests += "\n{}".format(request.capitalize())

        # Возврат сообщения со списком всех доступных запросов
        return string_requests

    def getAllResponses(self, arg, user_id):
        """ Предоставление списка всех доступных ответов на данный запрос для данного пользователя.

        :param arg: запрос.
        :type arg: str.

        :param user_id: ID пользователя, вызвавшего команду.
        :type user_id: int или str.

        :return: сообщение со списком всех доступных ответов на данный запрос.
        """
        string_responses = str()

        # Извлечение запроса и удаление лишних небуквенных символов
        request = "".join(filter(self.is_correct_character, arg.strip().lower()))

        # Проверка запроса на корректность
        if len(request) == 0:
            return self.errors[2]

        # Проверка запроса на существование в словаре ответов для данного пользователя
        if request not in answers.get(user_id):
            return "Запрос \"{}\" не найден в Вашем словаре ответов".format(request.capitalize())

        # Получение всех ответов на данный запрос для данного пользователя и их запись в сообщение для ответа
        all_responses = answers.get(user_id).get(request)
        for response in all_responses:
            if response[0:2] == "##":
                response = "Стикер №{}".format(response[2:])
            string_responses += "\n{}".format(response)

        # Возврат сообщения со списком всех доступных запросов
        return "Ответы на запрос \"{}\":\n{}".format(request.capitalize(), string_responses)

    def getAllCommands(self, arg=None, user_id=None):
        """ Предоставление списка всех доступных команд бота.

        :param arg: None.
        :type arg: None.

        :param user_id: None.
        :type user_id: None.

        :return: сообщение со списком всех доступных команд бота.
        """
        string_commands = str()
        number = 1

        # Получение всех команд и их запись в сообщение для ответа
        for command in self.commands.items():
            string_commands += "\n{}. {}\n{}\n\n".format(number, command[0].capitalize(), command[1][1])
            number += 1

        return "Команды:\n{}".format(string_commands)

    @staticmethod
    def get_top_math(arg, user_id):
        """ Предоставление списка рейтинга игры "Математика".

        :param arg: None.
        :type arg: None.

        :param user_id: ID пользователя, вызвавшего команду.
        :type user_id: int или str.
        """
        game_math_class.get_top(user_id)

    @staticmethod
    def game_math_start(arg, user_id):
        """ Начало игры "Математика".

        :param arg: None.
        :type arg: None.

        :param user_id: ID пользователя, вызвавшего команду.
        :type user_id: int или str.
        """
        where_are_users.update({user_id: "game_math"})
        game_math_class.start(str(user_id))

    @staticmethod
    def is_command(msg):
        return msg[0] == '!'

    @staticmethod
    def is_correct_character(character):
        return str.isalpha(character) or character == ' '
