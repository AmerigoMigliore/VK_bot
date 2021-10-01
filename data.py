import json
import threading
import sqlite3
from transliterate.discover import autodiscover
from transliterate.base import TranslitLanguagePack, registry

# Вся информация о пользователях
# id: role, class, method, args
users_info = {}
roles = {'user': 0, 'moderator': 1, 'admin': 2, 'master': 3}

# Все ответы на запросы пользователей
answers = {}
# Связь с базой данных
db_connect = None
db_cursor = None

# Статистика всех, кто сейчас играет в GameMath
game_math_stats = {}
# Рейтинг в GameMath
game_math_top = {}

# Таймер для сохранения всех данных в json
timer: threading.Timer

# Логи для обработки данных по синонимичному распознаванию запросов
synonyms_stats = []


def change_class(user_id, new_class):
    users_info[user_id]['class'] = new_class
    users_info[user_id]['method'] = None
    users_info[user_id]['args'] = None


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
db_cursor.executemany('INSERT OR IGNORE INTO synonyms_global VALUES(?, ?);', ((word, word) for word in answers.get('global').keys()))
db_connect.commit()

db_cursor.execute('CREATE TABLE IF NOT EXISTS synonyms_stats(phrase text PRIMARY KEY, request text, type text, rate real)')
db_connect.commit()

db_cursor.execute('CREATE TABLE IF NOT EXISTS users_info(id text PRIMARY KEY, role text, class text, method text, args text)')
db_connect.commit()
try:
    db_cursor.execute('ALTER TABLE users_info ADD COLUMN balance REAL DEFAULT 0;')
    db_connect.commit()
except Exception:
    pass
db_cursor.execute('SELECT id, role, class, method, args, balance FROM users_info')
users_info = {x[0]: {'role': x[1], 'class': x[2], 'method': x[3], 'args': x[4], 'balance': x[5]} for x in db_cursor.fetchall()}  # [(id, role, class, method, args, balance), (,,,,), ...]


def set_next_save_all():
    global timer
    timer = threading.Timer(3600 * 3, save_all)
    timer.start()


def save_all(is_finally=False):
    global timer

    db_connect_save = sqlite3.connect('all_data.db')
    db_cursor_save = db_connect_save.cursor()

    if users_info != {}:
        db_cursor_save.executemany('INSERT OR REPLACE INTO users_info(id, role, class, method, args, balance) VALUES(?, ?, ?, ?, ?, ?);',
                                   [(item[0], item[1].get('role'), item[1].get('class'), item[1].get('method'), item[1].get('args'), item[1].get('balance'))
                                    for item in users_info.items()])

    if synonyms_stats:
        db_cursor_save.executemany('INSERT OR IGNORE INTO synonyms_stats(phrase, request, type, rate) VALUES(?, ?, ?, ?);',
                                   synonyms_stats)
        synonyms_stats.clear()

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

    db_connect_save.commit()
    db_cursor_save.close()
    db_connect_save.close()

    print("\n\033[1m\033[32m\033[40m"
          "All data has been saved!"
          "\033[0m")


set_next_save_all()
