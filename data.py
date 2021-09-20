import json
import threading

# Все id пользователей, которые когда-либо использовали бота
users = None
# Классы, с которыми сейчас работают пользователи TODO: Сохранять в Json
# TODO: В файл с users добавить where_are_users и user_roles
where_are_users = {}

# Все ответы на запросы пользователей
answers = {}

# Статистика всех, кто сейчас играет в GameMath
game_math_stats = {}
# Рейтинг в GameMath
game_math_top = {}

# Таймер для сохранения всех данных в json
timer: threading.Timer

with open("users_id.json", "r") as read_file:
    if len(read_file.read()) == 0:
        users = list()
    else:
        read_file.seek(0)
        users = list(json.load(read_file))
    read_file.close()

with open("answers.json", "r", encoding='utf-8') as read_file:
    if len(read_file.read()) == 0:
        raise ValueError("Список ответов пуст!")
    else:
        read_file.seek(0)
        answers = json.load(read_file)
    read_file.close()

with open("gamers_active.json", "r", encoding='utf-8') as read_file:
    if len(json.load(read_file)) == 0:
        game_math_stats = {}
        game_math_top = {}
    else:
        read_file.seek(0)
        game_math_stats = dict(json.load(read_file).get('stats', {}))
        read_file.seek(0)
        game_math_top = dict(json.load(read_file).get('top', {}))
    read_file.close()


def set_next_save_all():
    global timer
    timer = threading.Timer(3600 * 3, save_all)
    timer.start()


def save_all(is_finally=False):
    global timer

    with open("users_id.json", "w") as write_file:
        json.dump(users, write_file)
        write_file.close()

    with open("answers.json", "w", encoding='utf-8') as write_file:
        json.dump(answers, write_file, ensure_ascii=False)
        write_file.close()

    with open("gamers_active.json", "w", encoding='utf-8') as write_file:
        json.dump({'stats': game_math_stats, 'top': game_math_top}, write_file, ensure_ascii=False)
        write_file.close()

    if not is_finally:
        set_next_save_all()
    else:
        if timer is not None:
            timer.cancel()

    print("\n\033[1m\033[32m\033[40m"
          "All data has been saved!"
          "\033[0m")


set_next_save_all()
