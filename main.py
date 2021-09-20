# >Created by ATB<

import sys
from data import users, save_all
from vk_auth import longpoll
from autoresponder import Autoresponder
from all_games import *


def main():
    is_bot_active = True
    autoresponder_class = Autoresponder()
    all_classes = {
        "autoresponder": autoresponder_class,
        "game_math": game_math_class
    }

    while True:
        try:
            for event in longpoll.listen():
                try:
                    # Обработка сообщений
                    if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:
                        user_id = event.obj.from_id

                        # Получение сообщения
                        message = event.obj.text

                        # Проверка на команды от администратора TODO: Брать из списка администраторов
                        if user_id == 171254367:

                            # Рассылка для всех зарегистрированных пользователей (!рассылка#сообщение)
                            if message.split('#')[0].strip().lower() == '!рассылка':
                                for user_info in users:
                                    vk_session.method('messages.send',
                                                      {'user_id': user_info, 'message': message.split('#')[1].strip(),
                                                       'random_id': 0})

                            # Включение/выключение бота
                            if event.obj.text.lower() == "!выключить":
                                is_bot_active = False
                                vk_session.method('messages.send',
                                                  {'user_id': 171254367,
                                                   'message': "Бот выключен", 'random_id': 0})
                                break
                            elif event.obj.text.lower() == "!включить":
                                is_bot_active = True
                                vk_session.method('messages.send',
                                                  {'user_id': 171254367,
                                                   'message': "Бот включен", 'random_id': 0})
                                break

                        # Если сообщение не от администратора, проверить бота на включенность. Иначе выдать сообщение
                        elif not is_bot_active:
                            vk_session.method('messages.send',
                                              {'user_id': user_id,
                                               'message': "Меня тут пока что улучшают, и я не могу отвечать."
                                                          "\nПопробуй написать мне немного позднее", 'random_id': 0})
                            vk_session.method('messages.send',
                                              {'user_id': user_id, 'random_id': 0, 'sticker_id': 18493})  # 58715
                            break

                        # Регистрация пользователей при первом запросе
                        if user_id not in users:
                            users.append(user_id)

                        # Основная обработка сообщений
                        all_classes.get(where_are_users.get(str(user_id), {}).get('class', 'autoresponder'))\
                            .process_event(event=event)

                    # Обработка событий
                    if event.type == VkBotEventType.MESSAGE_EVENT:
                        all_classes.get(where_are_users.get(str(event.obj.user_id), {}).get('class', 'autoresponder'))\
                            .process_event(event=event)

                    # TODO: ТЕСТИРОВАТЬ!!!
                    if event.type == VkBotEventType.VKPAY_TRANSACTION:
                        user_id = event.obj.from_id
                        if user_id is None:
                            user_id = event.obj.user_id
                        user_id = str(user_id)

                        user_info = game_math_stats.get(user_id)
                        game_math_stats.update(
                            {user_id: {'is_active': user_info.get('is_active'), 'lives': user_info.get('lives') + 5,
                                       'answer': user_info.get('answer'), 'score': user_info.get('score')}}
                        )
                        vk_session.method('messages.send',
                                          {'user_id': user_id, 'message':
                                              "Вам начислено 5 жизней.\n"
                                              "На данный момент у Вас жизней: {}".format(
                                                  game_math_stats.get(user_id).get('lives')),
                                           'random_id': 0})

                except Exception as exc:
                    user_id = event.obj.from_id
                    if user_id is None:
                        user_id = event.obj.user_id
                    user_id = str(user_id)

                    vk_session.method('messages.send',
                                      {'user_id': user_id, 'message':
                                          "Ой, кажется, у меня что-то сломалось ;o\n"
                                          "Но я еще работаю! Надеюсь, такого больше не повторится",
                                       'random_id': 0})
                    vk_session.method('messages.send',
                                      {'user_id': user_id, 'random_id': 0, 'sticker_id': 18467})

                    exc_type, exc_value = sys.exc_info()[:2]
                    vk_session.method('messages.send',
                                      {'user_id': 171254367, 'message': "FROM:\n" + str(user_id) +
                                                                        "\nERROR:\n"
                                                                        f'{exc_type.__name__} => {exc_value} in '
                                                                        f'{threading.current_thread().name}',
                                       'random_id': 0})

                    print("Exception: ", exc)
        # Обработка длительного ожидания от longpoll
        except Exception:
            pass


try:
    main()
except KeyboardInterrupt:
    raise
finally:
    save_all(True)
    print("\033[1m\033[32m\033[40mBye!\033[0m")
    sys.exit()
