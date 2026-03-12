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

app.config['JWT_SECRET_KEY'] = 'super-secret-key'
# os.environ.get('JWT_SECRET_KEY', 'super-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=30)

app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token_cookie"
app.config["JWT_ACCESS_COOKIE_PATH"] = "/"

app.config["JWT_COOKIE_SECURE"] = False
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
app.config["JWT_COOKIE_SAMESITE"] = "Lax"

# VIKTIGT
app.config["JWT_COOKIE_DOMAIN"] = None

jwt = JWTManager(app)

# Sätter in "rate limitern" in i "app.py" så att den faktiskt kan införa "limits" (vid /login t.ex)
limiter.init_app(app)

socketio = SocketIO(app, cors_allowed_origins="*")

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

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Custom 404 error handler"""
    app.logger.warning(f'{error} error: {request.url} not found')
    return render_template('errors/404.html'), 404 # 404 is the status code for not found errors

@app.errorhandler(429)
def ratelimit_handler(e):
    """Custom 429 error handler"""
    app.logger.warning(f'Rate limit exceeded: {e}')
    return render_template('errors/429.html'), 429 

@app.errorhandler(500)
def internal_error(error):
    """Custom 500 error handler"""
    app.logger.error(f'Internal server error: {error}')
    return render_template('errors/500.html'), 500 # 500 is the status code for internal server error

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle any unhandled exceptions"""
    app.logger.error(f'Unhandled exception: {error}', exc_info=True)
    return render_template('errors/500.html'), 500

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect(username):
    print(f"User connected", request.sid)
    emit("user_connected", broadcast=True)

@app.route('/login', methods=['POST', 'GET'])
@limiter.limit("50/minute")
def login():
    try:
        if request.method == 'GET':
            return render_template('login.html')
        
        if request.method == 'POST':
            # avgör om det är API eller web
            api_request = request.is_json

            if api_request:
                data = request.get_json()
                username = data.get("username")
                password = data.get("password")
            else:
                username = request.form.get("username")
                password = request.form.get("password")
            

            conn = get_db_connection()
            if not conn:
                app.logger.error("Database connection failed")
                return jsonify({"error": "Database connection failed"}), 500

            cursor = conn.cursor(dictionary=True)
            sql = "SELECT * FROM users WHERE username = %s AND password IS NOT NULL"
            cursor.execute(sql, (username, ))
            user = cursor.fetchone()

            cursor.close()
            conn.close()

            access_token = create_access_token(identity=username)

            if not user or not check_password_hash(user['password'], password):

                if api_request:
                    return jsonify({"error": "Invalid username or password"}), 401
                else:
                    flash("Invalid username or password", "danger")
                    return render_template("login.html")

            # API login
            if api_request:
                return jsonify({
                    "access_token": access_token,
                    "username": username
                }), 200

            # Web login
            response = make_response(redirect(url_for("profile")))
            set_access_cookies(response, access_token)
            return response
    except Exception as e:
        app.logger.error(f"Error during login: {e}", exc_info=True)

        if request.is_json:
            return jsonify({"error": "An error occurred during login"}), 500
        else:
            flash("An error occurred during login", "danger")
            # use the template name, not the URL, otherwise Jinja will try to load a file
            # literally named "/login" which doesn't exist and triggers a 500
            return render_template("login.html")


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
@jwt_required()
def profile():

    current_user = get_jwt_identity()
    print("JWT user:", current_user)

    conn = get_db_connection()

    if conn is None:
        return "Database connection failed"

    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT id, name, username, email FROM users WHERE username = %s",
        (current_user,)
    )

    user = cursor.fetchone()

    print("DB user:", user)

    cursor.close()
    conn.close()

    if not user:
        return "User not found in database"

    return render_template("profile.html", user=user)

@app.route('/forum')
@jwt_required()
def forum():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM topics")
    topics = cursor.fetchall()

    cursor.close()
    conn.close()

    if request.is_json:
        return jsonify(topics=topics), 200

    return render_template("forum.html", topics=topics)

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
            cursor.close()
            if topic is None:
                flash('Tråden existerar inte.', 'danger')
                conn.close()
                return redirect(url_for('forum'))
        except Exception as e:
            flash('Fel vid validering av tråd.', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('forum'))
        
        try:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO posts (inlägg, datum, username, topic_id) VALUES (%s, CURDATE(), %s, %s)', (content, username, topic_id))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('open_topic', topic_id=topic_id))
        except Exception as e:
            flash('Fel vid skapande av inlägg.', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('open_topic', topic_id=topic_id))
    return render_template('new_post.html', topic_id=topic_id)

@app.route('/forum/topic/<int:topic_id>')
@jwt_required()
def open_topic(topic_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM topics WHERE id = %s", (topic_id,))
    topic = cursor.fetchone()
    cursor.close()

    if not topic:
        conn.close()
        if request.is_json:
            return jsonify({"error": "Topic not found"}), 404
        flash("Topic not found")
        return redirect(url_for("forum"))

    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM posts WHERE topic_id = %s ORDER BY datum ASC",
        (topic_id,)
    )

    posts = cursor.fetchall()

    cursor.close()
    conn.close()

    if request.is_json:
        return jsonify(topic=topic, posts=posts), 200

    return render_template("open_topic.html", topic=topic, posts=posts)

if __name__ == '__main__':
    # Use SocketIO runner 
    socketio.run(app, debug=True, port=5500)
