import sys
from data import *
from autoresponder import *


def main():
    is_bot_active = True
    autoresponder = Autoresponder()
    methods = {"GameMath.game": autoresponder.game_math_class.game,
               "GameMath.use_lives": autoresponder.game_math_class.use_live}

    with open("users_id.json", "r") as read_file:
        if len(read_file.read()) == 0:
            users = list()
        else:
            read_file.seek(0)
            users = list(json.load(read_file))
        read_file.close()

    while True:
        try:
            for event in longpoll.listen():
                if event.obj.from_id == 171254367:
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

                if not is_bot_active:
                    vk_session.method('messages.send',
                                      {'user_id': event.obj.from_id,
                                       'message': "Меня тут пока что улучшают, и я не могу отвечать."
                                                  "\nПопробуй написать мне немного позднее", 'random_id': 0})
                    vk_session.method('messages.send',
                                      {'user_id': event.obj.from_id, 'random_id': 0, 'sticker_id': 58715})
                    break

                if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:

                    # # TODO: vvv Обработка сообщений во время тестирования УБРАТЬ ПРИ СОХРАНЕНИИ
                    # if event.obj.from_id != 171254367:
                    #     vk_session.method('messages.send',
                    #                       {'user_id': event.obj.from_id,
                    #                        'message': "Меня тут пока что улучшают, и я не могу отвечать."
                    #                                   "\nПопробуй написать мне немного позднее", 'random_id': 0})
                    #     vk_session.method('messages.send',
                    #                       {'user_id': event.obj.from_id, 'random_id': 0, 'sticker_id': 58715})
                    #     break
                    # # TODO: ^^^ УБРАТЬ ПРИ СОХРАНЕНИИ

                    # Регистрация пользователей при первом запросе
                    if event.obj.from_id not in users:
                        with open("users_id.json", "w") as write_file:
                            users.append(event.obj.from_id)
                            json.dump(users, write_file)
                    # Получение сообщения
                    message = event.obj.text

                    # Рассылка для всех зарегистрированных пользователей
                    if message.split('#')[0].strip().lower() == '!рассылка_05491':
                        for user in users:
                            vk_session.method('messages.send',
                                              {'user_id': user, 'message': message.split('#')[1].strip(),
                                               'random_id': 0})

                    # Основная обработка сообщений
                    else:
                        try:
                            autoresponder.respond(event.obj.from_id, message)
                        except Exception:
                            vk_session.method('messages.send',
                                              {'user_id': event.obj.from_id, 'message':
                                                  "Ой, кажется, у меня что-то сломалось ;o\n"
                                                  "Но я еще работаю! Надеюсь, такого больше не повторится",
                                               'random_id': 0})
                            vk_session.method('messages.send',
                                              {'user_id': event.obj.from_id, 'random_id': 0, 'sticker_id': 16588})

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
