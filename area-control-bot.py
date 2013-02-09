#!/usr/bin/env python2.7

# Standard libs
import random
import time

# External libs
from brisk import Brisk, BriskMap, Continent, Territory

# Constants
TEAM_NAME = 'KangarooUprising'
BRISK_TOKEN = '962b3ddf0266ab0cec6ee3b399da2a54659d5ada'
POLL_INTERVAL_IN_SECONDS = 1

class AreaControlBot(object):
    def __init__(self, brisk):
        self.brisk     = brisk
        self.brisk_map = None

    def start_game(self, game_id=None, no_bot=False):
        self.brisk.join_game(token=BRISK_TOKEN, game_id=game_id, no_bot=no_bot)

        map_layout = self.brisk.get_map_layout()
        self.brisk_map = BriskMap(map_layout)

        game_state = self.brisk.get_game_state()
        print game_state

        # Keep playing until we have a winner
        while not game_state['winner']:
            my_status = self.brisk.get_player_status()

            # If it's our turn, do stuff
            isMyTurn = my_status['current_turn']
            if isMyTurn:
                # Place reserve armies
                self.randomly_place_reserves(my_status)

                self.attack_everything()

                # Once we've done everything we want to do, explicitly end our
                # turn
                self.brisk.end_turn()

            # Sleep before polling the server again
            time.sleep(POLL_INTERVAL_IN_SECONDS)

            # Update the game state before looping back up
            game_state = self.brisk.get_game_state()

    def randomly_place_reserves(self, my_status):
        num_reserves = my_status['num_reserves']

        # Retrieve a list of territory IDs that belong to us
        my_territories = [t['territory'] for t in my_status['territories']]

        # Randomly distribute our reserves across our territories
        for i in xrange(num_reserves):
            random_territory = random.choice(my_territories)
            self.brisk.place_armies(random_territory, 1)

    def attack_everything(self):
        attack_queue = self.brisk.get_my_territories().keys()

        while attack_queue:
            my_territory = attack_queue.pop(0)
            adj_territories = self.brisk_map.graph[my_territory]

            for adj_territory in adj_territories:
                my_territories = self.brisk.get_my_territories()
                num_armies = my_territories[my_territory]

                if num_armies >= 2:
                    if adj_territory not in my_territories:
                        keepAttackingThisTerritory = True
                        while keepAttackingThisTerritory:
                            result = self.brisk.attack(my_territory,
                                                       adj_territory,
                                                       num_armies - 1)
                            num_armies = result['attacker_territory_armies_left']

                            # If we successfully captured the territory,
                            if result['defender_territory_captured']:
                                if num_armies > 1:
                                    self.brisk.transfer_armies(my_territory,
                                                               adj_territory,
                                                               num_armies - 1)
                                keepAttackingThisTerritory = False
                            elif num_armies < 2:
                                keepAttackingThisTerritory = False

def main():
    brisk = Brisk(TEAM_NAME)
    area_control_bot = AreaControlBot(brisk)
    area_control_bot.start_game()

if __name__ == '__main__':
    main()
