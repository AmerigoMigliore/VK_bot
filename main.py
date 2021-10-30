# >Created by ATB<

import sys
import threading
import time

import requests
import vk_api.exceptions

from data import roles, save_all, users_info, game_math_stats, add_new_user
from vk_auth import longpoll
from autoresponder import Autoresponder
from all_games import game_math_class, game_luck_class
from vk_auth import VkBotEventType, vk_session


is_bot_active = True
autoresponder_class = Autoresponder()
all_classes = {
    'autoresponder': autoresponder_class,
    'game_math': game_math_class,
    'game_luck': game_luck_class
}


def main():
    while True:
        try:
            for event in longpoll.listen():
                threading.Thread(target=async_longpoll_listen, args=[event]).start()

        # Обработка длительного ожидания от longpoll
        except requests.exceptions.ReadTimeout:
            pass


def async_longpoll_listen(event):
    global is_bot_active
    try:
        # Обработка сообщений
        if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:
            user_id = event.obj.from_id

            # Получение сообщения
            message = event.obj.text

            if roles[users_info.get(str(user_id), {}).get('role', 'user')] >= roles['admin']:

                # Рассылка для всех зарегистрированных пользователей (!рассылка#сообщение)
                if message.split('#')[0].strip().lower() == '!рассылка':
                    for to_id in users_info.keys():
                        vk_session.method('messages.send',
                                          {'user_id': to_id, 'message': message.split('#')[1].strip(),
                                           'random_id': 0})

                # Включение/выключение бота
                if event.obj.text.lower() == "!выключить":
                    is_bot_active = False
                    vk_session.method('messages.send',
                                      {'user_id': 171254367,
                                       'message': "Бот выключен", 'random_id': 0})
                    return
                elif event.obj.text.lower() == "!включить":
                    is_bot_active = True
                    vk_session.method('messages.send',
                                      {'user_id': 171254367,
                                       'message': "Бот включен", 'random_id': 0})
                    return

            # Если сообщение не от администратора, проверить бота на включенность. Иначе выдать сообщение
            elif not is_bot_active:
                vk_session.method('messages.send',
                                  {'user_id': user_id,
                                   'message': "Меня тут пока что улучшают, и я не могу отвечать."
                                              "\nПопробуй написать мне немного позднее", 'random_id': 0})
                vk_session.method('messages.send',
                                  {'user_id': user_id, 'random_id': 0, 'sticker_id': 18493})  # 58715
                return

            # Регистрация пользователей при первом запросе
            if str(user_id) not in users_info.keys():
                add_new_user(user_id)

            # Основная обработка сообщений
            all_classes.get(users_info.get(str(user_id), {}).get('class', 'autoresponder')) \
                .process_event(event=event)

        # Обработка событий
        if event.type == VkBotEventType.MESSAGE_EVENT:
            all_classes.get(users_info.get(str(event.obj.user_id), {}).get('class', 'autoresponder')) \
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

        if exc == vk_api.exceptions.ApiError and exc.code == 9:
            time.sleep(10)  # TODO: Оно работает?
        else:
            vk_session.method('messages.send',
                              {'user_id': user_id, 'message':
                                  "Ой, кажется, у меня что-то сломалось ;o\n"
                                  "Но я еще работаю! Надеюсь, такого больше не повторится",
                               'random_id': 0})
            vk_session.method('messages.send',
                              {'user_id': user_id, 'random_id': 0, 'sticker_id': 18467})

        exc_type, exc_value = sys.exc_info()[:2]
        vk_session.method('messages.send',
                          {'user_id': 171254367, 'message': f'FROM:\n{user_id}'
                                                            f'\nERROR:\n'
                                                            f'{exc_type.__name__} => {exc_value} in '
                                                            f'{threading.current_thread().name}',
                           'random_id': 0})

        print("Exception: ", exc)
        # raise


try:
    main()
except KeyboardInterrupt:
    raise
finally:
    save_all(True)
    print("\033[1m\033[32m\033[40mBye!\033[0m")
    sys.exit()
