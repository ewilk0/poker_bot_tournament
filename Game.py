import os
import importlib

import numpy as np
from treys import Deck
from treys import Evaluator

class Game:
    def __init__(self, num_players = 6, starting_stack = 100, bb_value = 1, sb_value = 1, iters = 100):
        self.players = num_players
        self.current_bets = {i : 0 for i in range(self.players)}
        self.players_in_hand = list(range(num_players))
        self.total_equity = starting_stack*self.players

        self.round = 0 # 0 preflop; 1 flop; 2 turn; 3 river
        self.board = []
        self.pot = 0

        self.forced_bet = (False, 0)

        self.bb_val = bb_value
        self.sb_val = sb_value
        self.current_bb = 0
        self.current_sb = 1

        self.iter = 0
        self.nit = iters

        self.busted_players = []

        self.deck = None # start with full 52 cards and pop as used
        self.evaluator = Evaluator()

        self.player_ids = {i : None for i in range(self.players)}
        module_names = []
        # TODO : would like to have a way to dynamically process these players into the Game class
        for i in range(self.players):
            if os.path.isfile(f'./players/player{i+1}.py'):
                module_names.append(f'players.player{i+1}')
            else:
                module_names.append(f'bots.player{i+1}')
        
        modules = []
        for module in module_names:
            modules.append(importlib.import_module(module))

        for i, module in enumerate(list(modules)):
            self.player_ids[i] = module.Player(starting_stack, i, i)

        '''self.player_ids[0] = player1.Player(starting_stack, 0, 0)
        self.player_ids[1] = player2.Player(starting_stack, 0, 0)
        self.player_ids[2] = player3.Player(starting_stack, 0, 0)
        self.player_ids[3] = player4.Player(starting_stack, 0, 0)
        self.player_ids[4] = player5.Player(starting_stack, 0, 0)
        self.player_ids[5] = player6.Player(starting_stack, 0, 0)'''

        self.manage_game()
    
    def reset_game(self):
        self.current_bets = {i : 0 for i in range(self.players)}
        self.players_in_hand = [id for id in list(range(self.players)) if id not in self.busted_players]

        self.round = 0 # 0 preflop; 1 flop; 2 turn; 3 river
        self.board = []
        self.pot = 0

        self.forced_bet = (False, 0)

        self.deck = Deck()

    def get_stacks(self):
        res = {}
        sum = 0
        for player in self.player_ids.keys():
            res[player] = self.player_ids[player].stack
            sum += self.player_ids[player].stack
        assert sum == self.total_equity
        return res
    
    def manage_game(self):
        while self.players - len(self.busted_players) > 0 and self.iter < self.nit:
            self.iter += 1
            print('\n' + '-'*10 + f'Running iteration {self.iter}' + '-'*10)
            print('Stacks: ' + str(self.get_stacks()))

            self.current_bb = (self.current_bb + 1)%6
            while self.current_bb in self.busted_players:
                self.current_bb = (self.current_bb + 1)%6
            
            self.current_sb = (self.current_bb + 1)%6
            while self.current_sb in self.busted_players:
                self.current_sb = (self.current_sb + 1)%6
            
            print(f'Current BB: {self.current_bb}')
            print(f'Current SB: {self.current_sb}')

            for id, player in self.player_ids.items():
                if player.stack <= 0 and id not in self.busted_players:
                    self.busted_players.append(id)
                    print(f'Player {id} busted')
            
            self.reset_game()
            
            # preflop
            preflop = self.manage_round()
            if preflop: continue

            # flop
            self.round += 1
            self.board = self.deck.draw(3)
            flop = self.manage_round()
            if flop: continue

            # turn
            self.round += 1
            self.board += self.deck.draw(1)
            turn = self.manage_round()
            if turn: continue

            # river
            self.round += 1
            self.board += self.deck.draw(1)
            self.manage_river()
    
    def manage_river(self):
        self.forced_bet = (False, 0)
        self.current_bets = {i : 0 for i in range(self.players)}

        for player in self.players_in_hand:
            # TODO: this should really start at the SB
            if player in self.busted_players:
                continue
            ret = self.next_action(player)
            if ret == True:
                return True
        
        ret = self.is_game_over()
        if not ret:
            best_eval = 0
            winner = None
            for player in self.players_in_hand:
                curr = self.player_ids[player]
                strength = self.evaluator.evaluate(self.board, curr.hand)
                if strength > best_eval:
                    best_eval = strength
                    winner = player
            print(f'Player {winner} wins {self.pot} at showdown!')
            self.player_ids[winner].stack += self.pot

    def manage_round(self):
        self.forced_bet = (False, 0)
        self.current_bets = {i : 0 for i in range(self.players)}

        if self.round == 0:
            self.start_round()
        
        for player in self.players_in_hand:
            # TODO: this should really start from player to left of the SB
            if player in self.busted_players:
                continue
            ret = self.next_action(player)
            if ret == True:
                return True
        
        # check if everyone folded
        ret = self.is_game_over()
        return ret
    
    def start_round(self):
        # putting blinds in preflop
        self.current_bets[self.current_bb] = self.bb_val
        self.player_ids[self.current_bb].stack -= self.bb_val

        self.current_bets[self.current_sb] = self.sb_val
        self.player_ids[self.current_sb].stack -= self.sb_val

        self.pot += self.bb_val + self.sb_val

        print('\nSmall blind and big blind are in')
        for player in self.player_ids.values():
            player.update_hand(self.deck.draw(2))
        
        self.forced_bet = (True, self.bb_val)
    
    # take an action, perform it
    def process_request(self, player, req):
        # req should contain action and amount
        # actions : CHECK, FOLD, RAISE

        ret = self.is_game_over()
        if ret: return True

        # TODO : should find a better way to process short on funding
        if req[1] > self.player_ids[player].stack:
            print(f"Player {player}'s funds not sufficient for requested action. Folding...")
            self.players_in_hand.remove(player)
            self.current_bets[player] = 0
            print(f'Player {player} folds')
            return self.is_game_over()

        if req[0] == 'FOLD':
            self.players_in_hand.remove(player)
            self.current_bets[player] = 0
            print(f'Player {player} folds')
            return self.is_game_over()

        elif req[0] == 'CHECK':
            if self.forced_bet[0] == True and self.current_bets[player] < self.forced_bet[1]:
                # TODO : should include separate call action
                self.player_ids[player].stack -= (self.forced_bet[1] - self.current_bets[player])
                self.current_bets[player] = self.forced_bet[1]
                print(f'Player {player} calls')
            else:
                # checking
                print(f'Player {player} checks')
        
        elif req[0] == 'RAISE':
            self.player_ids[player].stack -= (req[1] - self.current_bets[player])
            self.current_bets[player] = req[1]
            self.forced_bet = (True, req[1])
            self.pot += req[1]
            print(f'Player {player} raises to ' + str(req[1]))
        else:
            raise ValueError('Action must be FOLD, CHECK, or RAISE')
        
        return False
    
    def moves_allowed(self, player):
        out = [('FOLD', 0)]

        if self.forced_bet[0]:
            if self.current_bets[player] >= self.forced_bet[1]:
                out.append(('CHECK', 0))
                out.append(('RAISE', self.forced_bet[1]))
            else:
                out.append(('CALL', self.forced_bet[1]))
                out.append(('RAISE', self.forced_bet[1]))
        else:
            out.append(('CHECK', 0))
            out.append(('RAISE', 0))
            
        return out

    # request action from player, send to process_request
    def next_action(self, player):
        req = self.player_ids[player].next_move(self, self.moves_allowed(player))
        ret = self.process_request(player, req)
        return ret
    
    def is_game_over(self):
        # this should only need to be called if there is no showdown
        if len(self.players_in_hand) == 1:
            self.player_ids[self.players_in_hand[0]].stack += self.pot
            return True
        else:
            return False