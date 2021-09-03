import sys
from data import *
from autoresponder import *


def main():
    is_bot_active = True
    autoresponder = Autoresponder()
    methods = {"GameMath.game": autoresponder.game_math_class.game,
               "GameMath.use_lives": autoresponder.game_math_class.use_live}

    while True:
        try:
            for event in longpoll.listen():

                # Обработка сообщений
                if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:

                    # Получение сообщения
                    message = event.obj.text

                    # Проверка на команды от администратора TODO: Брать из списка администраторов
                    if event.obj.from_id == 171254367:

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
                                          {'user_id': event.obj.from_id,
                                           'message': "Меня тут пока что улучшают, и я не могу отвечать."
                                                      "\nПопробуй написать мне немного позднее", 'random_id': 0})
                        vk_session.method('messages.send',
                                          {'user_id': event.obj.from_id, 'random_id': 0, 'sticker_id': 18493})  # 58715
                        break

                    # Регистрация пользователей при первом запросе
                    if event.obj.from_id not in users:
                        users.append(event.obj.from_id)

                    # Основная обработка сообщений
                    try:
                        autoresponder.respond(event.obj.from_id, message)
                    except Exception:
                        vk_session.method('messages.send',
                                          {'user_id': event.obj.from_id, 'message':
                                              "Ой, кажется, у меня что-то сломалось ;o\n"
                                              "Но я еще работаю! Надеюсь, такого больше не повторится",
                                           'random_id': 0})
                        vk_session.method('messages.send',
                                          {'user_id': event.obj.from_id, 'random_id': 0, 'sticker_id': 18467})

                        exc_type, exc_value = sys.exc_info()[:2]
                        vk_session.method('messages.send',
                                          {'user_id': 171254367, 'message': "FROM:\n" + event.obj.from_id +
                                                                            "\nERROR:\n"
                                                                            f'{exc_type.__name__} => {exc_value} in '
                                                                            f'{threading.current_thread().name}',
                                           'random_id': 0})

                if event.type == VkBotEventType.MESSAGE_EVENT:
                    if methods.get(event.obj.payload.get('method')) is not None:
                        methods.get(event.obj.payload.get('method'))(event.obj.user_id, event.obj.payload.get('args'))
                        vk_session.method('messages.sendMessageEventAnswer',
                                          {'event_id': event.obj.event_id,
                                           'user_id': event.obj.user_id,
                                           'peer_id': event.obj.peer_id})

                if event.type == VkBotEventType.VKPAY_TRANSACTION:
                    user_id = str(event.obj.from_id)
                    user_info = game_math_stats.get(user_id)
                    game_math_stats.update(
                        {user_id: {'is_active': user_info.get('is_active'), 'lives': user_info.get('lives') + 5,
                                   'answer': user_info.get('answer'), 'score': user_info.get('score')}}
                    )
                    vk_session.method('messages.send',
                                      {'user_id': event.obj.from_id, 'message':
                                          "Вам начислено 5 жизней.\n"
                                          "На данный момент у Вас жизней: {}".format(
                                              game_math_stats.get(user_id).get('lives')),
                                       'random_id': 0})

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
