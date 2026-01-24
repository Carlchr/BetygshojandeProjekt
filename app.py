from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from flask_socketio import SocketIO, emit


app = Flask(__name__)
app.secret_key = 'replace_with_a_secret_key'
socketio = SocketIO(app)

# MySQL configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # replace with your MySQL username
    'password': '',  # replace with your MySQL password
    'database': 'forum-db'
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def login_required(func):
    """
    Middleware-decorator som skyddar routes genom att kontrollera användarautentisering.
    """
    @wraps(func) # Bevarar ursprunglig funktions metadata
    def decorated_function(*args, **kwargs):
        # Kontrollera om 'user'-nyckeln finns i sessionen
        if 'user' not in session:
            # Användaren är inte inloggad - omdirigera till inloggningssidan
            return redirect(url_for('login_page'))
       
        # Användaren är autentiserad - fortsätt till den skyddade routen
        return func(*args, **kwargs)
   
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)', (username, hashed_password))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Username already exists.', 'danger')
        except Exception as e:
            flash('Error creating account.', 'danger')
    return render_template('register.html')


@app.route('/hash')
def hash():
    return generate_password_hash(request.args.get('password'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return f"Welcome, {session['username']}!"

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/forum')
@login_required
def forum():
    return render_template('forum.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
