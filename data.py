import json
import pickle
import datetime
import sqlite3
import threading

from transliterate.discover import autodiscover
from transliterate.base import TranslitLanguagePack, registry
from keyboard import get_text_button
from save_games import save_games

# Настройка часового пояса
offset = datetime.timedelta(hours=3)
tz = datetime.timezone(offset, name='МСК')

# Вся информация о пользователях
# id: role, class, method, args
users_info = {}
roles = {'user': 0, 'moderator': 1, 'admin': 2, 'master': 3}

# Все ответы на запросы пользователей
answers = {}
# Главная клавиатура
main_keyboard = str(json.dumps({
    "one_time": False,
    "buttons": [
        [get_text_button('!Все запросы', 'primary'), get_text_button('!Все команды', 'primary')],
        [get_text_button('!Играть', 'positive')]
    ]
}, ensure_ascii=False))
# Связь с базой данных
db_connect = None
db_cursor = None

# Статистика всех, кто сейчас играет в GameMath
game_math_stats = {}
# Рейтинг в GameMath
game_math_top = {}

# # Таймер для сохранения всех данных в json
# timer: threading.Timer

# Логи для обработки данных по синонимичному распознаванию запросов
synonyms_stats = []


def change_users_info(user_id, new_class=None, new_method=None, new_args=None):
    if new_class is not None:
        users_info[user_id]['class'] = new_class
    users_info[user_id]['method'] = new_method
    users_info[user_id]['args'] = new_args


def add_new_user(user_id):
    users_info[str(user_id)] = {'role': 'user', 'class': 'autoresponder', 'method': None, 'args': None, 'balance': 0,
                                'lock': threading.Lock()}


# Регистрация транслитерации по раскладке клавиатуры
autodiscover()


class QWERTYLanguagePack(TranslitLanguagePack):
    language_code = "qwerty"
    language_name = "KeyBoard"
    mapping = (
        'QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>?qwertyuiop[]asdfghjkl;\'zxcvbnm,./',
        'ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,йцукенгшщзхъфывапролджэячсмитьбю.',
    )


registry.register(QWERTYLanguagePack)


# Загрузки данных из файлов
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

# Настройка базы данных синонимов для ответов
db_connect = sqlite3.connect('all_data.db')
db_cursor = db_connect.cursor()
db_cursor.execute('CREATE TABLE IF NOT EXISTS synonyms_global(word text PRIMARY KEY, request text);')
db_cursor.executemany('INSERT OR IGNORE INTO synonyms_global VALUES(?, ?);',
                      ((word, word) for word in answers.get('global').keys()))
db_connect.commit()

db_cursor.execute(
    'CREATE TABLE IF NOT EXISTS synonyms_stats(phrase text PRIMARY KEY, request text, type text, rate real)')
db_connect.commit()

db_cursor.execute(
    'CREATE TABLE IF NOT EXISTS users_info(id text PRIMARY KEY, role text, class text, method text, args text, balance REAL DEFAULT 0)')
db_connect.commit()

db_cursor.execute('SELECT id, role, class, method, args, balance FROM users_info')
users_info = {x[0]: {'role': x[1], 'class': x[2], 'method': x[3], 'args': pickle.loads(x[4]), 'balance': x[5], 'lock': threading.Lock()} for x in
              db_cursor.fetchall()}  # [(id, role, class, method, args, balance), (,,,,,), ...]


# def set_next_save_all():
#     global timer
#     timer = threading.Timer(30, save_all)
#     timer.start()


def save_all():  # (is_finally=False):
    # global timer

    db_connect_save = sqlite3.connect('all_data.db')
    db_cursor_save = db_connect_save.cursor()

    if users_info != {}:
        db_cursor_save.executemany(
            'INSERT OR REPLACE INTO users_info(id, role, class, method, args, balance) VALUES(?, ?, ?, ?, ?, ?);',
            [(item[0], item[1].get('role'), item[1].get('class'), item[1].get('method'), pickle.dumps(item[1].get('args')),
              item[1].get('balance'))
             for item in users_info.items()])

    if synonyms_stats:
        db_cursor_save.executemany(
            'INSERT OR IGNORE INTO synonyms_stats(phrase, request, type, rate) VALUES(?, ?, ?, ?);',
            synonyms_stats)
        synonyms_stats.clear()

    with open("answers.json", "w", encoding='utf-8') as write_file:
        json.dump(answers, write_file, ensure_ascii=False)
        write_file.close()

    with open("gamers_active.json", "w", encoding='utf-8') as write_file:
        json.dump({'stats': game_math_stats, 'top': game_math_top}, write_file, ensure_ascii=False)
        write_file.close()

    save_games.save_games()

    # if not is_finally:
    #     set_next_save_all()
    # else:
    #     if timer is not None:
    #         timer.cancel()

    db_connect_save.commit()
    db_cursor_save.close()
    db_connect_save.close()

    print("\n\033[1m\033[32m\033[40m"
          "All data has been saved!"
          "\033[0m")


# set_next_save_all()
