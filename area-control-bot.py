#!/usr/bin/env python2.7

# Standard libs
from collections import defaultdict
import random
import time

# External libs
from brisk import Brisk, BriskMap, Continent, Territory

DEBUG = False
GAME_IDS = [1662058487]

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
                num_reserves = my_status['num_reserves']
                self.place_reserves_based_on_need(num_reserves)

                self.attack_everything()

                if not self.move_backline_armies():
                    # Once we've done everything we want to do, explicitly end our
                    # turn
                    self.brisk.end_turn()
            else:
                print "not my turn"

            # Sleep before polling the server again
            time.sleep(POLL_INTERVAL_IN_SECONDS)

            # Update the game state before looping back up
            game_state = self.brisk.get_game_state()

    def update_map(self):
        all_territories = self.brisk.get_all_territories().get('territories', [])

        if all_territories:
            my_territories = {}
            enemy_territories = {}
            enemy_territories_per_continent = defaultdict(int)

            for territory in all_territories:
                territory_id = territory['territory']
                if territory['player'] == self.brisk.player_id:
                    my_territories[territory_id] = territory['num_armies']
                else:
                    enemy_territories[territory_id] = territory['num_armies']
                    continent_id = self.brisk_map.territory_map[territory_id].continent_id
                    enemy_territories_per_continent[continent_id] += 1

            self.brisk_map.my_territories = my_territories
            self.brisk_map.enemy_territories = enemy_territories
            self.brisk_map.enemy_territories_per_continent = enemy_territories_per_continent

    def place_reserves_based_on_need(self, num_reserves):
        print "placing reserves..."

        # Continents sorted by largest bonus
        continents = sorted(self.brisk_map.continent_map.values(), key=lambda x: x.bonus, reverse=True)

        my_territories = self.brisk_map.my_territories
        enemy_territories = self.brisk_map.enemy_territories
        enemy_territories_per_continent = self.brisk_map.enemy_territories_per_continent

        # Check whether the enemy controls an entire continent
        # If they do, put all our reserves at a border (if possible)
        for continent in continents:
            if enemy_territories_per_continent.get(continent.id, -1) == continent.size:
                for territory in continent.territories:
                    adj_territories = self.brisk_map.graph[territory]
                    for adj_territory in adj_territories:
                        if adj_territory in my_territories:
                            self.brisk.place_armies(adj_territory, num_reserves)
                            print "placing reserves to retake continent"
                            return

        # Check whether we're one or two territories away from securing our
        # own continent
        # If we are, put all our reserves within the continent (if possible)
        for continent in continents:
            if enemy_territories_per_continent[continent.id] > 0 and enemy_territories_per_continent[continent.id] <= 2:
                for territory in continent.territories:
                    adj_territories = self.brisk_map.graph[territory]
                    for adj_territory in adj_territories:
                        if adj_territory in my_territories:
                            self.brisk.place_armies(adj_territory, num_reserves)
                            print "placing reserves to secure continent"
                            return

        territories_to_supply = []

        # Determine which territories need new units the most, based on
        # surrounding enemy armies
        for territory in my_territories:
            adj_territories = self.brisk_map.graph[territory]
            army_need = 0
            for adj_territory in adj_territories:
                army_need += my_territories.get(adj_territory, 0)
                army_need -= enemy_territories.get(adj_territory, 0)
            territories_to_supply.append((territory, army_need))

        # Sort territories based on need
        territories_to_supply.sort(key=lambda x: x[1])

        # Distribute new armies to territories that need them the most
        for territory, need in territories_to_supply:
            if num_reserves <= 0:
                break

            if need < 0:
                num_reserves_to_place = min(num_reserves, need * -1)
            else:
                num_reserves_to_place = 1

            self.brisk.place_armies(territory, num_reserves_to_place)
            num_reserves -= num_reserves_to_place
            print "placing reserves based on need"

        # Randomly distribute any remaining reserves across our territories
        territory_ids = my_territories.keys()
        for i in xrange(num_reserves):
            random_territory = random.choice(my_territory_ids)
            self.brisk.place_armies(random_territory, 1)
            print "placing reserves randomly"

    def attack_everything(self):
        print "attacking..."

        self.update_map()

        # Queue of territories from which we can potentially attack
        attack_queue = self.brisk_map.my_territories.keys()

        while attack_queue:
            my_territory = attack_queue.pop(0)
            adj_territories = self.brisk_map.graph[my_territory]

            # For each of our territories, check whether the adjacent
            # territories can be captured
            for adj_territory in adj_territories:
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
                            print "attacking %d from %d with %d armies" % (adj_territory, my_territory, num_attacking_armies - 1)
                            result = self.brisk.attack(my_territory,
                                                       adj_territory,
                                                       num_attacking_armies - 1)
                            num_attacking_armies = result.get('attacker_territory_armies_left', 0)
                            num_defending_armies = result.get('defender_territory_armies_left', 0)

                            # If we successfully captured the territory
                            if result['defender_territory_captured']:
                                # If we have leftover armies, move them into
                                # the newly captured territory
                                if num_attacking_armies > 1:
                                    print "transferring %d armies from %d to %d" % (num_attacking_armies, my_territory, adj_territory)
                                    self.brisk.transfer_armies(my_territory,
                                                               adj_territory,
                                                               num_attacking_armies - 1)

                                    attack_queue.append(adj_territory)
                                keepAttackingThisTerritory = False
                            # If we no longer have enough armies to attack
                            elif num_attacking_armies < 2:
                                keepAttackingThisTerritory = False

                        self.update_map()

    def move_backline_armies(self):
        self.update_map()

        my_territories = self.brisk_map.my_territories
        for territory in my_territories:
            adj_territories = self.brisk_map.graph[territory]
            adj_enemy_territories = [t for t in adj_territories if t not in my_territories]
            if not adj_enemy_territories:
                num_armies = my_territories[territory]
                if num_armies > 1:
                    random_territory = random.choice(adj_territories.keys())
                    self.brisk.transfer_armies(territory,
                                               random_territory,
                                               num_armies - 1)
                    return True

        return False

def main():
    if DEBUG:
        brisk = Brisk(TEAM_NAME)
        area_control_bot = AreaControlBot(brisk)
        area_control_bot.start_game(game_id=None)
    else:
        for game_id in GAME_IDS:
            brisk = Brisk(TEAM_NAME)
            area_control_bot = AreaControlBot(brisk)
            area_control_bot.start_game(game_id=game_id, no_bot=True)

if __name__ == '__main__':
    main()
