import os
from flask import Flask, render_template, request, session, flash, redirect, url_for, jsonify
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO
from safety import limiter
from flask_socketio import emit
from error import *  # Importera alla error handlers från error.py

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key@£$€{--![]}') # Använd en miljövariabel för hemligheten, eller en standard om den inte är satt

# Sätter in "rate limitern" in i "app.py" så att den faktiskt kan införa "limits" (vid /login t.ex)
limiter.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Gör "current_user" tillgänglig i alla mallar så att vi kan visa inloggningsstatus, ilket visas i headern
@app.context_processor
def inject_user():
    return {'current_user': session.get('username')}

@app.context_processor
def inject_user_to_js():
    return {'current_user': session.get('username')}

# MySQL configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  
    'password': '',  
    'database': 'forum_db'
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"Fel vid anslutning till MySQL: {e}")
        return None
    
def is_valid_user_data():
    return session.get('username') and session.get('name') and session.get('email')

@socketio.on('connect')
def handle_connect():
    print("User connected", request.sid)
    emit("user_connected", broadcast=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST', 'GET'])
@limiter.limit("50/minute")
def login():
    try:
        if request.method == 'GET':
            return render_template('login.html')
        
        if request.method == 'POST':
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


            if not user or not check_password_hash(user['password'], password):        
                flash("Invalid username or password", "danger")
                return render_template("login.html")

            session["username"] = user["username"]
            return redirect(url_for("profile"))
    except Exception as e:
        app.logger.error(f"Error during login: {e}", exc_info=True)
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

@app.route('/logout', methods = ['GET', 'POST'])
def logout():
    """User logout route"""
    
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    conn = get_db_connection()

    if conn is None:
        return "Database connection failed"

    if "username" not in session:
        return redirect(url_for("login"))

    cursor = conn.cursor(dictionary=True)
    username = session.get('username')
    cursor.execute(
        "SELECT id, name, username, email FROM users WHERE username = %s",(username,)
    )

    user = cursor.fetchone()
    print("DB user:", user)

    cursor.close()
    conn.close()

    if not user:
        return "User not found in database"
    return render_template("profile.html", user=user)

@app.route('/profile', methods=['POST'])
def update_user():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # 1. Hämta data från body (req.body)
    new_username = request.form.get('username')
    username = session.get('username')
   
    if not username or not new_username:
        return {"error": "Ingen session"}, 401
    
    # skapa databaskoppling (kod bortklippt) och använd UPDATE för att uppdatera databasen
    sql = """UPDATE users SET username = %s WHERE username = %s"""
   
    # 3. Kör frågan med en tupel av värden
    cursor.execute(sql, (new_username, username))
    
    conn.commit()
    # Kontrollera om någon rad faktiskt uppdaterades
    if cursor.rowcount == 0: 
        return print({"error": "Användaren hittades inte"}), 404
    
    session["username"] = new_username  # Uppdatera sessionen med det nya användarnamnet

    cursor.close()
    conn.close()
    return redirect(url_for("profile"))

@app.route('/forum')
def forum():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM topics")
    topics = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("forum.html", topics=topics)

@app.route('/forum/new_topic', methods=['GET', 'POST'])
def new_topic():
    """Route for creating a new forum topic"""
    if request.method == 'POST':
        title = request.form['title']
        username = session.get('username')
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
def new_post(topic_id):
    """Route for creating a new post in a forum topic"""
    if request.method == 'POST':
        content = request.form['content']
        username = session.get('username')
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
def open_topic(topic_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM topics WHERE id = %s", (topic_id,))
    topic = cursor.fetchone()
    cursor.close()

    if not topic:
        conn.close()
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

@app.route('/forum/topic/like_post/<int:post_id>', methods=['POST'])
def like_post(post_id):

    username = session.get("username")

    if not username:
        return {"error": "Not logged in"}, 401

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO likes (post_id, username) VALUES (%s, %s)",
            (post_id, username)
        )
        conn.commit()

    except mysql.connector.IntegrityError:
        flash("You have already liked this post.", "danger")
        return redirect(request.referrer)

    cursor.close()
    conn.close()

    return redirect(request.referrer)

@app.route('/forum/topic/dislike_post/<int:post_id>', methods=['POST'])
def dislike_post(post_id):

    username = session.get("username")

    conn = get_db_connection()
    cursor = conn.cursor()


    cursor.execute(
        "DELETE FROM likes WHERE post_id = %s AND username = %s",
        (post_id, username)
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(request.referrer)

@app.route('/forum/topic/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):

    username = session.get("username")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT username, topic_id FROM posts WHERE id = %s", (post_id,))
    post = cursor.fetchone()

    if not post:
        return {"error": "Post not found"}, 404

    if post["username"] != username:
        return {"error": "Not allowed"}, 403

    cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
    conn.commit()

    topic_id = post["topic_id"]

    cursor.close()
    conn.close()

    return redirect(url_for("open_topic", topic_id=topic_id))

@app.route('/realtidschatt')
def realtidschatt():
    return render_template("realtidschatt.html")

if __name__ == '__main__':
    # Use SocketIO runner 
    socketio.run(app, debug=True, port=5500)
