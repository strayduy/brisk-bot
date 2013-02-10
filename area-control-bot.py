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
        self.brisk         = brisk
        self.brisk_map     = None
        self.other_players = []

    def start_game(self, game_id=None, no_bot=False):
        # Join the game
        self.brisk.join_game(token=BRISK_TOKEN, game_id=game_id, no_bot=no_bot)

        # Initialize our representation of the map
        map_layout = self.brisk.get_map_layout()
        self.brisk_map = BriskMap(map_layout)

        game_state = self.brisk.get_game_state()
        print game_state

        # Keep playing until we have a winner
        while not game_state['winner']:
            self.update_map()

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

    def update_map(self):
        all_territories = self.brisk.get_all_territories().get('territories', [])

        if all_territories:
            my_territories = {}
            enemy_territories = {}

            for territory in all_territories:
                if territory['player'] == self.brisk.player_id:
                    my_territories[territory['territory']] = territory['num_armies']
                else:
                    enemy_territories[territory['territory']] = territory['num_armies']

            self.brisk_map.my_territories = my_territories
            self.brisk_map.enemy_territories = enemy_territories

    def randomly_place_reserves(self, my_status):
        num_reserves = my_status['num_reserves']

        # Retrieve a list of territory IDs that belong to us
        my_territories = [t['territory'] for t in my_status['territories']]

        # Randomly distribute our reserves across our territories
        for i in xrange(num_reserves):
            random_territory = random.choice(my_territories)
            self.brisk.place_armies(random_territory, 1)

    def attack_everything(self):
        self.update_map()

        # Queue of territories from which we can potentially attack
        attack_queue = self.brisk_map.my_territories.keys()

        while attack_queue:
            my_territory = attack_queue.pop(0)
            adj_territories = self.brisk_map.graph[my_territory]

            # For each of our territories, check whether the adjacent
            # territories can be captured
            for adj_territory in adj_territories:
                self.update_map()
                my_territories = self.brisk_map.my_territories
                num_attacking_armies = my_territories[my_territory]

                # If we have enough armies to attack from this territory
                if num_attacking_armies >= 2:
                    # If this is an enemy territory
                    if adj_territory not in my_territories:
                        num_defending_armies = self.brisk_map.enemy_territories[adj_territory]

                        # Check if the odds are in our favor
                        # If they're not, don't try attacking
                        if ((num_attacking_armies <= 4 and num_defending_armies >= num_attacking_armies)
                            or (num_attacking_armies > 4 and num_defending_armies > num_attacking_armies)):
                            continue

                        # Keep attacking it until:
                        # 1. We capture it
                        # 2. We exhaust our attacking army
                        keepAttackingThisTerritory = True
                        while keepAttackingThisTerritory:
                            result = self.brisk.attack(my_territory,
                                                       adj_territory,
                                                       num_attacking_armies - 1)
                            num_attacking_armies = result['attacker_territory_armies_left']
                            num_defending_armies = result['defender_territory_armies_left']

                            # If we successfully captured the territory
                            if result['defender_territory_captured']:
                                # If we have leftover armies, move them into
                                # the newly captured territory
                                if num_attacking_armies > 1:
                                    self.brisk.transfer_armies(my_territory,
                                                               adj_territory,
                                                               num_attacking_armies)

                                    attack_queue.append(adj_territory)
                                keepAttackingThisTerritory = False
                            # If we no longer have enough armies to attack
                            elif num_attacking_armies < 2:
                                keepAttackingThisTerritory = False

def main():
    brisk = Brisk(TEAM_NAME)
    area_control_bot = AreaControlBot(brisk)
    area_control_bot.start_game()

if __name__ == '__main__':
    main()
