#!/usr/bin/env python2.7

# Standard libs
import random
import time

# External libs
from brisk import Brisk

class AggroBot(object):
    def __init__(self, brisk):
        self.brisk = brisk

    def start_game(self):
        self.brisk.join_game(False, 1)

        map_layout = self.brisk.get_map_layout()
        self.adjacent_territory_map = dict([
            (t['territory'], t['adjacent_territories'])
            for t in map_layout['territories']
        ])

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

                self.attack_everything(my_status)

                # Once we've done everything we want to do, explicitly end our
                # turn
                self.brisk.end_turn()

            # Sleep before polling the server again
            time.sleep(1)

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

    def attack_everything(self, my_status):
        # Create a map of territory ID -> num armies for each of our
        # territories
        my_territories = dict([(t['territory'], t['num_armies'])
                               for t in my_status['territories']])

        # For each of our territories that has at least one army,
        # attack each neighboring enemy territory
        for territory, num_armies in my_territories.iteritems():
            if num_armies > 1:
                adj_territories = self.adjacent_territory_map[territory]
                for adj_territory in adj_territories:
                    if adj_territory not in my_territories:
                        self.brisk.attack(territory,
                                          adj_territory,
                                          num_armies - 1)

def main():
    brisk = Brisk('test team name')
    aggro_bot = AggroBot(brisk)
    aggro_bot.start_game()

if __name__ == '__main__':
    main()
