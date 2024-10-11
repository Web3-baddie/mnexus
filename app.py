import sqlite3
import subprocess
import secrets
from flask import Flask, request, session, redirect, render_template, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask import redirect
import os
from flask import Flask, send_from_directory

app = Flask(__name__, static_folder='static', static_url_path='')


app.secret_key = secrets.token_hex(16)  # Use a more secure secret key

# Connect to SQLite
def get_db_connection():
    conn = sqlite3.connect('ethereum_wallet.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            address TEXT NOT NULL UNIQUE,
            private_key TEXT NOT NULL
        )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER,
            streamer_name TEXT,
            stream_url TEXT,
            active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (tournament_id) REFERENCES tournaments (id)
        )''')
    conn.commit()
    conn.close()

@app.route('/create_stream', methods=['POST'])
def create_stream():
    tournament_id = request.form['tournament_id']
    streamer_name = request.form['streamer_name']

    # Create stream using Twitch API (replace with your implementation)
    stream_url = f"https://twitch.tv/{streamer_name}"  # Replace with actual Twitch stream link generation

    conn = get_db_connection()
    conn.execute('INSERT INTO streams (tournament_id, streamer_name, stream_url) VALUES (?, ?, ?)',
                 (tournament_id, streamer_name, stream_url))
    conn.commit()
    conn.close()

    return jsonify({'stream_url': stream_url})

@app.route('/get_active_streams', methods=['GET'])
def get_active_streams():
    conn = get_db_connection()
    streams = conn.execute('SELECT * FROM streams WHERE active = TRUE').fetchall()
    conn.close()
    
    return jsonify([dict(stream) for stream in streams])

# Register route with wallet generation
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Generate Ethereum wallet
        from web3 import Web3
        web3 = Web3(Web3.HTTPProvider('https://sepolia.infura.io/v3/2a195169b77c4532a9660754f9d15905'))
        account = web3.eth.account.create()  # Generate new Ethereum account
        address = account.address
        private_key = account.key.hex()

        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Hash the password before storing it
            hashed_password = generate_password_hash(password)
            cur.execute('INSERT INTO users (username, password, address, private_key) VALUES (?, ?, ?, ?)',
                        (username, hashed_password, address, private_key))
            conn.commit()
            return redirect('/')
        except sqlite3.IntegrityError:
            return 'Username already exists!'
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/join_tournament', methods=['POST'])
def join_tournament():
    tournament_id = request.form['tournament_id']
    twitch_username = request.form['twitch_username']

    conn = get_db_connection()
    # Save the gamer's Twitch username in the database for the tournament
    conn.execute('INSERT INTO streams (tournament_id, streamer_name, stream_url) VALUES (?, ?, ?)',
                 (tournament_id, twitch_username, f'https://twitch.tv/{twitch_username}'))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Twitch username saved for the tournament!'})

@app.route('/get_stream/<int:tournament_id>', methods=['GET'])
def get_stream(tournament_id):
    conn = get_db_connection()
    stream = conn.execute('SELECT * FROM streams WHERE tournament_id = ? AND active = TRUE', (tournament_id,)).fetchone()
    conn.close()

    if stream:
        return jsonify({'streamer_name': stream['streamer_name'], 'stream_url': stream['stream_url']})
    else:
        return jsonify({'error': 'No active stream found for this tournament'}), 404

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['email']  # Use email field for username
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):  # Verify hashed password
            session['user_id'] = user['id']
            session['address'] = user['address']
            session['private_key'] = user['private_key']

            # Retrieve Ethereum balance using let.mjs
            address = user['address']
            try:
                result = subprocess.run(
                    ['node', 'let.mjs', 'check', 'eth', address],
                    capture_output=True,
                    text=True
                )
                balance_eth = result.stdout.strip()  # Get the balance from the output
                session['balance'] = balance_eth  # Store balance in session for display in the index route
                return redirect('/homepage')  # Redirect to the homepage after successful login
            except Exception as e:
                return f'Error retrieving balance: {str(e)}', 500
            
        else:
            return 'Invalid credentials!'

    return render_template('signin.html')  # Render the login/sign-in page

# Homepage route
@app.route('/homepage')
def homepage():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('Homepage.html')

# Account route for balance checking and sending Ethereum
@app.route('/account', methods=['GET', 'POST'])
def account():
    if 'user_id' in session:
        if request.method == 'POST':
            to_address = request.form.get('to_address')
            amount = request.form.get('amount')

            if to_address and amount:
                try:
                    # Call the Node.js script to send Ethereum
                    result = subprocess.run(
                        ['node', 'let.mjs', 'send', 'eth', session['address'], session['private_key'], to_address, amount],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    output = result.stdout.strip()  # Get the output from the script

                    # Check if the output indicates success
                    if "Transaction successful with hash" in output:
                        transaction_hash = output.split("Transaction successful with hash: ")[1].strip()  # Extract transaction hash
                        return render_template('account.html', transaction_hash=transaction_hash, success_message="Transaction successful!", balance=session['balance'], address=session['address'])
                    else:
                        return render_template('account.html', error="Transaction failed: " + output, success_message=None, balance=session['balance'], address=session['address'])

                except subprocess.CalledProcessError as e:
                    error_message = e.stderr.strip() or "Error sending Ethereum."
                    return render_template('account.html', error=error_message, success_message=None, balance=session['balance'], address=session['address'])

            return render_template('account.html', error='Invalid input provided.', success_message=None, balance=session['balance'], address=session['address'])

        # Display balance and send form
        return render_template('account.html', balance=session['balance'], address=session['address'])

    return redirect('/login')

@app.route('/get_address', methods=['GET'])
def get_address():
    if 'user_id' in session:
        address = session['address']  # Get the address from the session
        return jsonify({'address': address})
    return jsonify({'error': 'User not logged in'}), 401

# Logout route
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clear the session data
    return redirect('/login')  # Redirect to the login page

@app.route('/playtoken')
def playtoken():
    return render_template('PlayToken.html')

@app.route('/sportspool')
def sportspool():
    return render_template('SportsPool.html')  # Make sure to create this template


@app.route('/metamall')
def metamall():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/esports')
def esports():
    return render_template('esports.html')

if __name__ == '__main__':
    init_db()  # Initialize database on startup
    app.run(debug=True)
