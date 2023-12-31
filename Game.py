import os
import importlib

import numpy as np
from treys import Deck
from treys import Evaluator
from treys import Card

class Game:
    def __init__(self, players, starting_stack = 100, bb_value = 2, sb_value = 1, iters = 100):
        while len(players) < 6:
            players.append(f'Player{len(players) + 1}')
        self.players = len(players)
        self.player_names = players
        self.current_bets = {i : 0 for i in range(self.players)}
        self.players_in_hand = list(range(self.players))
        self.total_equity = starting_stack*self.players

        self.round = 0 # 0 preflop; 1 flop; 2 turn; 3 river
        self.board = []
        self.pot = 0

        self.forced_bet = (False, 0)
        self.players_checked = set()

        # store values of BB and SB
        self.bb_val = bb_value
        self.sb_val = sb_value
        # store BB and SB positions
        self.current_bb = 0
        self.current_sb = 1

        self.iter = 0
        self.nit = iters

        self.busted_players = []

        self.deck = Deck() # start with full 52 cards and pop as used
        self.evaluator = Evaluator()

        # load player modules into the game instance
        self.player_ids = {i : None for i in range(self.players)}
        module_names = []
        for i in range(self.players):
            if os.path.isfile(f'./players/player{i+1}.py'):
                module_names.append(f'players.player{i+1}')
            else:
                module_names.append(f'bots.player{i+1}')
        
        modules = []
        for module in module_names:
            modules.append(importlib.import_module(module))
        
        # store player IDs
        for i, module in enumerate(list(modules)):
            self.player_ids[i] = module.Player(starting_stack, i, i)

        # game history for post-game anaysis
        self.game_history = []
    
    # return player names
    def get_players(self):
        return self.player_names, [self.player_ids[id].stack for id in range(self.players)]
    
    # return player names of BB and SB
    def get_bb_and_sb(self):
        return self.player_names[self.current_bb], self.player_names[self.current_sb]

    # return pretty hands of players and the bets on the table
    def get_player_hands_and_bet(self):
        suit_map = {1 : 's', 2 : 'h', 4 : 'd', 8 : 'c'}
        hands = []
        for id in self.player_ids:
            curr_hand = []
            for card in self.player_ids[id].hand:
                curr_hand.append(Card.int_to_pretty_str(card).strip('[').strip(']'))
            hands.append(curr_hand)
        
        bets = [self.current_bets[id] for id in range(self.players)]
        for i in range(self.players):
            if i not in self.players_in_hand:
                bets[i] = 'FOLD'
            if i in self.busted_players:
                bets[i] = 'BUSTED'
        return hands, bets

    # check is the current round has ended
    def is_round_over(self):
        # either all bets are 0 except for 1 or everyone has checked
        bets = len([bet for bet in self.current_bets.values() if bet != 0])
        return bets == 1 or len(self.players_checked) >= len(self.players_in_hand)

    # return the cards on the board
    def get_board(self):
        board = []
        suit_map = {1 : 's', 2 : 'h', 4 : 'd', 8 : 'c'}
        for card in self.board:
            board.append(Card.int_to_pretty_str(card).strip('[').strip(']'))
        # board = [Card.int_to_pretty_str(self.board[card]) for card in range(len(self.board))]
        while len(board) < 5:
            board.append('')
        return board

    # reset the attributes after each round
    def reset_game(self):
        self.current_bets = {i : 0 for i in range(self.players)}
        self.players_in_hand = [id for id in list(range(self.players)) if id not in self.busted_players]

        self.round = 0 # 0 preflop; 1 flop; 2 turn; 3 river
        self.board = []
        self.pot = 0

        self.players_checked = set()

        self.forced_bet = (False, 0)

        self.deck = Deck()
        self.iter += 1

    # return everyone's stacks
    def get_stacks(self):
        res = {}
        sum = 0
        for player in self.player_ids.keys():
            res[player] = self.player_ids[player].stack
            sum += self.player_ids[player].stack
        # assert sum == self.total_equity, 'Sum of stacks not equal to total equity in game'
        return res
    
    # send an update of the current game state
    def update(self):
        if self.round == 0:
            print('\n' + '-'*10 + f'Running iteration {self.iter}' + '-'*10)
            print('Stacks: ' + str(self.get_stacks()))

            for id, player in self.player_ids.items():
                if player.stack <= self.bb_val and id not in self.busted_players:  # If a player has less than bb_val, they can't play
                    self.busted_players.append(id)

            self.current_bb = (self.current_bb + 1)%6
            while self.current_bb in self.busted_players:
                self.current_bb = (self.current_bb + 1)%6
            
            self.current_sb = (self.current_bb + 1)%6
            while self.current_sb in self.busted_players:
                self.current_sb = (self.current_sb + 1)%6

            if self.current_bb == self.current_sb:
                print('GAME OVER / ERROR; bb = sb')

            # preflop
            round_over = self.manage_round()
            self.round += 1
            if round_over:
                self.reset_game()
        elif self.round == 1:
            # flop
            self.board = self.deck.draw(3)  
            round_over = self.manage_round()
            self.round += 1
            if round_over:
                self.reset_game()
        elif self.round == 2:
            # turn
            self.board += self.deck.draw(1) 
            round_over = self.manage_round()
            self.round += 1
            if round_over:
                self.reset_game()
        elif self.round == 3:
            # river
            self.round += 1
            self.board += self.deck.draw(1)
            self.manage_river()
        else:
            self.reset_game()
    
    # special routine to manage river bets and logic
    def manage_river(self):
        self.players_checked = set()
        self.forced_bet = (False, 0)
        self.current_bets = {i : 0 for i in range(self.players)}

        while not self.is_round_over():
            for player in self.players_in_hand:
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
        
        self.game_history.append(self.get_stacks())

    # engine to manage round game other than the river
    def manage_round(self):
        self.players_checked = set()
        self.forced_bet = (False, 0)
        self.current_bets = {i : 0 for i in range(self.players)}

        if self.round == 0:
            self.start_round()
        
        while not self.is_round_over():
            for player in self.players_in_hand:
                if player in self.busted_players:
                    continue
                ret = self.next_action(player)
                if ret == True:
                    return True
        
        # check if everyone folded
        ret = self.is_game_over()
        return ret
    
    # called to start preflop action
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
    
    # take a requested action, perform it if possible
    def process_request(self, player, req):
        # req should contain action and amount
        # actions : CHECK, CALL, FOLD, RAISE

        ret = self.is_game_over()
        if ret: return True

        # check for illegal actions
        if req[1] > self.player_ids[player].stack:
            print(f"Player {player}'s funds not sufficient for requested action. Folding...")
            self.players_in_hand.remove(player)
            self.current_bets[player] = 0
            print(f'Player {player} folds')
            return self.is_game_over()

        if req[0] == 'RAISE' and req[1] == self.current_bets[player]:
            # this is a check
            if self.forced_bet[0] == True and self.current_bets[player] < self.forced_bet[1]:
                self.player_ids[player].stack -= (self.forced_bet[1] - self.current_bets[player])
                self.current_bets[player] = self.forced_bet[1]
                print(f'Player {player} calls')
                self.players_checked.add(player)
                return False
            else:
                # checking
                self.players_checked.add(player)
                print(f'Player {player} checks')
                return False

        if req[0] == 'FOLD':
            self.players_in_hand.remove(player)
            self.current_bets[player] = 0
            print(f'Player {player} folds')
            return self.is_game_over()

        elif req[0] == 'CHECK':
            self.players_checked.add(player)
            if self.forced_bet[0] == True and self.current_bets[player] < self.forced_bet[1]:
                self.player_ids[player].stack -= (self.forced_bet[1] - self.current_bets[player])
                self.current_bets[player] = self.forced_bet[1]
                print(f'Player {player} calls')
                return False
            else:
                # checking
                print(f'Player {player} checks')
                return False
        
        elif req[0] == 'RAISE':
            try:
                self.players_checked.remove(player)
            except:
                pass
            self.player_ids[player].stack -= (req[1] - self.current_bets[player])
            self.current_bets[player] = req[1]
            self.forced_bet = (True, req[1])
            self.pot += req[1]
            print(f'Player {player} raises to ' + str(req[1]))
        else:
            raise ValueError('Action must be FOLD, CHECK, or RAISE')
        
        return False
    
    # return a list of the moves a given player can make
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
    
    # check if the game is over
    def is_game_over(self):
        # this should only need to be called if there is no showdown
        if len(self.players_in_hand) == 1:
            self.player_ids[self.players_in_hand[0]].stack += self.pot
            return True
        else:
            return False