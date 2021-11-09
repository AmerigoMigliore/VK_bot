import pickle
from game_math import *
from game_luck import *
from game_pets import *
from save_games import save_games

game_math_class = GameMath()
game_luck_class = GameLuck()
game_pets_class = GamePets()

try:
    with open("game_pets.txt", "rb") as read_file:
        game_pets_class.load_me(pickle.load(read_file))
        read_file.close()
except FileNotFoundError:
    pass

save_games.game_pets_class = game_pets_class

