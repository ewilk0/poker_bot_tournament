from treys import Evaluator

class Player:
    def __init__(self, stack : int, pos : int, player_id : int):
        self.stack = stack
        self.hand = []
        self.position = pos
        self.player_num = player_id
        self.evaluator = Evaluator()
    
    def update_hand(self, new_hand : list):
        self.hand = new_hand
    
    def next_move(self, game_state : dict, moves_available : list):
        '''
        game_state attributes:
            .players : number of players at the table, busted or not
            .current_bets : current bets on the table
            .players_in_hand : IDs of players currently in the hand

            .round : 0 preflop; 1 flop; 2 turn; 3 river
            .board : cards currently on the table
            .pot : size of pot

            .forced_bet : 2-tuple of whether a bet must be made and, if so, the amount

            .bb_val : value of the big blind in this game
            .sb_val : value of the small blind in this game
            .current_bb : player who is currently in the big blind position

            .iter : iteration the game is on
            .nit : total number of iterations in the game

            .busted_players : list of players who have busted
        '''
        moves_available = [move[0] for move in moves_available]
        if game_state.round >= 1 and self.evaluator.evaluate(game_state.board, self.hand) > 400 and 'RAISE' in moves_available:
            return ('RAISE', 6)
        elif 'CHECK' in moves_available:
            return ('CHECK', 0)
        else:
            return ('FOLD', 0)