from flask import *
import mysql.connector
from mysql.connector import Error
from werkzeug.security import *
from functools import *
from flask_socketio import *
from safety import limiter
import random as rand

# .\.venv\Scripts\Activate.ps1 (för att aktivera venv i terminalen (för säkrare installation av paket)), "deactivate" för att stänga av venv igen. 
# Installera paketen med: pip install; "Flask-Limiter" (denna ska laddas ned utan .venv mode), "mysql-connector-python", "flask-socketio"

app = Flask(__name__)
app.secret_key = str(rand.randint(1, 10000))
socketio = SocketIO(app)

# Sätter in "rate limitern" in i "app.py" så att den faktiskt kan införa "limits" (vid /login t.ex)
limiter.init_app(app)

# MySQL configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # replace with your MySQL username
    'password': '',  # replace with your MySQL password
    'database': 'forum_db'
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Fel vid anslutning till MySQL: {e}")
        return None
    
def login_required(func):
    """
    Middleware-decorator som skyddar routes genom att kontrollera användarautentisering.
    """
    @wraps(func) # Bevarar ursprunglig funktions metadata
    def decorated_function(*args, **kwargs):
        # Kontrollera om inloggnings-nyckel finns i sessionen
        # Vi sätter `session['user_id']` och/eller `session['username']` vid login,
        # så kontrollera `user_id` istället för en missvisande 'user'-nyckel.
        if 'user_id' not in session:
            return redirect(url_for('login'))
        # Användaren är autentiserad - fortsätt till den skyddade routen
        return func(*args, **kwargs)
   
    return decorated_function


@app.route('/trigger-500')
def trigger_500():
    """Route that intentionally triggers a 500 error by dividing by zero"""
    app.logger.warning('Someone accessed the /trigger-500 route')
    # This will cause a ZeroDivisionError and trigger our 500 error handler
    result = 1 / 0
    return f"This should never be reached: {result}"

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Custom 404 error handler"""
    app.logger.warning(f'{error} error: {request.url} not found')
    
    # it is posible to render a template and return a status code other than 200
    return render_template('errors/404.html'), 404 # 404 is the status code for not found errors

@app.errorhandler(500)
def internal_error(error):
    """Custom 500 error handler"""
    app.logger.error(f'Internal server error: {error}')
    return render_template('errors/500.html'), 500 # 500 is the status code for internal server error

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle any unhandled exceptions"""
    app.logger.error(f'Unhandled exception: {error}', exc_info=True)
    return render_template('errors/500.html')

@app.errorhandler(429)
def ratelimit_handler(e):
    """Custom 429 error handler"""
    app.logger.warning(f'Rate limit exceeded: {e}')
    return render_template('errors/429.html'), 429 

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5/minute")
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        #Om ingen koppling kunde skapas
        if conn is None:
            flash('Databasanslutning misslyckades. Försök igen senare.')
            return render_template('login.html')
        try:
            #Hämta användare från databasen
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
        finally:
            try:
                #slutar hämta info
                cursor.close()
            except:
                pass 
            # stänger kopplingen
            conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')

            return redirect(url_for('profile'))
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
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Use SocketIO runner 
    socketio.run(app, debug=True, port=5500)
