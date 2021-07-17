import sys
from threading import Thread

from autoresponder import *

autoresponder = Autoresponder()


def main():
    with open("users_id.json", "r") as read_file:
        if len(read_file.read()) == 0:
            users = list()
        else:
            read_file.seek(0)
            users = list(json.load(read_file))
        read_file.close()

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            # Регистрация пользователей при первом запросе
            if event.user_id not in users:
                with open("users_id.json", "w") as write_file:
                    users.append(event.user_id)
                    json.dump(users, write_file)

            message = event.message

            print(event.type)

            # Рассылка для всех зарегистрированных пользователей
            if message.split('#')[0].strip().lower() == '!рассылка_05491':
                for user in users:
                    vk_session.method('messages.send',
                                      {'user_id': user, 'message': message.split('#')[1].strip(), 'random_id': 0})

            else:
                try:
                    thread = Thread(target=autoresponder.respond, args=(event.user_id, message))
                    thread.start()
                except Exception:
                    vk_session.method('messages.send',
                                      {'user_id': event.user_id, 'message':
                                          "Ой, кажется, у меня что-то сломалось ;o\n"
                                          "Но я еще работаю! Надеюсь, такого больше не повторится",
                                       'random_id': 0})
                    vk_session.method('messages.send',
                                      {'user_id': event.user_id, 'random_id': 0, 'sticker_id': 16588})

                    exc_type, exc_value = sys.exc_info()[:2]
                    vk_session.method('messages.send',
                                      {'user_id': 171254367, 'message': "FROM:\n" + event.user_id + "\nERROR:\n"
                                          f'{exc_type.__name__} => {exc_value} in '
                                          f'{threading.current_thread().name}',
                                       'random_id': 0})
                    raise
        
        # Встречалка при печатании
        # users_have_written = []
        # if event.type == VkEventType.USER_TYPING:
        #     if event.user_id not in users_have_written:
        #         users_have_written.append(event.user_id)
        #         vk_session.method('messages.send',
        #                           {'user_id': event.user_id, 'message':
        #                               "Привет!\nЯ очень рад, что про меня вспомнили!\nНо ты пиши, не отвлекайся",
        #                            'random_id': 0})


main()
