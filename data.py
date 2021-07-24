import json
import threading

"""ID всех, кто сейчас играет в GameMath"""
game_math_stats = {}
game_math_top = {}

with open("gamers_active.json", "r", encoding='utf-8') as read_file:
    if len(json.load(read_file)) == 0:
        game_math_stats = {}
        game_math_top = {}

    else:
        read_file.seek(0)
        game_math_stats = dict(json.load(read_file).get('stats'))
        read_file.seek(0)
        game_math_top = dict(json.load(read_file).get('top'))
        if game_math_stats is None:
            game_math_stats = {}
        if game_math_top is None:
            game_math_top = {}

    read_file.close()


def save_all():
    with open("gamers_active.json", "w") as write_file:
        json.dump({'stats': game_math_stats, 'top': game_math_top}, write_file)
        write_file.close()
    print("All data has been saved!")
    threading.Timer(60, save_all).start()


threading.Timer(60, save_all).start()
