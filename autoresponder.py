import sqlite3

import numpy as np
import re

import data
from all_games import game_math_class, game_luck_class
from data import answers, users_info, roles, change_users_info, main_keyboard
from pyxdameraulevenshtein import normalized_damerau_levenshtein_distance_seqs
from transliterate import translit
from unicodedata import normalize, category
from keyboard import *
import json
from vk_auth import VkBotEventType, vk_session, VkEventType, my_vk_session, my_longpoll
import random


class Autoresponder:
    """ Класс ответов на сообщения пользователей """
    commands = {}
    methods = {}
    errors = {}

    def __init__(self):
        self.commands = {'!добавить': [self.add_response, 'Запрос\nОтвет\nОтвет\n...'],
                         '!удалить ответы': [self.delete_response, 'Запрос\nОтвет\nОтвет\n...'],
                         '!удалить запрос': [self.delete_all_responses, 'Запрос'],
                         '!все запросы': [self.get_all_requests, ''],
                         '!все ответы': [self.get_all_responses, 'Запрос'],
                         '!все команды': [self.get_all_commands, ''],
                         '!рандом': [self.choose_random, ''],
                         '!играть': [self.game_start, ''],
                         '!баланс': [self.get_balance, ''],
                         '!!добавить': [self.add_global_response, 'Запрос\nОтвет\nОтвет\n...'],
                         '!!удалить ответы': [self.delete_global_response, 'Запрос\nОтвет\nОтвет\n...'],
                         '!!удалить запрос': [self.delete_all_global_responses, 'Запрос'],
                         '!!добавить синонимы': [self.add_synonyms, 'Запрос\nСиноним\nСиноним\n...'],
                         '!!удалить синонимы': [self.delete_synonyms, 'Синоним\nСиноним\n...'],
                         '!!синонимы': [self.get_synonyms, 'Запрос'],
                         '!!!изменить роль': [self.set_role, 'ID\nРоль'],
                         '!!!выдать монеты': [self.give_money, 'ID\nКоличество'],
                         # '!!!!перезагрузка': [self.reboot, ''],
                         '!!!!сбросить положение': [self.reset_position, 'ID'],
                         '!!!!статистика синонимов': [self.get_synonyms_stats, '']
                         }
        self.methods = {'': self.choose_random}
        self.errors = [  # TODO: Поменять на что-то нормальное
            # 0
            'Я пока что не знаю этой фразы ;o\nВы можете обучить меня, введя команду !добавить'
            '\nУзнать все доступные запросы: !все запросы',
            # 1
            'Неизвестная команда.\nУзнать список доступных команд и их синтаксис: !все команды',
            # 2
            'Неверные аргументы.\nУзнать список доступных команд и их синтаксис: !все команды', ]

    def process_event(self, event):
        """ Обработка сообщений от пользователя двух типов:
        1. Сообщение-запрос.
            - Формат сообщения: любой текст, не начинающийся с символа '!'.
            - Действия при получении сообщения: нет.
            - Ответ на сообщение: выбирается случайный ответ из словаря всех ответов, сформированного для каждого
            пользователя отдельно. При первом формировании словаря, в него записывается стандартный набор ответов,
            созданный администраторами бота.

        2. Сообщение-команда.
            - Формат сообщения: символ(-ы) '!', тело команды, символ '/n', аргументы команды, разделенные символами '/n'.
            - Действия при получении сообщения: передать сообщение в метод read_command.
            - Ответ на сообщение: нет или пришедшая после обработки сообщения в read_command строка.

        :param event: событие, пришедшее в VkBotLongPoll
        :type event: :class:`Event`
        """
        if event is None:
            return

        if event.type == VkBotEventType.MESSAGE_EVENT:
            user_id = str(event.obj.user_id)
            args = event.obj.payload.get('args')

            method = users_info.get(user_id, {}).get('method')
            if method == 'choose_random':
                self.choose_random(args, user_id)
            elif method == 'game_start':
                self.game_start(args, user_id)

            # Сброс активированной кнопки, вызвавшей событие
            vk_session.method('messages.sendMessageEventAnswer',
                              {'event_id': event.obj.event_id,
                               'user_id': int(user_id),
                               'peer_id': event.obj.peer_id})

        elif event.type == VkBotEventType.MESSAGE_NEW:
            user_id = str(event.obj.from_id)
            message = event.obj.text

            # Проверка пользователя на наличие его ID в словаре.
            # Если пользователя нет, добавить его и дать базовый набор запросов и ответов
            if user_id not in answers.keys():
                answers[user_id] = {}

            # Получаем метод, с которым работает пользователь, и если он не пуст, перенаправляем сообщение в данный метод
            method = users_info.get(user_id, {}).get('method')
            if method is not None:
                args = users_info.get(user_id, {}).get('args')

                if method == "choose_random":
                    self.choose_random(args, user_id, message)
                if method == "game_start":
                    self.choose_random(args, user_id, message)

                return

            else:
                # Если сообщение - не команда
                if not self.is_command(message):
                    db_cursor = sqlite3.connect('all_data.db').cursor()

                    # Удаление лишних и изменение специальных символов и повторов букв в словах
                    message = re.sub(r'([\D])(\1)+', r'\1',
                                     re.sub(r'\W+', ' ',
                                            ''.join(c for c in normalize('NFD', message) if category(c) != 'Mn')
                                            ).lower().strip(),
                                     flags=re.I)

                    # Получение всех доступных синонимов
                    db_cursor.execute(f'SELECT word FROM synonyms_global')
                    all_synonyms = db_cursor.fetchall()
                    all_synonyms = [x[0] for x in all_synonyms] if len(all_synonyms) > 0 else list(
                        answers.get('global').keys())

                    # Получение слова-синонима с исправленными опечатками для данного запроса (если есть)
                    db_cursor.execute(
                        f'SELECT request FROM synonyms_global WHERE word="{self.fix_command(message, all_synonyms)}";')
                    request = db_cursor.fetchone()

                    # Получение списка всех возможных ответов на данный запрос
                    answer = answers.get("global").get(request[0] if request is not None else None, []) + \
                        answers.get(user_id).get(message, [])

                    # Если найдено совпадение
                    if len(answer) != 0:
                        # Случайный выбор ответа из полученного списка
                        answer = answer[random.randint(0, len(answer) - 1)]

                    # Если совпадений не найдено
                    else:
                        # Интеграция с Марусей (id=194070336)
                        my_vk_session.method('messages.send',
                                             {'peer_id': -194070336, 'message': message, 'random_id': 0})

                        for event in my_longpoll.listen():
                            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.peer_id == -194070336:
                                # Получение сообщения
                                answer = event.message
                                # Добавление запроса и ответа в список ответов на данный запрос для данного пользователя
                                answers[user_id][message] = [answer]
                                break

                    # Если ответ - стикер (формат: ##ID, где ID - id стикера)
                    if answer[0:2] == "##":
                        vk_session.method('messages.send',
                                          {'user_id': int(user_id), 'sticker_id': answer[2:], 'random_id': 0,
                                           'keyboard': main_keyboard})

                    # Если ответ - не стикер
                    else:
                        vk_session.method('messages.send',
                                          {'user_id': int(user_id), 'message': answer, 'random_id': 0,
                                           'keyboard': main_keyboard})

                # Если полученное сообщение - команда (формат: !команда, где команда - текст команды)
                else:
                    command_message = self.read_command(message, user_id)

                    # Формирование ответа, пришедшего после выполнения команды
                    if command_message is not None:
                        vk_session.method('messages.send',
                                          {'user_id': int(user_id), 'message': command_message, 'random_id': 0,
                                           'keyboard': main_keyboard})

    def read_command(self, msg, user_id):
        """ Обработка команд по шаблону:
            - Первая строка: команда.
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

    def add_response(self, arg, user_id):
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
        request = re.sub(r'([\D])(\1)+', r'\1',
                         re.sub(r'\W+', ' ',
                                ''.join(c for c in normalize('NFD', split[0]) if category(c) != 'Mn')
                                ).lower().strip(),
                         flags=re.I)

        # Проверка запроса на корректность
        if len(request) == 0:
            return self.errors[2]

        # Получение уже имеющихся ответов по данному запросу из словаря для данного пользователя
        all_responses = answers.get(user_id).get(request, [])

        return_added_responses = str()
        return_invalid_responses = str()

        # Проход по всем ответам и их запись в список ответов на данный запрос и строку для ответа пользователю
        for response in split[1:]:
            response = response.strip()
            if response in all_responses or \
                    (response[0:2] == "##" and not response[2:].isalpha()):
                return_invalid_responses += f"\n\"{response}\""
            else:
                all_responses.append(response)
                return_added_responses += f"\n\"{response}\""

        # Обновление списка ответов на данный запрос для данного пользователя
        answers[user_id][request] = all_responses

        # Возврат сообщения о завершении добавления ответов
        return f'На запрос "{request.capitalize()}" добавлены ответы:' \
               f'{return_added_responses}\n\n' \
               f'Проигнорированы ответы: {return_invalid_responses}'

    def delete_response(self, arg, user_id):
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
        request = re.sub(r'([\D])(\1)+', r'\1',
                         re.sub(r'\W+', ' ',
                                ''.join(c for c in normalize('NFD', split[0]) if category(c) != 'Mn')
                                ).lower().strip(),
                         flags=re.I)

        # Проверка запроса на корректность
        if len(request) == 0:
            return self.errors[2]

        # Проверка запроса на существование в словаре ответов для данного пользователя
        if request not in answers.get(user_id, {}):
            return f'Запрос "{request.capitalize()}" не найден в Вашем словаре ответов'

        # Получение уже имеющихся ответов по данному запросу из словаря для данного пользователя
        all_responses = answers.get(user_id).get(request, [])
        return_deleted_responses = str()
        return_invalid_responses = str()
        is_deleted_all = False

        for response in split[1:]:
            response.strip()
            if response not in all_responses:
                return_invalid_responses += f'\n"{response}"'
            else:
                all_responses.remove(response)
                return_deleted_responses += f'\n"{response}"'

        # Проверка запроса на наличие ответов и удаление необходимых ответов из словаря для данного пользователя
        if len(all_responses) == 0:
            answers.get(user_id).pop(request)
            is_deleted_all = True
        else:
            answers[user_id][request] = all_responses

        # Возврат сообщения о завершении удаления ответов
        if is_deleted_all:
            return f'Запрос "{request.capitalize()}" полностью удален из Вашего словаря ответов'
        else:
            return f'На запрос "{request.capitalize()}" удалены ответы: ' \
                   f'{return_deleted_responses}\n\n' \
                   f'Проигнорированы ответы: {return_invalid_responses}'

    def delete_all_responses(self, arg, user_id):
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
        request = re.sub(r'([\D])(\1)+', r'\1',
                         re.sub(r'\W+', ' ',
                                ''.join(c for c in normalize('NFD', arg) if category(c) != 'Mn')
                                ).lower().strip(),
                         flags=re.I)

        # Проверка запроса на корректность
        if len(request) == 0:
            return self.errors[2]

        # Проверка запроса на существование в словаре ответов для данного пользователя
        if request not in answers.get(user_id):
            return f'Запрос "{request.capitalize()}" не найден в Вашем словаре ответов'

        # Удаление всего запроса из словаря ответов для данного пользователя
        answers.get(user_id).pop(request)

        # Возврат сообщения о завершении удаления ответов
        return f'Запрос "{request.capitalize()}" полностью удален из Вашего словаря ответов'

    def add_global_response(self, arg, user_id):
        """ Добавление нового запроса или новых ответов к уже существующему запросу для всех пользователей.
        Уровень доступа: модератор.

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
        if roles[users_info.get(user_id).get('role')] < roles['moderator']:
            return "Недостаточный уровень доступа"
        else:
            # Проверка на пустоту аргумента запроса и ответов
            if arg.count('\n') == 0:
                return self.errors[2]

            # Разделение аргумента по строкам. Первая строка - запрос; последующие - ответы
            split = arg.split('\n')

            # Извлечение запроса и удаление лишних небуквенных символов
            request = re.sub(r'([\D])(\1)+', r'\1',
                             re.sub(r'\W+', ' ',
                                    ''.join(c for c in normalize('NFD', split[0]) if category(c) != 'Mn')
                                    ).lower().strip(),
                             flags=re.I)

            # Проверка запроса на корректность
            if len(request) == 0:
                return self.errors[2]

            # Получение уже имеющихся ответов по данному запросу из словаря для всех пользователей
            all_responses = answers.get('global', {}).get(request, [])

            return_added_responses = str()
            return_invalid_responses = str()

            # Проход по всем ответам и их запись в список ответов на данный запрос и строку для ответа модератору
            for response in split[1:]:
                response = response.strip()
                if response in all_responses or \
                        (response[0:2] == "##" and not response[2:].isalpha()):
                    return_invalid_responses += f"\n\"{response}\""
                else:
                    all_responses.append(response)
                    return_added_responses += f"\n\"{response}\""

            # Обновление списка ответов на данный запрос для всех пользователей
            answers['global'][request] = all_responses

            # Возврат сообщения о завершении добавления ответов
            return f'На глобальный запрос "{request.capitalize()}" добавлены ответы:' \
                   f'{return_added_responses}\n\n' \
                   f'Проигнорированы ответы: {return_invalid_responses}'

    def delete_global_response(self, arg, user_id):
        """ Выборочное удаление ответов на запрос для всех пользователей.
        Уровень доступа: модератор.

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
        if roles[users_info.get(user_id).get('role')] < roles['moderator']:
            return "Недостаточный уровень доступа"
        else:
            # Проверка аргумента на пустоту
            if arg.count('\n') == 0:
                return self.errors[2]

            # Разделение аргумента по строкам. Первая строка - запрос; последующие - ответы
            split = arg.split('\n')

            # Извлечение запроса и удаление лишних небуквенных символов
            request = re.sub(r'([\D])(\1)+', r'\1',
                             re.sub(r'\W+', ' ',
                                    ''.join(c for c in normalize('NFD', split[0]) if category(c) != 'Mn')
                                    ).lower().strip(),
                             flags=re.I)

            # Проверка запроса на корректность
            if len(request) == 0:
                return self.errors[2]

            # Проверка запроса на существование в словаре ответов для всех пользователей
            if request not in answers.get('global', {}):
                return f'Запрос "{request.capitalize()}" не найден в глобальном словаре ответов'

            # Получение уже имеющихся ответов по данному запросу из словаря для всех пользователей
            all_responses = answers.get('global').get(request, [])
            return_deleted_responses = str()
            return_invalid_responses = str()
            is_deleted_all = False

            for response in split[1:]:
                response = response.strip()
                if response not in all_responses:
                    return_invalid_responses += f'\n"{response}"'
                else:
                    all_responses.remove(response)
                    return_deleted_responses += f'\n"{response}"'

            # Проверка запроса на наличие ответов и удаление необходимых ответов из словаря для всех пользователей
            if len(all_responses) == 0:
                answers.get('global').pop(request)
                is_deleted_all = True
            else:
                answers['global'][request] = all_responses

            # Возврат сообщения о завершении удаления ответов
            if is_deleted_all:
                return f'Запрос "{request.capitalize()}" полностью удален из глобального словаря ответов'
            else:
                return f'На глобальный запрос "{request.capitalize()}" удалены ответы: ' \
                       f'{return_deleted_responses}\n\n' \
                       f'Проигнорированы ответы: {return_invalid_responses}'

    def delete_all_global_responses(self, arg, user_id):
        """ Удаление всего запроса для всех пользователей.
        Уровень доступа: модератор.

        :param arg: сообщение от пользователя по шаблону:
            - Первая строка: запрос.
        :type arg: str.

        :param user_id: ID пользователя, вызвавшего команду.
        :type user_id: int или str.

        :return: сообщение об ошибке или сообщение об удалении данного запроса.
        """
        user_id = str(user_id)
        if roles[users_info.get(user_id).get('role')] < roles['moderator']:
            return "Недостаточный уровень доступа"
        else:
            # Извлечение запроса и удаление лишних небуквенных символов
            request = re.sub(r'([\D])(\1)+', r'\1',
                             re.sub(r'\W+', ' ',
                                    ''.join(c for c in normalize('NFD', arg) if category(c) != 'Mn')
                                    ).lower().strip(),
                             flags=re.I)

            # Проверка запроса на корректность
            if len(request) == 0:
                return self.errors[2]

            # Проверка запроса на существование в словаре ответов для всех пользователей
            if request not in answers.get('global'):
                return f'Запрос "{request.capitalize()}" не найден в глобальном словаре ответов'

            # Удаление всего запроса из словаря ответов для всех пользователей
            answers.get('global').pop(request)

            # Возврат сообщения о завершении удаления ответов
            return f'Запрос "{request.capitalize()}" полностью удален из глобального словаря ответов'

    def add_synonyms(self, arg, user_id):
        user_id = str(user_id)
        if roles[users_info.get(user_id).get('role')] < roles['moderator']:
            return "Недостаточный уровень доступа"
        else:
            split = arg.split('\n')
            request = split[0].lower().strip()
            if request not in answers.get('global').keys():
                return f'Запрос "{request}" не найден в словаре ответов.'
            if len(split) < 2:
                return self.errors[2]
            else:
                db_connect = sqlite3.connect('all_data.db')
                db_cursor = db_connect.cursor()
                db_cursor.executemany('INSERT OR IGNORE INTO synonyms_global VALUES(?, ?);',
                                      ((word.lower().strip(), request) for word in split[1:]))
                db_connect.commit()
                n = '\n'
                return f'К запросу "{request}" добавлены синонимы:\n' \
                       f'{n.join([word.capitalize().strip() for word in split[1:]])}'

    def get_synonyms(self, arg, user_id):
        user_id = str(user_id)
        if roles[users_info.get(user_id).get('role')] < roles['moderator']:
            return "Недостаточный уровень доступа"
        else:
            split = arg.split('\n')
            if len(split) != 1:
                return self.errors[2]
            else:
                db_connect = sqlite3.connect('all_data.db')
                db_cursor = db_connect.cursor()
                db_cursor.execute(f'SELECT word FROM synonyms_global WHERE request="{split[0].lower().strip()}"')
                synonyms = db_cursor.fetchall()
                if len(synonyms) == 0:
                    return f'Запрос "{split[0].capitalize()}" не имеет синонимов'
                else:
                    n = '\n'
                    return f'Запрос "{split[0].capitalize()}" имеет синонимы:\n' \
                           f'{n.join((word[0].capitalize() for word in synonyms))}'

    def delete_synonyms(self, arg, user_id):
        user_id = str(user_id)
        if roles[users_info.get(user_id).get('role')] < roles['moderator']:
            return "Недостаточный уровень доступа"
        else:
            split = arg.split('\n')
            request = split[0].lower().strip()
            if len(split) < 2:
                return self.errors[2]
            else:
                db_connect = sqlite3.connect('all_data.db')
                db_cursor = db_connect.cursor()
                db_cursor.execute(f'SELECT word FROM synonyms_global WHERE request="{request}"')
                synonyms = db_cursor.fetchall()
                if len(synonyms) == 0:
                    return f'Запрос "{request.capitalize()}" не имеет синонимов для удаления'
                else:
                    synonyms = [word[0].lower() for word in synonyms]
                    return_deleted_synonyms = str()
                    return_invalid_synonyms = str()
                    for word in split[1:]:
                        if word.lower().strip() in synonyms and word.lower().strip() != request:
                            db_cursor.execute(f'DELETE FROM synonyms_global WHERE word="{word.lower().strip()}";')
                            return_deleted_synonyms += f"\n\"{word.capitalize()}\""
                        else:
                            return_invalid_synonyms += f"\n\"{word.capitalize()}\""
                    db_connect.commit()

                    return f'У запроса "{request}" ' \
                           f'удалены синонимы:\n{return_deleted_synonyms}\n\n' \
                           f'Проигнорированы синонимы:\n{return_invalid_synonyms}'

    @staticmethod
    def get_synonyms_stats(arg, user_id):
        user_id = str(user_id)
        if roles[users_info.get(user_id).get('role')] < roles['master']:
            return "Недостаточный уровень доступа"
        else:
            db_cursor = sqlite3.connect('all_data.db').cursor()

            db_cursor.execute('SELECT phrase, request, type, rate FROM synonyms_stats')
            all_synonyms = db_cursor.fetchall()
            # db_cursor.execute('DELETE FROM synonyms_stats')
            all_synonyms = [f'USER\'S PHRASE: {x[0]}, BEST REQUEST: {x[1]}, TYPE OF FIX: {x[2]}, RATE: {x[3]}\n\n'
                            for x in all_synonyms] if len(all_synonyms) > 0 else 'NOT FOUND'
            return_string = str()
            for s in all_synonyms:
                return_string += s
            for s in data.synonyms_stats:
                return_string += f'USER\'S PHRASE: {s[0]}, BEST REQUEST: {s[1]}, TYPE OF FIX: {s[2]}, RATE: {s[3]}\n\n'
            return return_string

    @staticmethod
    def get_all_requests(arg, user_id):
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
            string_requests += f'\n{request.capitalize()}'

        # Получение всех локальных запросов и их запись в сообщение для ответа
        string_requests += "\n\nВаши запросы:\n"
        for request in answers.get(user_id).keys():
            string_requests += f'\n{request.capitalize()}'

        # Возврат сообщения со списком всех доступных запросов
        return string_requests

    def get_all_responses(self, arg, user_id):
        """ Предоставление списка всех доступных ответов на данный запрос для данного пользователя.

        :param arg: запрос.
        :type arg: str.

        :param user_id: ID пользователя, вызвавшего команду.
        :type user_id: int или str.

        :return: сообщение со списком всех доступных ответов на данный запрос.
        """
        string_responses = str()

        # Извлечение запроса и удаление лишних небуквенных символов
        request = re.sub(r'([\D])(\1)+', r'\1',
                         re.sub(r'\W+', ' ',
                                ''.join(c for c in normalize('NFD', arg) if category(c) != 'Mn')
                                ).lower().strip(),
                         flags=re.I)

        # Проверка запроса на корректность
        if len(request) == 0:
            return self.errors[2]

        # Проверка запроса на существование в словаре ответов для данного пользователя
        if request not in answers.get(user_id):
            return f'Запрос "{request.capitalize()}" не найден в Вашем словаре ответов'

        # Получение всех ответов на данный запрос для данного пользователя и их запись в сообщение для ответа
        all_responses = answers.get(user_id).get(request)
        for response in all_responses:
            if response[0:2] == "##":
                response = f'Стикер №{response[2:]}'
            string_responses += f'\n{response}'

        # Возврат сообщения со списком всех доступных запросов
        return f'Ответы на запрос "{request.capitalize()}":\n{string_responses}'

    def get_all_commands(self, arg=None, user_id=None):
        """ Предоставление списка всех доступных команд бота.

        :param arg: None.
        :type arg: None.

        :param user_id: None.
        :type user_id: None.

        :return: сообщение со списком всех доступных команд бота.
        """
        if user_id is None:
            return
        string_commands = str()
        number = 1
        role = roles[users_info.get(user_id, {}).get('role', 'user')] + 1

        # Получение всех команд и их запись в сообщение для ответа
        for command in self.commands.items():
            if command[0].count('!') <= role:
                string_commands += f'\n{number}. {command[0].capitalize()}\n{command[1][1]}\n\n'
                number += 1

        return f'Команды:\n{string_commands}'

    def choose_random(self, arg, user_id, message=None):
        users_info[user_id]['args'] = arg

        # Завершение работы с генератором и возврат к автоответчику
        if arg == 'back' or (message is not None and message.lower().strip() == 'назад'):
            users_info[user_id]['method'] = None
            users_info[user_id]['args'] = None
            vk_session.method('messages.send',
                              {'user_id': int(user_id), 'message': "Вы завершили работу с генератором случайных чисел",
                               'random_id': 0, 'keyboard': main_keyboard})
            return

        # Случайное вещественное число от 0 до 1
        elif arg == 'random':
            users_info[user_id]['args'] = None
            answer = f"Ваше случайное число: {random.random()}"

        # Случайное целое число от A до B
        elif arg == 'randint':
            if message is None:
                answer = f"Случайное целое число от A до B\n" \
                         f"Введите 2 целых числа через пробел - граничные значения A и B"
            else:
                split_message = sorted(message.split(' '))
                if len(split_message) == 2 and self.is_int(split_message[0]) and self.is_int(split_message[1]):
                    answer = f"Ваше случайное число: {random.randint(int(split_message[0]), int(split_message[1]))}"
                else:
                    answer = "Неверные аргументы"

        # Случайное вещественное число от A до B
        elif arg == 'uniform':
            if message is None:
                answer = f"Случайное вещественное число от A до B\n" \
                         f"Введите 2 вещественных числа через пробел - граничные значения A и B"
            else:
                split_message = sorted(message.replace(',', '.').split(' '))
                if len(split_message) == 2 and self.is_float(split_message[0]) and self.is_float(split_message[1]):
                    answer = f"Ваше случайное число: {random.uniform(float(split_message[0]), float(split_message[1]))}"
                else:
                    answer = "Неверные аргументы"

        # Случайный элемент последовательности
        elif arg == 'choice':
            if message is None:
                answer = f"Случайный элемент последовательности\n" \
                         f"Введите последовательность элементов через пробел"
            elif len(message.split(' ')) > 0:
                split_message = message.split(' ')
                answer = f"Ваш случайный элемент: {random.choice(split_message)}"
            else:
                answer = "Неверные аргументы"

        # Профессиональный генератор
        elif arg == 'professional':
            keyboard = str(json.dumps(
                {
                    "inline": False,
                    "buttons": [
                        [get_callback_button("Бета-распределение", 'positive',
                                             {"args": "betavariate"})],
                        [get_callback_button("Гамма-распределение", 'positive',
                                             {"args": "gammavariate"})],
                        [get_callback_button("Экспоненциальное распределение", 'positive',
                                             {"args": "expovariate"})],
                        [get_callback_button("Нормальное распределение", 'positive',
                                             {"args": "normalvariate"})],
                        [get_callback_button("Простой генератор", 'primary',
                                             {"args": "simple"})],
                    ]
                },
                ensure_ascii=False))

            vk_session.method('messages.send',
                              {'user_id': int(user_id), 'message': "~Профессиональный генератор~\n"
                                                                   "[ДОСТУПЕН ОГРАНИЧЕННОЕ ВРЕМЯ]\n\n"
                                                                   "Выберите тип профессионального генератора случайных чисел.\n"
                                                                   "Если желаете использовать генератор многократно, достаточно выбрать тип один раз и повторять ввод аргументов.\n"
                                                                   "Если не знаете, как этим пользоваться, выберите кнопку \"Простой генератор\"",
                               'random_id': 0,
                               'keyboard': keyboard})

            return

        # Бета-распределение
        elif arg == 'betavariate':
            if message is None:
                answer = f"Бета-распределение\n" \
                         f"Введите значения α (>0) и β (>0) через пробел"
            else:
                split_message = message.replace(',', '.').split(' ')
                if len(split_message) == 2 and self.is_float(split_message[0]) and self.is_float(split_message[1]) and \
                        float(split_message[0]) > 0 and float(split_message[1]) > 0:
                    answer = f"Ваш случайный элемент: {random.betavariate(float(split_message[0]), float(split_message[1]))}"
                else:
                    answer = "Неверные аргументы"

        # Гамма-распределение
        elif arg == 'gammavariate':
            if message is None:
                answer = f"Гамма-распределение\n" \
                         f"Введите значения α (>0) и β (>0) через пробел"
            else:
                split_message = message.replace(',', '.').split(' ')
                if len(split_message) == 2 and self.is_float(split_message[0]) and self.is_float(split_message[1]) and \
                        float(split_message[0]) > 0 and float(split_message[1]) > 0:
                    answer = f"Ваш случайный элемент: {random.gammavariate(float(split_message[0]), float(split_message[1]))}"
                else:
                    answer = "Неверные аргументы"

        # Экспоненциальное распределение
        elif arg == 'expovariate':
            if message is None:
                answer = f"Экспоненциальное распределение\n" \
                         f"Введите значение λ (≠0) через пробел"
            else:
                split_message = message.replace(',', '.').split(' ')
                if len(split_message) == 1 and self.is_float(split_message[0]) and float(split_message[0]) != 0:
                    answer = f"Ваш случайный элемент: {random.expovariate(float(split_message[0]))}"
                else:
                    answer = "Неверные аргументы"

        # Нормальное распределение
        elif arg == 'normalvariate':
            if message is None:
                answer = f"Нормальное распределение\n" \
                         f"Введите значения μ и σ (>0) через пробел"
            else:
                split_message = message.replace(',', '.').split(' ')
                if len(split_message) == 2 and self.is_float(split_message[0]) and self.is_float(split_message[1]) and \
                        float(split_message[1]) > 0:
                    answer = f"Ваш случайный элемент: {random.normalvariate(float(split_message[0]), float(split_message[1]))}"
                else:
                    answer = "Неверные аргументы"

        # Простой генератор (по умолчанию)
        else:
            # if arg is None
            keyboard = str(json.dumps(
                {
                    'inline': False,
                    'buttons': [
                        [get_callback_button('Случайное вещественное число от 0 до 1', 'positive',
                                             {'args': 'random'})],
                        [get_callback_button('Случайное целое число от A до B', 'positive',
                                             {'args': 'randint'})],
                        [get_callback_button('Случайное вещественное число от A до B', 'positive',
                                             {'args': 'uniform'})],
                        [get_callback_button('Случайный элемент последовательности', 'positive',
                                             {'args': 'choice'})],
                        [get_callback_button('Профессиональный генератор', 'primary',
                                             {'args': 'professional'})],
                        [get_callback_button('Назад', 'negative', {'args': 'back'})]
                    ]
                },
                ensure_ascii=False))

            vk_session.method('messages.send',
                              {'user_id': int(user_id), 'message': '~Простой генератор~\n\n'
                                                                   'Выберите тип генератора случайных чисел.\n'
                                                                   'Если желаете использовать генератор многократно, достаточно выбрать тип один раз и повторять ввод аргументов.\n'
                                                                   'Для возврата выберите кнопку "Назад"',
                               'random_id': 0,
                               'keyboard': keyboard})

            users_info[user_id]['method'] = 'choose_random'
            users_info[user_id]['args'] = None
            return

        vk_session.method('messages.send',
                          {'user_id': int(user_id), 'message': answer, 'random_id': 0})

    def set_role(self, arg, admin_id):
        admin_id = str(admin_id)

        if roles[users_info.get(admin_id).get('role')] < roles['admin']:
            return f'Недостаточный уровень доступа ({users_info.get(admin_id).get("role")})'

        split = [x.lower().strip() for x in arg.split('\n')]
        if len(split) != 2 or not split[0].isdigit() or split[1] not in roles:
            return self.errors[2]
        elif split[0] not in users_info.keys():
            return 'Пользователь не найден'
        elif split[0] == admin_id:
            return 'Вы не можете изменить свой уровень доступа'
        elif roles[users_info.get(admin_id).get('role')] <= roles[users_info.get(split[0]).get('role')]:
            return f'Вы не можете изменить уровень доступа пользователя уровня {users_info.get(split[0]).get("role")}'
        else:
            users_info[split[0]]['role'] = split[1]

            user = vk_session.method('users.get', {'user_ids': int(admin_id)})[0]
            name = f"{user.get('first_name')} {user.get('last_name')}"
            vk_session.method('messages.send',
                              {'user_id': int(split[0]),
                               'message': f'Ваш уровень доступа изменен на "{split[1]}" пользователем "{name}" '
                                          f'уровня "{users_info.get(admin_id).get("role")}"',
                               'random_id': 0})

            return f'Пользователю "{split[0]}" выдан уровень доступа "{split[1]}"'

    @staticmethod
    def get_balance(arg, user_id):
        return f'Ваш баланс: {users_info[user_id]["balance"]}💰'

    def give_money(self, arg, admin_id):
        admin_id = str(admin_id)
        if arg is None:
            return self.errors[2]
        split = arg.split('\n')

        if roles[users_info.get(admin_id).get('role')] < roles['admin']:
            return f'Недостаточный уровень доступа ({users_info.get(admin_id).get("role")})'
        elif len(split) != 2 or not self.is_int(split[0]) or not self.is_float(split[1]):
            return self.errors[2]
        elif users_info.get(str(split[0])) is None:
            return 'Пользователь не найден'
        else:
            users_info[str(split[0])]['balance'] += float(split[1])

            user = vk_session.method('users.get', {'user_ids': int(admin_id)})[0]
            name = f"{user.get('first_name')} {user.get('last_name')}"
            vk_session.method('messages.send',
                              {'user_id': int(split[0]),
                               'message': f'Вам начислено "{split[1]}"💰 пользователем "{name}" '
                                          f'уровня "{users_info.get(admin_id).get("role")}"\n'
                                          f'Баланс: {users_info[str(split[0])]["balance"]}💰',
                               'random_id': 0})
            return f'Пользователю "{split[0]}" начислено {split[1]}💰.\n' \
                   f'Баланс: {users_info[str(split[0])]["balance"]}💰'

    @staticmethod
    def game_start(arg, user_id, message=None):
        """ Начало игры "Математика".

        :param message: сообщение от пользователя.
        :type message: str.

        :param arg: None.
        :type arg: None.

        :param user_id: ID пользователя, вызвавшего команду.
        :type user_id: int или str.
        """
        # Завершение работы с игровым меню и возврат к автоответчику
        if arg == 'back':
            users_info[user_id]['method'] = None
            users_info[user_id]['args'] = None
            vk_session.method('messages.send',
                              {'user_id': int(user_id), 'message': "Вы завершили работу с игровым меню",
                               'random_id': 0, 'keyboard': main_keyboard})

        elif arg == 'game_math':
            change_users_info(user_id, new_class='game_math')
            game_math_class.start(str(user_id))
            return

        elif arg == 'game_luck':
            change_users_info(user_id, new_class='game_luck')
            game_luck_class.start(str(user_id))
            return

        else:
            keyboard = str(json.dumps(
                {
                    'inline': False,
                    'buttons': [
                        [get_callback_button('Математика', 'positive', {'args': 'game_math'})],
                        [get_callback_button('Удача', 'positive', {'args': 'game_luck'})],
                        [get_callback_button("Назад", 'negative', {'args': 'back'})]
                    ]
                },
                ensure_ascii=False))

            vk_session.method('messages.send',
                              {'user_id': int(user_id), 'message': '~Игровое меню~\n\n'
                                                                   'Выберите игру.\n'
                                                                   'Для возврата выберите кнопку "Назад"',
                               'random_id': 0,
                               'keyboard': keyboard})

            users_info[user_id]['method'] = 'game_start'
            users_info[user_id]['args'] = None

    @staticmethod
    def is_command(string):
        """ Проверка: является ли сообщение командой.
        :param string: str.

        :return: True, если сообщение - команда.
            False - иначе.
        """
        return string.startswith('!')

    @staticmethod
    def is_int(string):
        """ Проверка: является ли сообщение целым числом.
        :param string: str.

        :return: True, если сообщение - целое число.
            False - иначе.
        """
        try:
            return float(string) == int(string)
        except ValueError:
            return False

    @staticmethod
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

    @staticmethod
    def fix_command(text, words):
        """ Поиск максимально приближенного к text сообщения из words.
        :param text: сообщение для анализа.
        :type text: str.

        :param words: список идеальных сообщений, среди которых надо искать максимальное приближение.
        :type words: list<str>.

        :return: command из words, максимально похожий на text, если процент совпадения больше 0.5.
            None - иначе.
        """
        # Оригинальный текст
        text_original = text.lower()
        # Текст после транслитерации
        text_transliteration = translit(text, 'ru')
        # Текст после преобразования раскладки клавиатуры
        text_qwerty = translit(text, language_code='qwerty')

        array = np.array(words)
        command_original, rate_original = \
            min(list(zip(words, list(normalized_damerau_levenshtein_distance_seqs(text_original, array)))),
                key=lambda x: x[1])
        command_transliteration, rate_transliteration = \
            min(list(zip(words, list(normalized_damerau_levenshtein_distance_seqs(text_transliteration, array)))),
                key=lambda x: x[1])
        command_qwerty, rate_qwerty = \
            min(list(zip(words, list(normalized_damerau_levenshtein_distance_seqs(text_qwerty, array)))),
                key=lambda x: x[1])

        rate = min(rate_original, rate_transliteration, rate_qwerty)
        if rate == rate_original:
            command = command_original
            if rate > 0:
                data.synonyms_stats += [(text, command, "original", rate)]
        elif rate == rate_transliteration:
            command = command_transliteration
            if rate > 0:
                data.synonyms_stats += [(text, command, "transliteration", rate)]
        else:
            command = command_qwerty
            if rate > 0:
                data.synonyms_stats += [(text, command, "qwerty", rate)]

        # Подобранное значение для определения совпадения текста среди значений указанного списка
        # Если True, считаем что слишком много ошибок в слове, т.е. text среди запросов нет
        if rate > 0.5:
            return

        return command

    def reset_position(self, arg, admin_id):
        admin_id = str(admin_id)

        if roles[users_info.get(admin_id).get('role')] < roles['admin']:
            return f'Недостаточный уровень доступа ({users_info.get(admin_id).get("role")})'
        elif arg is None or not self.is_int(arg):
            return self.errors[2]
        elif users_info.get(str(arg)) is None:
            return 'Пользователь не найден'
        else:
            change_users_info(user_id=str(arg), new_class='autoresponder')

            user = vk_session.method('users.get', {'user_ids': int(admin_id)})[0]
            name = f"{user.get('first_name')} {user.get('last_name')}"
            vk_session.method('messages.send',
                              {'user_id': int(arg),
                               'message': f'Вы были перенаправлены в главное меню бота пользователем "{name}" '
                                          f'уровня "{users_info.get(admin_id).get("role")}"',
                               'random_id': 0, 'keyboard': main_keyboard})
            return f'Пользователь "{arg}" отправлен в главное меню.'
