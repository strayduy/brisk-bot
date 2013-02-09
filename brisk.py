#!/usr/bin/env python2.7

# Standard libs
import json

# External libs
import requests

class Brisk(object):
    DEFAULT_HOST = 'http://www.briskchallenge.com'
    MAX_ARMIES_PER_ATTACK = 3

    def __init__(self, team_name, host=DEFAULT_HOST):
        self.team_name  = team_name
        self.url_root   = urljoin(host, '/v1/brisk/game')
        self.url_reward = urljoin(host, '/v1/brisk/reward.php')
        self.game_id    = None
        self.player_id  = None
        self.token      = None

    def join_game(self, game_id, bot_id):
        data = { 'join': True, 'team_name': self.team_name }
        response = requests.post(self.url_root, data=json.dumps(data))
        json_response = response.json()

        self.game_id   = json_response['game']
        self.player_id = json_response['player']
        self.token     = json_response['token']

        self.url_game   = urljoin(self.url_root, str(self.game_id))
        self.url_player = urljoin(self.url_game, 'player', str(self.player_id))

    def url_territory(self, territory_id):
        return urljoin(self.url_player, 'territory', str(territory_id))

    def get_game_state(self):
        response = requests.get(self.url_game)
        return response.json()

    def get_map_layout(self):
        params = { 'map' : True }
        response = requests.get(self.url_game, params=params)
        return response.json()

    def get_map_svg(self):
        params = { 'map' : 'svg' }
        response = requests.get(self.url_game, params=params)
        return response.text

    def get_player_status(self, check_turn=False):
        params = { 'check_turn' : True } if check_turn else {}
        response = requests.get(self.url_player, params=params)
        return response.json()

    def end_turn(self):
        data = { 'end_turn': True, 'token': self.token }
        response = requests.post(self.url_player, data=json.dumps(data))

    def get_history(self):
        history_url = urljoin(self.url_game, 'history')
        response = requests.get(self.url_game)
        return response.json()

    def attack(self, attacker_territory_id, defender_territory_id,
               num_attacker_armies):
        attack_url = self.url_territory(defender_territory_id)
        num_armies = min(num_attacker_armies, self.MAX_ARMIES_PER_ATTACK)
        data = { 'token'      : self.token,
                 'attacker'   : attacker_territory_id,
                 'num_armies' : num_armies }
        response = requests.post(attack_url, data=json.dumps(data))

    def place_armies(self, territory_id, num_armies):
        territory_url = self.url_territory(territory_id)
        data = { 'token'      : self.token,
                 'num_armies' : num_armies }
        response = requests.post(territory_url, data=json.dumps(data))

    def transfer_armies(self, from_territory_id, to_territory_id, num_armies):
        territory_url = self.url_territory(from_territory_id)
        data = { 'token'       : self.token,
                 'destination' : to_territory_id,
                 'num_armies'  : num_attacker_armies }
        response = requests.post(territory_url, data=json.dumps(data))

    def reward(self):
        data = { 'game'   : self.game_id,
                 'player' : self.player_id,
                 'token'  : self.token }
        response = requests.post(self.url_root, data=json.dumps(data))
        return response.text

# Joins given arguments into a url. Trailing but not leading slashes area
# stripped for each argument.
# http://stackoverflow.com/questions/1793261/how-to-join-components-of-a-path-when-you-are-constructing-a-url-in-python
def urljoin(*args):
    return '/'.join(map(lambda x: str(x).rstrip('/'), args))
