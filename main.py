import sys
from threading import Thread
from autoresponder import *

autoresponder = Autoresponder()
methods = {"GameMath.game": autoresponder.game_math_class.game}


def main():
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
                            thread = Thread(target=autoresponder.respond, args=(event.obj.from_id, message))
                            thread.start()
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

                # Встречалка при печатании
                # users_have_written = []
                # if event.type == VkBotEventType.USER_TYPING:
                #     if event.obj.from_id not in users_have_written:
                #         users_have_written.append(event.obj.from_id)
                #         vk_session.method('messages.send',
                #                           {'user_id': event.obj.from_id, 'message':
                #                               "Привет!\nЯ очень рад, что про меня вспомнили!\nНо ты пиши, не отвлекайся",
                #                            'random_id': 0})
        except Exception:
            pass


main()
