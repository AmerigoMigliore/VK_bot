# >Created by ATB<
import datetime
import sys
import threading

import requests

from data import roles, save_all, users_info, game_math_stats, add_new_user, change_users_info, main_keyboard, tz
from vk_auth import longpoll
from autoresponder import Autoresponder
from all_games import game_math_class, game_luck_class, game_pets_class
from vk_auth import VkBotEventType, vk_session


is_bot_active = True
autoresponder_class = Autoresponder()
all_classes = {
    'autoresponder': autoresponder_class,
    'game_math': game_math_class,
    'game_luck': game_luck_class,
    'game_pets': game_pets_class
}
max_messages_per_min = 17


def update_flood_control(user_id):
    if user_id not in users_info.keys():
        add_new_user(user_id)

    if users_info.get(user_id).get('lock') is None:
        users_info[user_id]['lock'] = threading.Lock()

    if users_info.get(user_id, {}).get('is_stopped', False):
        return -1
    if users_info.get(user_id, {}).get('messages_per_min') is not None:
        minute = datetime.datetime.now(tz=tz).minute
        users_info[user_id]['messages_per_min'] = [x for x in users_info.get(user_id, {}).get('messages_per_min', [])
                                                   if x.minute == minute]
        users_info[user_id]['messages_per_min'] += [datetime.datetime.now(tz=tz)]

        if len(users_info.get(user_id).get('messages_per_min')) >= max_messages_per_min:
            users_info[user_id]['is_stopped'] = True
            threading.Timer(10, function=del_from_stop_list, args=[user_id]).start()
            return 0
        else:
            return 1
    else:
        users_info[user_id]['messages_per_min'] = [datetime.datetime.now(tz=tz)]
        users_info[user_id]['is_stopped'] = False
        return 1


def del_from_stop_list(user_id):
    users_info[user_id]['is_stopped'] = False


def main():
    sys.stderr = open(f'log.txt', 'a')
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
        if event.type == VkBotEventType.MESSAGE_NEW or event.type == VkBotEventType.MESSAGE_EVENT:
            user_id = str(event.obj.from_id)
            if user_id is None:
                user_id = str(event.obj.user_id)

            n = update_flood_control(user_id)
        else:
            n = 1

        if n == -1:
            return
        else:
            # Обработка сообщений
            if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:
                user_id = str(event.obj.from_id)

                # Получение сообщения
                message = event.obj.text

                if roles[users_info.get(user_id, {}).get('role', 'user')] >= roles['admin']:

                    # Рассылка для всех зарегистрированных пользователей (!рассылка#сообщение)
                    if message.split('#')[0].strip().lower() == '!рассылка':
                        for to_id in users_info.keys():
                            vk_session.method('messages.send',
                                              {'user_id': int(to_id), 'message': message.split('#')[1].strip(),
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
                                      {'user_id': int(user_id),
                                       'message': "Меня тут пока что улучшают, и я не могу отвечать."
                                                  "\nПопробуй написать мне немного позднее", 'random_id': 0})
                    vk_session.method('messages.send',
                                      {'user_id': int(user_id), 'random_id': 0, 'sticker_id': 18493})  # 58715
                    return

                # Регистрация пользователей при первом запросе
                if user_id not in users_info.keys():
                    add_new_user(user_id)

                # Основная обработка сообщений
                users_info[user_id]['lock'].acquire()
                try:
                    all_classes.get(users_info.get(user_id, {}).get('class', 'autoresponder')) \
                        .process_event(event=event)
                finally:
                    users_info[user_id]['lock'].release()

                # Проверка на количество непрочитанных ботом сообщений и возврат в главное меню, если их больше 1
                if vk_session.method('messages.getConversationsById', {'peer_ids': int(user_id)}).get('items', {})[0].get('unread_count', 0) > 1:
                    change_users_info(user_id=str(user_id), new_class='autoresponder')
                    answer = f'Вы были перенаправлены в главное меню бота'
                    vk_session.method('messages.send',
                                      {'user_id': int(user_id),
                                       'message': answer,
                                       'random_id': 0, 'keyboard': main_keyboard})

            # Обработка событий
            if event.type == VkBotEventType.MESSAGE_EVENT:
                user_id = str(event.obj.user_id)
                try:
                    # Если сообщение не от администратора, проверить бота на включенность. Иначе выдать сообщение
                    if roles[users_info.get(user_id, {}).get('role', 'user')] < roles['admin'] and not is_bot_active:
                        vk_session.method('messages.send',
                                          {'user_id': int(user_id),
                                           'message': "Меня тут пока что улучшают, и я не могу отвечать."
                                                      "\nПопробуй написать мне немного позднее", 'random_id': 0})
                        vk_session.method('messages.send',
                                          {'user_id': int(user_id), 'random_id': 0, 'sticker_id': 18493})  # 58715
                        return

                    users_info[user_id]['lock'].acquire()
                    try:
                        all_classes.get(users_info.get(user_id, {}).get('class', 'autoresponder')) \
                            .process_event(event=event)
                    finally:
                        users_info[user_id]['lock'].release()
                finally:
                    # Сброс активированной кнопки, вызвавшей событие
                    vk_session.method('messages.sendMessageEventAnswer',
                                      {'event_id': event.obj.event_id,
                                       'user_id': int(user_id),
                                       'peer_id': event.obj.peer_id})

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

            # Отправка уведомления от Flood Control
            if n == 0:
                user_id = event.obj.from_id
                if user_id is None:
                    user_id = event.obj.user_id
                if user_id is not None:
                    vk_session.method('messages.send',
                                      {'user_id': int(user_id), 'message':
                                          "Я устал, мне нужен отдых!",
                                       'random_id': 0})
                    vk_session.method('messages.send',
                                      {'user_id': int(user_id), 'random_id': 0, 'sticker_id': 9425})

    except Exception as exc_longpoll:
        user_id = event.obj.from_id
        if user_id is None:
            user_id = event.obj.user_id
        if user_id is not None:
            vk_session.method('messages.send',
                              {'user_id': int(user_id), 'message':
                                  "Ой, кажется, у меня что-то сломалось ;o\n"
                                  "Но я еще работаю! Надеюсь, такого больше не повторится",
                               'random_id': 0})
            vk_session.method('messages.send',
                              {'user_id': int(user_id), 'random_id': 0, 'sticker_id': 18467})

            exc_type, exc_value = sys.exc_info()[:2]
            vk_session.method('messages.send',
                              {'user_id': 171254367, 'message': f'FROM:\n{user_id}'
                                                                f'\nERROR:\n'
                                                                f'{exc_type.__name__} => {exc_value} in '
                                                                f'{threading.current_thread().name}',
                               'random_id': 0})
        with open('log.txt', 'a') as log_file:
            log_file.write(f'\n\n[{datetime.datetime.now(tz=tz)}]\n')
            log_file.close()
        raise exc_longpoll


try:
    main()
except KeyboardInterrupt:
    raise
finally:
    save_all()
    print("\033[1m\033[32m\033[40mBye!\033[0m")
    sys.exit()
