from vk_auth import vk_session, VkBotEventType
from data import users_info, change_users_info, main_keyboard
from keyboard import get_callback_button, get_text_button
import json
import random


class GameLuck:
    start_keyboard = None

    def __init__(self):
        self.start_keyboard = str(json.dumps(
                {
                    'inline': False,
                    'one_time': True,
                    'buttons': [
                        [get_callback_button('Случайное число', 'positive', {'args': 'random_number'})],
                        [get_callback_button('3 из 9', 'positive', {'args': 'three_out_of_nine'})],
                        [get_callback_button('Назад', 'negative', {'args': 'back'})]
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

            method = users_info.get(user_id, {}).get('method')
            args = event.obj.payload.get('args')

            if method == 'start':
                if args == 'back':
                    vk_session.method('messages.send',
                                      {'user_id': int(user_id),
                                       'message': 'Сегодня твой удачный день! Приходи еще!',
                                       'random_id': 0, 'keyboard': main_keyboard})
                    change_users_info(user_id, 'autoresponder')

                    # Сброс активированной кнопки, вызвавшей событие
                    vk_session.method('messages.sendMessageEventAnswer',
                                      {'event_id': event.obj.event_id,
                                       'user_id': int(user_id),
                                       'peer_id': event.obj.peer_id})
                    return
                else:
                    self.start(user_id, args)

            elif method == 'random_number':
                self.random_number(user_id, args)

            elif method == 'three_out_of_nine':
                self.three_out_of_nine(user_id, args)

            # Сброс активированной кнопки, вызвавшей событие
            vk_session.method('messages.sendMessageEventAnswer',
                              {'event_id': event.obj.event_id,
                               'user_id': int(user_id),
                               'peer_id': event.obj.peer_id})

        elif event.type == VkBotEventType.MESSAGE_NEW:
            user_id = str(event.obj.from_id)
            message = event.obj.text.lower()
            method = users_info.get(user_id, {}).get('method', None)
            args = users_info.get(user_id, {}).get('args', None)

            if method == 'random_number':
                self.random_number(user_id, args, message)

            if method == 'three_out_of_nine':
                self.three_out_of_nine(user_id, args, message)

    def start(self, user_id, args=None):
        user_id = str(user_id)

        if args == 'random_number':
            change_users_info(user_id, new_method=args)
            self.random_number(user_id)
            return
        elif args == 'three_out_of_nine':
            change_users_info(user_id, new_method=args)
            self.three_out_of_nine(user_id)
            return
        else:
            message = f'~Честные лотереи~\n\n' \
                      f'Выберите игру.\n' \
                      f'Для возврата выберите кнопку "Назад"' \
                      f'Ваш баланс: {users_info.get(user_id, {}).get("balance", 0)}💰\n'

            vk_session.method('messages.send',
                              {'user_id': int(user_id), 'message': message,
                               'random_id': 0,
                               'keyboard': self.start_keyboard})

            change_users_info(user_id, new_method='start')

    def random_number(self, user_id, args=None, number=None):
        keyboard = None

        if args == 'back':
            change_users_info(user_id, new_method='start')
            self.start(user_id)
            return

        elif args == 'rules':
            message = 'Правила игры "Случайное число".\n' \
                      'Я загадываю случайное число от 100 до 999. ' \
                      'Ты, пытаясь угадать это число, называешь свой вариант - число от 100 до 999. ' \
                      'Начисление приза производится по следующей схеме:\n\n' \
                      'Угадано:\n' \
                      '3 цифры из 3 на своих местах - 20💰\n' \
                      '2 цифры из 3 на своих местах - 10💰\n' \
                      '3 цифры из 3, но только 1 на своем месте - 8💰\n' \
                      '2 цифры из 3, но только 1 на своем месте - 5💰\n' \
                      '1 цифру из 3 на своем месте - 3💰\n' \
                      '3 цифры из 3, но ни одна не на своем месте - 3💰\n\n' \
                      'Стоимость игры: 1💰'

        elif args == 'play':
            number = number.strip() if number is not None else None

            if number is not None and number.isdigit() and 100 <= int(number) <= 999:
                users_info[user_id]['balance'] -= 1
                answer = str(random.randint(100, 999))

                if number == answer:
                    users_info[user_id]['balance'] += 20
                    message = f'Браво! Вы угадали мое число и выиграли 20💰!\n' \
                              f'Ваш баланс: {users_info.get(user_id, {}).get("balance", 0)}💰\n'

                elif (number[0] == answer[0] and (number[1] == answer[1] or number[2] == answer[2])) or \
                        (number[1] == answer[1] and number[2] == answer[2]):
                    users_info[user_id]['balance'] += 10
                    message = f'Я загадал число "{answer}".\n' \
                              f'Вы угадали 2 цифры из 3 на своих местах и выиграли 10💰\n' \
                              f'Ваш баланс: {users_info.get(user_id, {}).get("balance", 0)}💰\n'

                elif set(number) == set(answer) and \
                        (number[0] == answer[0] or number[1] == answer[1] or number[2] == answer[2]):
                    users_info[user_id]['balance'] += 8
                    message = f'Я загадал число "{answer}".\n' \
                              f'Вы угадали 3 цифры из 3, но только 1 на своем месте, и выиграли 8💰\n' \
                              f'Ваш баланс: {users_info.get(user_id, {}).get("balance", 0)}💰\n'

                elif (number[0] == answer[0] and (number[1] == answer[2] or number[2] == answer[1])) or \
                        (number[1] == answer[1] and (number[0] == answer[2] or number[2] == answer[0])) or \
                        (number[2] == answer[2] and (number[0] == answer[1] or number[1] == answer[0])):
                    users_info[user_id]['balance'] += 5
                    message = f'Я загадал число "{answer}".\n' \
                              f'Вы угадали 2 цифры из 3, но только 1 на своем месте, и выиграли 5💰\n' \
                              f'Ваш баланс: {users_info.get(user_id, {}).get("balance", 0)}💰\n'

                elif number[0] == answer[0] or number[1] == answer[1] or number[2] == answer[2]:
                    users_info[user_id]['balance'] += 3
                    message = f'Я загадал число "{answer}".\n' \
                              f'Вы угадали 1 цифру из 3 на своем месте и выиграли 3💰\n' \
                              f'Ваш баланс: {users_info.get(user_id, {}).get("balance", 0)}💰\n'

                elif set(number) == set(answer):
                    users_info[user_id]['balance'] += 3
                    message = f'Я загадал число "{answer}".\n' \
                              f'Вы угадали 3 цифры из 3, но ни одна не на своем месте, и выиграли 3💰\n' \
                              f'Ваш баланс: {users_info.get(user_id, {}).get("balance", 0)}💰\n'

                else:
                    message = f'Я загадал число "{answer}".\n' \
                              f'К сожалению, в этот раз Вы ничего не выиграли, но в следующий раз Вам обязательно повезет!\n' \
                              f'Ваш баланс: {users_info.get(user_id, {}).get("balance", 0)}💰\n'

                change_users_info(user_id, new_method='random_number')

            elif users_info.get(user_id, {}).get('balance', 0) >= 1:
                change_users_info(user_id, new_method='random_number', new_args='play')
                message = 'Назовите число от 100 до 999'

            else:
                message = f'Недостаточно 💰 для игры\n' \
                          f'Ваш баланс: {users_info.get(user_id, {}).get("balance", 0)}💰\n'
                change_users_info(user_id, new_method='random_number')

        else:
            keyboard = str(json.dumps(
                {
                    'inline': False,
                    'one_time': False,
                    'buttons': [
                        [get_callback_button('Играть (1💰)', 'positive', {'args': 'play'})],
                        [get_callback_button('Правила', 'primary', {'args': 'rules'}),
                         get_callback_button('Назад', 'negative', {'args': 'back'})]
                    ]
                },
                ensure_ascii=False))

            message = '~Случайное число~\n\n' \
                      'Выберите действие.\n' \
                      'Для возврата выберите кнопку "Назад"'

        vk_session.method('messages.send',
                          {'user_id': int(user_id), 'message': message,
                           'random_id': 0,
                           'keyboard': keyboard})

    def three_out_of_nine(self, user_id, args=None, msg=None):
        keyboard = str(json.dumps(
            {
                'one_time': True,
                'buttons': [
                    [get_text_button('Играть (1💰)', 'positive')],
                    [get_callback_button('Правила', 'primary', {'args': 'rules'}),
                     get_callback_button('Назад', 'negative', {'args': 'back'})]
                ]
            },
            ensure_ascii=False))

        if args == 'back':
            change_users_info(user_id, new_method='start')
            self.start(user_id)
            return

        elif args == 'rules':
            message = 'Правила игры "3 из 9".\n' \
                      'Я загадываю 3 разных числа от 1 до 9. ' \
                      'Твоя задача выяснить, какие 3 числа я загадал, выбирая соответствующие числа на клавиатуре. ' \
                      'Начисление приза производится по следующей схеме:\n\n' \
                      'Угадано:\n' \
                      '3 числа из 3 - 5💰\n' \
                      '2 числа из 3 - 3💰\n' \
                      '1 число из 3 - 2💰\n\n' \
                      'Стоимость игры: 1💰'

        elif msg is not None:
            if msg == 'играть (1💰)':
                if users_info.get(user_id, {}).get('balance', 0) >= 1:
                    users_info[user_id]['balance'] -= 1

                    users_info[user_id]['args'] = {}
                    users_info[user_id]['args']['play'] = True
                    users_info[user_id]['args']['keyboard'] = ['secondary'] * 9
                    users_info[user_id]['args']['answer'] = random.sample(range(1, 10), 3)
                    users_info[user_id]['args']['count'] = 0

                    message = 'Я загадал 3 числа. Выбор за тобой!'
                    keyboard = self.get_keyboard(user_id)

                    users_info[user_id]['args']['message_id'] = vk_session.method('messages.send',
                                                                                  {'user_id': int(user_id),
                                                                                   'message': message,
                                                                                   'random_id': 0,
                                                                                   'keyboard': keyboard})
                    return

                else:
                    message = f'Недостаточно 💰 для игры\n' \
                              f'Ваш баланс: {users_info.get(user_id, {}).get("balance", 0)}💰\n'
            else:
                return

        elif users_info.get(user_id, {}).get('args', {}) is not None and \
                users_info.get(user_id, {}).get('args', {}).get('play', False) and str(args).isdigit():
            if users_info[user_id]['args']['keyboard'][args - 1] != 'secondary':
                message = f'Вы уже выбрали число {args}.'
            else:
                users_info[user_id]['args']['count'] += 1
                if args in users_info[user_id]['args']['answer']:
                    message = f'Ура! Число "{args}" есть в моем списке!'
                    users_info[user_id]['args']['keyboard'][args - 1] = 'positive'
                else:
                    message = f'Эх.. Числа "{args}" нет в моем списке!'
                    users_info[user_id]['args']['keyboard'][args - 1] = 'negative'

            keyboard = self.get_keyboard(user_id)

            if users_info[user_id]['args']['count'] == 3:
                count = users_info[user_id]['args']['keyboard'].count('positive')
                answer = users_info[user_id]['args']['answer']
                message += f'\n\nИгра окончена.\n' \
                           f'Я загадал числа "{answer[0]}, {answer[1]}, {answer[2]}"\n'
                if count == 3:
                    users_info[user_id]['balance'] += 5
                    message += f'Угадано 3 числа из 3.\n Выигрыш: 5💰\n'
                elif count == 2:
                    users_info[user_id]['balance'] += 3
                    message += f'Угадано 2 числа из 3.\n Выигрыш: 3💰\n'
                elif count == 1:
                    users_info[user_id]['balance'] += 2
                    message += f'Угадано 1 число из 3.\n Выигрыш: 2💰\n'
                else:
                    message += f'Увы, ни одно число не угадано.\n'

                message += f'Ваш баланс: {users_info.get(user_id, {}).get("balance", 0)}💰\n'

            vk_session.method('messages.edit',
                              {'peer_id': int(user_id), 'message': message,
                               'message_id': users_info.get(user_id, {}).get('args', {}).get('message_id', 0),
                               'random_id': 0,
                               'keyboard': keyboard})

            if users_info[user_id]['args']['count'] == 3:
                users_info[user_id]['args'] = None
                self.three_out_of_nine(user_id)

            return

        else:
            message = '~3 из 9~\n\n' \
                      'Выберите действие.\n' \
                      'Для возврата выберите кнопку "Назад"'

        vk_session.method('messages.send',
                          {'user_id': int(user_id), 'message': message,
                           'random_id': 0,
                           'keyboard': keyboard})

    @staticmethod
    def get_keyboard(user_id):
        keyboard = {
            'inline': True,
            'buttons': [[], [], []]
        }

        if users_info.get(user_id, {}).get('args', {}).get('keyboard', None) is None:
            return None

        for i, c in enumerate(users_info[user_id]['args']['keyboard']):
            keyboard['buttons'][i // 3] += [get_callback_button(i + 1, c, {'args': i + 1})]

        return str(json.dumps(keyboard, ensure_ascii=False))
