import os
from flask import Flask, flash, request, redirect, render_template
from flask_cors import CORS
from Game import Game

path = os.getcwd()
app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(path, 'players')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CORS(app)

playerNextToMove = 0
NUM_PLAYERS = 0
active_games = {}
pre_game_lobby = {}
game_id = 56396


@app.route('/poker-table')
def poker_table():
    return render_template('/pokerTable.html')

@app.route('/')
def index():
    return render_template('/index.html')

@app.route('/api/createLobby', methods=['POST'])
def create_lobby():
    global game_id
    if 'script' not in request.files:
        return {'msg': len(request.files)}
    python_file = request.files['script']        
    if python_file.filename == '':
        return {"msg": "no file selected"}
    playerName = request.form.get('name')

    player_id = f'player1'
    python_script_filename = f'{player_id}.py'
    python_file.save(os.path.join(app.config['UPLOAD_FOLDER'], python_script_filename))
    
    pre_game_lobby[game_id] = [playerName]
    game_id += 1

    return {'code': str(game_id - 1)}


@app.route('/api/joinLobby', methods=['POST'])
def join_lobby():
    global game_id
    if 'script' not in request.files:
        return {'msg': len(request.files)}
    python_file = request.files['script']
    if python_file.filename == '':
        return {"msg": "no file selected"}
    playerName = request.form.get('name')
    game_to_join_id = int(request.form.get('game_id'))
    
    if int(game_to_join_id) not in pre_game_lobby:
        return {'msg': 'no such game exists'}

    num_players = len(pre_game_lobby[game_to_join_id])
    if num_players >= 6:
        return {'msg': 'Too many players, only up to 6 can join'}

    player_id = f'player{num_players + 1}'
    python_script_filename = f'{player_id}.py'
    python_file.save(os.path.join(app.config['UPLOAD_FOLDER'], python_script_filename))
    
    pre_game_lobby[game_to_join_id].append(playerName)
    game_id += 1

    return {'msg': 'Joined game'}


@app.route('/api/startGame', methods=['POST'])
def start_lobby():
    game_to_join_id = request.form.get('game_id')
    if game_to_join_id not in pre_game_lobby:
        return {'msg': 'no such game exists'}
    big_blind = request.form.get('big_blind')
    small_blind = request.form.get('small_blind')
    num_iters = request.form.get('num_iters')

    active_games[game_id] = Game(pre_game_lobby[game_id], big_blind, small_blind, num_iters)

    return {'msg': 'Game Successfully created'}


@app.route('/api/getPlayers')
def get_players():
    game_to_play = 56396
    
    names, stacks = active_games[game_to_play].get_players()

    players = [
        {"name": names[0], "stack": stacks[0]},
        {"name": names[1], "stack": stacks[1]},
        {"name": names[2], "stack": stacks[2]},
        {"name": names[3], "stack": stacks[3]},
        {"name": names[4], "stack": stacks[4]},
        {"name": names[5], "stack": stacks[5]}
    ]

    return jsonify(players)



@app.route('/api/updateGame', methods=['POST'])
def update_game():
    # Extract the game_id from the request data
    game_to_play = int(request.json.get('game_id'))

    active_games[game_to_play].update()

    names, stacks = active_games[game_to_play].get_players()
    hands, bets = active_games[game_to_play].get_player_hands_and_bet()
    big_blind = active_games[game_to_play].current_bb
    small_blind = active_games[game_to_play].current_sb
    pot = active_games[game_to_play].pot
    board = active_games[game_to_play].get_board()
    round_over = active_games[game_to_play].is_round_over()

    game_data = {
        "players": [
            {"name": names[0], "stack": stacks[0], "hand": hands[0], "bet": bets[0]},
            {"name": names[1], "stack": stacks[1], "hand": hands[1], "bet": bets[1]},
            {"name": names[2], "stack": stacks[2], "hand": hands[2], "bet": bets[2]},
            {"name": names[3], "stack": stacks[3], "hand": hands[3], "bet": bets[3]},
            {"name": names[4], "stack": stacks[4], "hand": hands[4], "bet": bets[4]},
            {"name": names[5], "stack": stacks[5], "hand": hands[5], "bet": bets[5]}
        ],
        "pot_size": pot,
        "big_blind": big_blind,
        "small_blind": small_blind,
        "board_cards": board,
        "round_over": round_over
    }

    return jsonify(game_data)

if __name__ == "__main__":
    app.run(debug=False)