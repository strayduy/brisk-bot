#!/usr/bin/env python2.7

# Standard libs
import json

# External libs
import networkx as nx
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

    def join_game(self, token=None, game_id=None, no_bot=False):
        data = { 'join': True, 'team_name': self.team_name }
        if token:
            data['token'] = token
        if game_id:
            data['game'] = game_id
        if no_bot:
            data['no_bot'] = no_bot
        response = requests.post(self.url_root, data=json.dumps(data))
        json_response = response.json()

        self.game_id   = json_response['game']
        self.player_id = json_response['player']
        self.token     = json_response['token']

        self.url_game   = urljoin(self.url_root, str(self.game_id))

    def url_player(self, player_id):
        return urljoin(self.url_game, 'player', str(player_id))

    def url_territory(self, territory_id):
        return urljoin(self.url_game, 'player', str(self.player_id),
                       'territory', str(territory_id))

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

    def get_player_status(self, player_id=None, check_turn=False):
        player_id = player_id if player_id else self.player_id
        params = { 'check_turn' : True } if check_turn else {}
        response = requests.get(self.url_player(player_id), params=params)
        return response.json()

    def get_my_status(self):
        return self.get_player_status()

    def get_my_territories(self):
        my_status = self.get_my_status()
        my_territories = dict([(t['territory'], t['num_armies'])
                               for t in my_status['territories']])
        return my_territories

    def end_turn(self):
        data = { 'end_turn': True, 'token': self.token }
        response = requests.post(self.url_player(self.player_id), data=json.dumps(data))

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
        return response.json()

    def place_armies(self, territory_id, num_armies):
        territory_url = self.url_territory(territory_id)
        data = { 'token'      : self.token,
                 'num_armies' : num_armies }
        response = requests.post(territory_url, data=json.dumps(data))

    def transfer_armies(self, from_territory_id, to_territory_id, num_armies):
        territory_url = self.url_territory(from_territory_id)
        data = { 'token'       : self.token,
                 'destination' : to_territory_id,
                 'num_armies'  : num_armies }
        response = requests.post(territory_url, data=json.dumps(data))

    def reward(self):
        data = { 'game'   : self.game_id,
                 'player' : self.player_id,
                 'token'  : self.token }
        response = requests.post(self.url_root, data=json.dumps(data))
        return response.text

class BriskMap(object):
    def __init__(self, map_layout):
        self.continent_map = {}
        self.territory_map = {}
        self.territory_to_continent_map = {}
        self.graph = nx.Graph()

        for c in map_layout['continents']:
            c_id          = c['continent']
            c_name        = c.get('continent_name', None)
            c_bonus       = c.get('bonus', 0)
            c_territories = c.get('territories', [])

            continent = Continent(c_id, name=c_name, bonus=c_bonus, territories=c_territories)
            self.continent_map[c_id] = continent

            for territory_id in c_territories:
                self.territory_to_continent_map[territory_id] = c_id

        for t in map_layout['territories']:
            t_id   = t['territory']
            t_name = t.get('territory_name', None)
            adj_territories = t.get('adjacent_territories', [])
            continent_id = self.territory_to_continent_map[t_id]

            territory = Territory(t_id, continent_id, t_name)
            self.territory_map[t_id] = territory

            for adj_t_id in adj_territories:
                self.graph.add_edge(t_id, adj_t_id)

class Continent(object):
    def __init__(self, id, territories=[], bonus=0, name=None):
        self.id = id
        self.territories = territories
        self.bonus = bonus
        self.name = name if name else 'Continent %d' % (self.id)

class Territory(object):
    def __init__(self, id, continent_id, name=None):
        self.id = id
        self.continent_id = continent_id
        self.name = name if name else 'Territory %d' % (self.id)

# Joins given arguments into a url. Trailing but not leading slashes area
# stripped for each argument.
# http://stackoverflow.com/questions/1793261/how-to-join-components-of-a-path-when-you-are-constructing-a-url-in-python
def urljoin(*args):
    return '/'.join(map(lambda x: str(x).rstrip('/'), args))
