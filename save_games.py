import pickle


class SaveGames:
    game_pets_class = None

    def save_games(self):
        with open("game_pets.txt", "wb") as write_file:
            pickle.dump(self.game_pets_class.save_me(), write_file)
            write_file.close()


save_games = SaveGames()
