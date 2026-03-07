import os
from flask import *
import mysql.connector
from mysql.connector import Error
from werkzeug.security import *
from functools import *
from flask_socketio import SocketIO
from safety import limiter
from flask_jwt_extended import *
from datetime import timedelta 
from flask_socketio import *


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key@£$€{--![]}') # Använd en miljövariabel för hemligheten, eller en standard om den inte är satt

# Gör all kod i jinja mallar till text istället vör kod. Förhindrar XSS attacker
# Det undviker att användarinmatning som innehåller HTML eller JavaScript körs i webbläsaren
app.jinja_env.autoescape = True  

app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'super-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=10)

app.config['JWT_TOKEN_LOCATION'] = ['cookies', 'headers']
app.config['JWT_COOKIE_NAME'] = 'access_token'

jwt = JWTManager(app)

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
    
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    # Hämta identity från JWT, i det här fallet användarnamnet som vi satte som identity när vi skapade token
    current_user = get_jwt_identity()
    # Det här är för att visa att vi kan hämta hela JWT payloaden
    print(get_jwt())
    return jsonify(logged_in_as=current_user), 200

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
@limiter.limit("50/minute")
def login():
    """Login route that authenticates users with tokens"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()

        #Om ingen koppling kunde skapas
        if conn is None:
            flash('Databasanslutning misslyckades. Försök igen senare.')
            print("Database connection failed during login attempt.")
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
            access_token = create_access_token(identity=user['username'])
            response = redirect(url_for('profile'))
            set_access_cookies(response, access_token)
            print(f"User {username} logged in successfully.")
            return response
        else:
            flash('Invalid username or password', 'danger')
            print(f"Failed login attempt for username: {username}")
            return render_template('login.html')
    print("Rendering login page")
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("10/hour")  # Förhindra brute-force registreringar
def register():
    """User registration route"""
    if request.method == 'POST':

        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        hashed_password = generate_password_hash(password)
        
        try:
        
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (name, username, email, password) VALUES (%s, %s, %s, %s)', (name, username, email, hashed_password))
            conn.commit()
            cursor.close()
            conn.close()
        
            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Username or email already exists.', 'danger')
        except Exception as e:
            flash('Error creating account.', 'danger')
    return render_template('register.html')

@app.route('/logout')
def logout():
    """User logout route"""
    if request.headers.get('Authorization'):
        # API logout
        return jsonify(success=True), 200
    else:
        # Web logout
        response = redirect(url_for('index'))
        unset_jwt_cookies(response)
        return response

@app.route('/profile')
def profile():
    """Profile route - returns JSON if API call, renders template if web page"""
    if request.headers.get('Authorization') or request.cookies.get('access_token'):
        # API call or web with cookie
        try:
            current_user = get_jwt_identity()
        except:
            if request.headers.get('Authorization'):
                return jsonify(error='Invalid token'), 401
            else:
                return redirect(url_for('login'))
        conn = get_db_connection()
        if conn is None:
            if request.headers.get('Authorization'):
                return jsonify(error='Database connection failed'), 500
            else:
                flash('Database connection failed.')
                return render_template('profile.html')
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT id, name, username, email FROM users WHERE username = %s', (current_user,))
            user = cursor.fetchone()
        finally:
            try:
                cursor.close()
            except:
                pass
            conn.close()
        
        if user is None:
            if request.headers.get('Authorization'):
                return jsonify(error='User not found'), 404
            else:
                return redirect(url_for('login'))
        
        if request.headers.get('Authorization'):
            return jsonify(user), 200
        else:
            return render_template('profile.html', user=user)
    else:
        # Web page load without token
        return redirect(url_for('login'))

@app.route('/forum')
def forum():
    """Forum route - returns JSON if API call, renders template if web page"""
    if request.headers.get('Authorization') or request.cookies.get('access_token'):
        # API call or web with cookie
        try:
            get_jwt_identity()  # Just to verify token
        except:
            if request.headers.get('Authorization'):
                return jsonify(error='Invalid token'), 401
            else:
                return redirect(url_for('login'))
        conn = get_db_connection()
        if conn is None:
            if request.headers.get('Authorization'):
                return jsonify(error='Database connection failed'), 500
            else:
                flash('Database connection failed.')
                return render_template('forum.html')
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM topics')
            topics = cursor.fetchall()
        finally:
            try:
                cursor.close()
            except:
                pass
            conn.close()
        
        if request.headers.get('Authorization'):
            return jsonify(topics=topics), 200
        else:
            return render_template('forum.html', topics=topics)
    else:
        # Web page load without token
        return redirect(url_for('login'))

@app.route('/forum/new_topic', methods=['GET', 'POST'])
@jwt_required()
def new_topic():
    """Route for creating a new forum topic"""
    if request.method == 'POST':
        title = request.form['title']
        username = get_jwt_identity()
        conn = get_db_connection()
        if conn is None:
            flash('Databasanslutning misslyckades. Försök igen senare.')
            return render_template('new_topic.html')
        try:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO topics (rubrik, username) VALUES (%s, %s)', (title, username))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Tråd skapad!', 'success')
            return redirect(url_for('forum'))
        except Exception as e:
            flash('Fel vid skapande av tråd.', 'danger')
    return render_template('new_topic.html')

@app.route('/forum/new_post/<int:topic_id>', methods=['GET', 'POST'])
@jwt_required()
def new_post(topic_id):
    """Route for creating a new post in a forum topic"""
    if request.method == 'POST':
        content = request.form['content']
        username = get_jwt_identity()
        conn = get_db_connection()
        if conn is None:
            flash('Databasanslutning misslyckades. Försök igen senare.')
            return redirect(url_for('open_topic', topic_id=topic_id))
        
        # Validera att topic_id existerar
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT id FROM topics WHERE id = %s', (topic_id,))
            topic = cursor.fetchone()
            if topic is None:
                flash('Tråden existerar inte.', 'danger')
                return redirect(url_for('forum'))
        finally:
            try:
                cursor.close()
            except:
                pass
        
        try:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO posts (inlägg, datum, username, topic_id) VALUES (%s, CURDATE(), %s, %s)', (content, username, topic_id))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('open_topic', topic_id=topic_id))
        except Exception as e:
            flash('Fel vid skapande av inlägg.', 'danger')
            return redirect(url_for('open_topic', topic_id=topic_id))
    return render_template('new_post.html', topic_id=topic_id)

@app.route('/forum/topic/<int:topic_id>')
def open_topic(topic_id):
    """Topic route - returns JSON if API call, renders template if web page"""
    if request.headers.get('Authorization') or request.cookies.get('access_token'):
        # API call or web with cookie
        try:
            get_jwt_identity()  # Just to verify token
        except:
            if request.headers.get('Authorization'):
                return jsonify(error='Invalid token'), 401
            else:
                return redirect(url_for('login'))
        conn = get_db_connection()
        if conn is None:
            if request.headers.get('Authorization'):
                return jsonify(error='Database connection failed'), 500
            else:
                flash('Database connection failed.')
                return render_template('open_topic.html', topic_id=topic_id)
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM topics WHERE id = %s', (topic_id,))
            topic = cursor.fetchone()
            
            if topic is None:
                if request.headers.get('Authorization'):
                    return jsonify(error='Topic not found'), 404
                else:
                    flash('Topic not found.')
                    return redirect(url_for('forum'))
            
            cursor.execute('SELECT * FROM posts WHERE topic_id = %s ORDER BY datum ASC', (topic_id,))
            posts = cursor.fetchall()
        finally:
            try:
                cursor.close()
            except:
                pass
            conn.close()
        
        if request.headers.get('Authorization'):
            return jsonify(topic=topic, posts=posts), 200
        else:
            return render_template('open_topic.html', topic=topic, posts=posts)
    else:
        # Web page load without token
        return redirect(url_for('login'))

if __name__ == '__main__':
    # Use SocketIO runner 
    socketio.run(app, debug=True, port=5500)
