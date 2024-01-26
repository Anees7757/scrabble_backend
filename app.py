import os
import pyodbc
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__)

SERVER = f'DESKTOP-CF1EUD1\\SQLEXPRESS'
DATABASE = 'Scrabble'
DRIVER = 'SQL Server'
USERNAME = 'sa'
PASSWORD = '123'
DATABASE_CONNECTION = f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}'

UPLOAD_FOLDER = 'FlaskApp\\uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def close_db_connection(connection):
    try:
        connection.close()
    except Exception as e:
        raise e


@app.route('/get_users', methods=['GET'])
def get_users():
    try:
        conn = pyodbc.connect(DATABASE_CONNECTION)

        cursor = conn.cursor()
        query = """SELECT * FROM Users"""
        cursor.execute(query)
        users = cursor.fetchall()
        conn.commit()

        if users:
            user_list = []
            for user in users:
                user_dict = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'password': user.password,
                    'image': user.image
                }
                user_list.append(user_dict)

            return jsonify({'users': user_list}), 200

        if users.empty:
            return jsonify({'error': 'No users found'}), 404

    except Exception as e:
        return jsonify({'error': f"An error occurred: {e}"}), 500

    finally:
        if 'connection' in locals():
            close_db_connection(conn)


@app.route('/images/<path:image_path>', methods=['GET'])
def get_image(image_path):
    return send_from_directory('uploads', image_path)


@app.route('/add_user', methods=['POST'])
def add_user():
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        image_file = request.files.get('image')

        if image_file.filename == '':
            return 'No selected file', 400

        if image_file:
            filename = username + os.path.splitext(image_file.filename)[1]
            print(filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        conn = pyodbc.connect(DATABASE_CONNECTION)
        cursor = conn.cursor()
        query = """INSERT INTO Users (username, email, password, image) VALUES (?, ?, ?, ?)"""
        values = (username, email, password, filename)
        cursor.execute(query, values)
        conn.commit()

        return 'Record inserted successfully.', 201
    except Exception as e:
        return jsonify({'error': f"An error occurred: {e}"}), 500

    finally:
        if 'connection' in locals():
            close_db_connection(conn)


@app.route('/get_user_details', methods=['POST'])
def get_user_details():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        conn = pyodbc.connect(DATABASE_CONNECTION)
        cursor = conn.cursor()

        query = """SELECT * FROM Users WHERE email = ? AND password = ?"""
        cursor.execute(query, (email, password))
        user_details = cursor.fetchone()
        conn.commit()

        if user_details:
            user_dict = {
                'username': user_details.username,
                'email': user_details.email,
                'image': user_details.image
            }
            return jsonify(user_dict), 200
        else:
            return jsonify({'error': 'User not found'}), 404

    except Exception as e:
        return jsonify({'error': f"An error occurred: {e}"}), 500

    finally:
        if 'conn' in locals():
            close_db_connection(conn)


@app.route('/get_opponent_details', methods=['GET'])
def get_details():
    try:
        username = request.args.get('username')
        conn = pyodbc.connect(DATABASE_CONNECTION)
        cursor = conn.cursor()

        query = """SELECT * FROM Users WHERE username = ?"""
        cursor.execute(query, username)
        user_details = cursor.fetchone()
        conn.commit()

        if user_details:
            user_dict = {
                'username': user_details.username,
                'email': user_details.email,
                'image': user_details.image
            }
            return jsonify(user_dict), 200
        else:
            return jsonify({'error': 'User not found'}), 404

    except Exception as e:
        return jsonify({'error': f"An error occurred: {e}"}), 500

    finally:
        if 'conn' in locals():
            close_db_connection(conn)


# -1 Game Created
# 0 Game Started
# 1 Game Ended

@app.route('/checkGame', methods=['POST'])
def checkGame():
    try:
        data = request.json
        username = data.get('username')

        conn = pyodbc.connect(DATABASE_CONNECTION)
        cursor = conn.cursor()

        query = """SELECT * FROM game WHERE joined_players < total_players AND status = ? ORDER BY id DESC"""
        cursor.execute(query, -1)
        game_details = cursor.fetchone()

        if game_details:
            game_data = {
                'id': game_details.id,
                'started_by': game_details.started_by,
                'total_players': game_details.total_players,
                'joined_players': game_details.joined_players,
                'status': game_details.status
            }

            if username != game_details.started_by:
                query = """UPDATE game_users SET player_2 = ? WHERE game_id = ?"""
                cursor.execute(query, (username, game_details.id))

                query1 = """UPDATE game SET joined_players = 2, status = 0 WHERE id = ?"""
                cursor.execute(query1, game_details.id)

                query = """SELECT * FROM game WHERE id = ?"""
                cursor.execute(query, game_details.id)
                game_details = cursor.fetchone()

                game_data = {
                    'id': game_details.id,
                    'started_by': game_details.started_by,
                    'total_players': game_details.total_players,
                    'joined_players': game_details.joined_players,
                    'status': game_details.status
                }

                query2 = """SELECT * FROM game_users WHERE game_id = ?"""
                cursor.execute(query2, game_details.id)
                players_detail = cursor.fetchone()
                conn.commit()

                if players_detail:
                    return jsonify({
                        "game_data": game_data, "players_detail": {
                            'game_id': players_detail.game_id,
                            'player_1': players_detail.player_1,
                            'player_2': players_detail.player_2
                        }
                    }), 200
                else:
                    return jsonify({'msg': 'Game already exists by his name'}), 201
        else:
            return jsonify({'msg': 'No New Game is created'}), 201

    except Exception as e:
        return jsonify({'error': f"An error occurred: {e}"}), 500

    finally:
        if 'conn' in locals():
            close_db_connection(conn)


@app.route('/newGame', methods=['POST'])
def newGame():
    try:
        data = request.json
        username = data.get('username')

        conn = pyodbc.connect(DATABASE_CONNECTION)
        cursor = conn.cursor()

        query = """INSERT INTO game (started_by, total_players, joined_players, status) VALUES (?, ?, ?, ?)"""
        cursor.execute(query, (username, 2, 1, -1))
        conn.commit()

        query = """SELECT * FROM game WHERE started_by = ? ORDER BY id DESC"""
        cursor.execute(query, username)
        game_details = cursor.fetchone()
        conn.commit()

        if game_details:
            game_data = {
                'id': game_details.id,
                'started_by': game_details.started_by,
                'total_players': game_details.total_players,
                'joined_players': game_details.joined_players,
                'status': game_details.status
            }

            query = """INSERT INTO game_users (game_id,player_1) VALUES (?,?)"""
            cursor.execute(query, (game_details.id, username))
            conn.commit()

            query = """SELECT * FROM game_users WHERE player_1 = ? AND game_id = ?"""
            cursor.execute(query, (username, game_details.id))
            players_detail = cursor.fetchone()
            conn.commit()

            return jsonify({
                "game_data": game_data, "players_detail": {
                    'game_id': players_detail.game_id,
                    'player_1': players_detail.player_1,
                    'player_2': players_detail.player_2
                }
            }), 200

        return jsonify({'msg': 'wait'}), 201

    except Exception as e:
        return jsonify({'error': f"An error occurred: {e}"}), 500

    finally:
        if 'conn' in locals():
            close_db_connection(conn)


@app.route('/playerJoined', methods=['GET'])
def joined():
    try:
        game_id = request.args.get('game_id')

        conn = pyodbc.connect(DATABASE_CONNECTION)
        cursor = conn.cursor()

        query = """SELECT joined_players FROM game WHERE id = ?"""
        cursor.execute(query, game_id)
        game_data = cursor.fetchone()
        conn.commit()

        query = """SELECT * FROM game_users WHERE game_id = ?"""
        cursor.execute(query, game_id)
        game_users = cursor.fetchone()
        conn.commit()

        if game_data.joined_players == 2:
            query = """UPDATE game SET status = ? WHERE id = ?"""
            cursor.execute(query, (0, game_id))

            query = """SELECT * FROM game WHERE id = ?"""
            cursor.execute(query, game_id)
            game_data = cursor.fetchone()

            conn.commit()

            return jsonify({
                "joined": True,
                "player_1": game_users.player_1,
                "player_2": game_users.player_2
            }), 201
        else:
            return jsonify({
                "joined": False,
                "player_1": game_users.player_1,
                "player_2": None
            }), 200

    except Exception as e:
        return jsonify({'error': f"An error occurred: {e}"}), 500

    finally:
        if 'conn' in locals():
            close_db_connection(conn)


@app.route('/endGame', methods=['POST'])
def endGame():
    try:
        data = request.json
        game_id = data.get('game_id')

        conn = pyodbc.connect(DATABASE_CONNECTION)
        cursor = conn.cursor()

        query = """UPDATE game SET status = ? WHERE id = ?"""
        cursor.execute(query, (1, game_id))
        conn.commit()

        return jsonify({
            "game_status": 'ended'
        }), 201

    except Exception as e:
        return jsonify({'error': f"An error occurred: {e}"}), 500

    finally:
        if 'conn' in locals():
            close_db_connection(conn)


@app.route('/addMove', methods=['POST'])
def addTurn():
    try:
        data = request.json
        char = data.get('char')
        rowIndex = data.get('rowIndex')
        colIndex = data.get('colIndex')
        game_id = data.get('game_id')
        player_id = data.get('player_id')

        conn = pyodbc.connect(DATABASE_CONNECTION)
        cursor = conn.cursor()

        query = """INSERT into move (char,rowIndex,colIndex,game_id,player_id) values (?,?,?,?,?)"""
        cursor.execute(query, (char, rowIndex, colIndex, game_id, player_id))
        conn.commit()

        return "Move Inserted", 201

    except Exception as e:
        return jsonify({'error': f"An error occurred: {e}"}), 500

    finally:
        if 'conn' in locals():
            close_db_connection(conn)


@app.route('/getMove', methods=['GET'])
def getTurn():
    try:
        game_id = request.args.get('game_id')

        conn = pyodbc.connect(DATABASE_CONNECTION)
        cursor = conn.cursor()

        query = """SELECT * from move WHERE game_id = ?"""
        cursor.execute(query, game_id)
        moves = cursor.fetchall()
        conn.commit()

        move_list = []
        for move in moves:
            user_dict = {
                "char": move.char,
                "rowIndex": move.rowIndex,
                "colIndex": move.colIndex,
                "game_id": move.game_id,
                "player_id": move.player_id
            }
            move_list.append(user_dict)
            print(move_list)

        return jsonify({'moves': move_list}), 200

    except Exception as e:
        return jsonify({'error': f"An error occurred: {e}"}), 500

    finally:
        if 'conn' in locals():
            close_db_connection(conn)


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0")
