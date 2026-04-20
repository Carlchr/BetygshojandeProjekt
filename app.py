from functools import wraps
import os
from unittest import result
from flask import Flask, render_template, request, session, flash, redirect, url_for, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO
from safety import limiter
from flask_socketio import emit
from error import *  # Importera alla error handlers från error.py

# Huvudapplikation för forumet. Här definieras Flask-appen, databaskopplingar,
# autentiseringskontroller, API-routes och Socket.IO-hantering.
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key@£$€{--![]}') # Använd en miljövariabel för hemligheten, eller en standard om den inte är satt

# Sätter in "rate limitern" in i "app.py" så att den faktiskt kan införa "limits" (vid /login t.ex)
limiter.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Gör "current_user" tillgänglig i alla mallar så att vi kan visa inloggningsstatus, ilket visas i headern
@app.context_processor
def inject_user():
    """Gör inloggad användarinfo tillgänglig i alla Jinja2-mallar.
    Hämtar användarens namn från databasen och lägger det i template-context."""
    username = session.get('username')
    if not username:
        # Ingen inloggad användare - returnera None
        return {'current_user': None, 'current_name': None}

    # Hämta användarens namn från databasen
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    # Returnera både användarnamn och namn för mallerna
    return {'current_user': username, 'current_name': user['name'] if user else None}

@app.context_processor
def inject_user_to_js():
    """Gör användarnamn tillgängligt för JavaScript-kod i mallarna."""
    return {'current_user': session.get('username')}

# MySQL configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  
    'password': '',  
    'database': 'forum_db'
}

# ========== Hjälpfunktioner ==========

def get_db_connection():
    """Skapa en ny databaskoppling till MySQL.
    Returnerar connection-objektet om lyckat, annars None."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        # Fångar alla anslutningsfel (nätverk, autentisering, server nere, etc)
        print(f"Fel vid anslutning till MySQL: {e}")
        return None

def is_valid_user_data():
    """Kontrollera om sessionens användardata är komplett.
    Returnerar True om användarnamn, namn och email finns i sessionen."""
    return session.get('username') and session.get('name') and session.get('email')

def login_required(func):
    """
    Decorator som skyddar routes genom att tvinga användar-autentisering.
    Om användaren inte är inloggad omdirigeras de till login-sidan.
    """
    @wraps(func)  # Bevarar funktionens metadata (namn, docstring, etc)
    def decorated_function(*args, **kwargs):
        # Kolla om 'username' finns i sessionen (dvs användaren är inloggad)
        if 'username' not in session:
            # Inte inloggad - skicka vidare till login-sidan
            return redirect(url_for('login'))
       
        # Användaren är inloggad - tillåt att routen körs
        return func(*args, **kwargs)
   
    return decorated_function

# ========== SocketIO-event-hanterare ==========
# Hanterar WebSocket-kopplingar för realtidscommunikation

@socketio.on('connect')
def handle_connect():
    """Körs när en klient ansluter via WebSocket."""
    print("User connected", request.sid)
    emit("user_connected", broadcast=True)  # Meddelar alla klienter att någon anslutit

# ========== ROUTES - Webbutfrågor ==========

# Hem-route: visar startsidan
@app.route('/')
def index():
    """Visa startsidan (ingen inloggning krävs)"""
    return render_template('index.html')

# Route för inloggning, både GET och POST
# GET: visa inloggningsformulär
# POST: validera autentiseringsuppgifter, skapa session
@app.route('/login', methods=['POST', 'GET'])
@limiter.limit("20/minute")  # Rate limiting: max 20 försök per minut
def login():
    """Hanterar inloggningslogik. Om lyckad inloggning skapas session."""
    try:
        if request.method == 'GET':
            # Visa tom inloggningsform
            return render_template('login.html')
        
        if request.method == 'POST':
            # Hämta användarnamn och lösenord från formuläret
            username = request.form.get("username")
            password = request.form.get("password")

            # Försök ansluta till databasen
            conn = get_db_connection()
            if not conn:
                app.logger.error("Database connection failed")
                return jsonify({"error": "Database connection failed"}), 500

            # Sök efter användaren i databasen
            cursor = conn.cursor(dictionary=True)
            sql = "SELECT * FROM users WHERE username = %s AND password IS NOT NULL"
            cursor.execute(sql, (username, ))
            user = cursor.fetchone()  # Hämta första matchningen

            cursor.close()
            conn.close()

            # Validera lösenordet med hash-jämförelse
            if not user or not check_password_hash(user['password'], password):        
                flash("Invalid username or password", "danger")
                return render_template("login.html")

            # Lösenordet var korrekt - skapa session för användaren
            session["username"] = user["username"]
            return redirect(url_for("profile"))  # Skicka till profilsidan
            
    except Exception as e:
        # Fång och loggning av okända fel under inloggning
        app.logger.error(f"Error during login: {e}", exc_info=True)
        flash("An error occurred during login", "danger")
        return render_template("login.html")

# Route för registrering, både GET och POST
# GET: visa registreringsformulär
# POST: skapa ny användare i databasen med hasherat lösenord
@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("10/hour")  # Rate limiting: max 10 registreringar per timme (förhindra brute-force)
def register():
    """Hanterar registreringen av nya användare."""
    if request.method == 'POST':
        # Hämta formulärdata
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Generera hash av lösenordet (aldrig lagra lösenord i klartext!)
        hashed_password = generate_password_hash(password)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Insätt ny användare i users-tabellen
            cursor.execute('INSERT INTO users (name, username, email, password) VALUES (%s, %s, %s, %s)', 
                          (name, username, email, hashed_password))
            conn.commit()  # Spara ändringarna
            cursor.close()
            conn.close()
        
            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            # Användarnamnet eller emailadressen finns redan
            flash('Username or email already exists.', 'danger')
        except Exception:
            # Något annat fel inträffade under registreringen
            flash('Error creating account.', 'danger')
    return render_template('register.html')

# Route för utloggning
# Raderar sessionen och skickar användaren tillbaka till startsidan
@app.route('/logout', methods = ['GET', 'POST'])
def logout():
    """Logga ut användaren och tömma sessionen."""
    session.clear()  # Raderar all sessiondata
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

# Route för att visa användarprofil
# Kräver inloggning (login_required decorator)
@app.route('/profile')
@login_required
def profile():
    """Visa inloggad användares profil med deras information."""
    conn = get_db_connection()

    if conn is None:
        return "Database connection failed"

    if "username" not in session:
        return redirect(url_for("login"))

    # Hämta användarens data från databasen
    cursor = conn.cursor(dictionary=True)
    username = session.get('username')
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()  # Hämta användaren

    cursor.close()
    conn.close()

    if not user:
        return "User not found in database"
    return render_template("profile.html", user=user)

# Route för att uppdatera användarens namn
# POST: uppdaterar användarnamnet i DB och i sessionen
@app.route('/profile/update_username', methods=['POST'])
@login_required
def update_username():
    """Uppdatera användarens användarnamn."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        new_username = request.form.get('username')
        username = session.get('username')  # Det gamla användarnamnet

        # Validera att båda värden finns
        if not username or not new_username:
            flash("Ingen session eller nytt användarnamn saknas.", "danger")
            return redirect(url_for("profile"))

        # Uppdatera användarnamnet i databasen
        sql = """UPDATE users SET username = %s WHERE username = %s"""
        cursor.execute(sql, (new_username, username))
        conn.commit()

        # Kontrollera att uppdateringen lycka (cursor.rowcount = antal påverkade rader)
        if cursor.rowcount == 0:
            flash("Användaren hittades inte.", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for("profile"))

        # Uppdatera sessionens användarnamn så att användarenän förblir inloggad
        session["username"] = new_username

        cursor.close()
        conn.close()
        flash("Användarnamn uppdaterat!", "success")
        return redirect(url_for("index"))
    except Exception as e:
        # Fång och loggning av okända fel
        app.logger.error(f"Error updating user: {e}", exc_info=True)
        flash("An error occurred while updating your profile.", "danger")
        return redirect(url_for("profile"))

# Route för att uppdatera användarens lösenord
# POST: validerar nuvarande lösenord och uppdaterar med nytt hasherat lösenord
@app.route('/profile/update_password', methods=['POST'])
@login_required
def update_password():
    """Uppdatera användarens lösenord med validering av det gamla."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        username = session.get('username')
        new_password = request.form.get('password')
        current_password = request.form.get('currentpassword')

        # Validera att alla fält är ifyllda
        if not username or not new_password or not current_password:
            flash("Alla lösenordsfält måste fyllas i.", "danger")
            return redirect(url_for("profile"))

        # Hämta det lagra de hashade lösenordet från databasen
        password_sql_select = "SELECT password FROM users WHERE username = %s"
        cursor.execute(password_sql_select, (username,))
        database_password = cursor.fetchone()

        if not database_password:
            flash("Användaren hittades inte.", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for("profile"))

        # Validera att det nuvarande lösenordet är korrekt
        current_password_check = check_password_hash(database_password["password"], current_password)
        if not current_password_check:
            flash("Felaktigt nuvarande lösenord.", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for("profile"))

        # Generera hash av det nya lösenordet och uppdatera databasen
        hashed_password = generate_password_hash(new_password)
        password_sql_update = "UPDATE users SET password = %s WHERE username = %s"
        cursor.execute(password_sql_update, (hashed_password, username))
        conn.commit()

        if cursor.rowcount == 0:
            flash("Användaren hittades inte.", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for("profile"))

        cursor.close()
        conn.close()
        flash("Lösenord uppdaterat!", "success")
        return redirect(url_for("profile"))
    except Exception as e:
        app.logger.error(f"Error updating user: {e}", exc_info=True)
        flash("An error occurred while updating your profile.", "danger")
        return redirect(url_for("profile"))

# ========== FORUM ROUTES ==========

# Route för forumöversikten
# Visar alla befintliga trådar
@app.route('/forum')
@login_required
def forum():
    """Visa forumets huvudsida med alla trådar."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Hämta alla trådar från databasen
    cursor.execute("SELECT * FROM topics")
    topics = cursor.fetchall()  # Hämta alla resultat

    cursor.close()
    conn.close()

    return render_template("forum.html", topics=topics)

# Route för sökning i trådlistan
# GET-parameter searchInfo används för att söka efter trådar
@app.route('/search')
@login_required
def search():
    """Sök efter trådar baserat på titel (rubrik)."""
    # Hämta söksträngen från URL-parametern
    searchInfo = request.args.get("searchInfo")
    
    # Kontrollera att användaren skrev något
    if not searchInfo:
        flash("Skriv något att söka efter.", "info")
        return redirect(url_for("forum"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Sök efter trådar vars titel innehåller söksträngen (LIKE = partiell matchning)
    sql = "SELECT id FROM topics WHERE rubrik LIKE %s"
    cursor.execute(sql, (f"%{searchInfo}%",))
    topic = cursor.fetchone()  # Hämta första matchningen
    
    cursor.close()
    conn.close()

    if not topic:
        # Ingen tråd hittades
        print("Ingen tråd matchade din sökning.", "info")
        return redirect(url_for("forum"))

    # Omdirigera till den hittade tråden
    return redirect(url_for("open_topic", topic_id=topic["id"]))

# Route för att skapa en ny tråd i forumet
@app.route('/forum/new_topic', methods=['GET', 'POST'])
@login_required
def new_topic():
    """Route for creating a new forum topic"""
    if request.method == 'POST':
        title = request.form['title']
        username = session.get('username')
        content = request.form['content']
        conn = get_db_connection()
        if conn is None:
            flash('Databasanslutning misslyckades. Försök igen senare.')
            return render_template('new_topic.html')
        try:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO topics (rubrik, username, innehall) VALUES (%s, %s, %s)', (title, username, content))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Tråd skapad!', 'success')
            return redirect(url_for('forum'))
        except Exception:
            flash('Fel vid skapande av tråd.', 'danger')
    return render_template('new_topic.html')

# Route för att skapa ett nytt inlägg i en tråd
@app.route('/forum/new_post/<int:topic_id>', methods=['GET', 'POST'])
@login_required
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
        except Exception:
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
        except Exception:
            flash('Fel vid skapande av inlägg.', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('open_topic', topic_id=topic_id))
    return render_template('new_post.html', topic_id=topic_id)

# Route för att öppna en tråd och visa alla inlägg i den
@app.route('/forum/topic/<int:topic_id>')
@login_required
def open_topic(topic_id):
    """Visa en specifik forumtråd med alla dess inlägg och röstningsstatistik."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Hämta trådsinformationen
    cursor.execute("SELECT * FROM topics WHERE id = %s", (topic_id,))
    topic = cursor.fetchone()
    cursor.close()

    if not topic:
        # Tråden existerar inte
        conn.close()
        flash("Topic not found")
        return redirect(url_for("forum"))

    # Hämta alla inlägg i tråden, sorterade efter datum (tidigaste först)
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM posts WHERE topic_id = %s ORDER BY datum ASC",
        (topic_id,)
    )

    posts = cursor.fetchall()  # Hämta alla inlägg

    # För varje inlägg räknar vi antalet likes och dislikes
    for post in posts:
        # Räkna likes för det här inlägget
        like_cursor = conn.cursor()
        like_cursor.execute(
            "SELECT COUNT(*) FROM likes WHERE post_id = %s AND likes = 1",
            (post["id"],)
        )
        result = like_cursor.fetchone()
        post["likes_count"] = result[0] if result else 0  # Standardvärde 0 om inget resultat
        like_cursor.close()

        # Räkna dislikes för det här inlägget
        dislike_cursor = conn.cursor()
        dislike_cursor.execute(
            "SELECT COUNT(*) FROM likes WHERE post_id = %s AND dislikes = 1",
            (post["id"],)
        )
        result = dislike_cursor.fetchone()
        post["dislikes_count"] = result[0] if result else 0  # Standardvärde 0 om inget resultat
        dislike_cursor.close()

    cursor.close()
    conn.close()

    # Skicka tråden och inläggen med röstningsstatistik till mallen
    return render_template("open_topic.html", topic=topic, posts=posts), 200

# Route för röstning (likes/dislikes) på inlägg
# Implementerar toggle-beteende: om redan röstad ändras rösten, annars tas den bort

@app.route('/forum/topic/like_post/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    """Gilla ett inlägg. Om redan gillat, tas gillningen bort (toggle)."""
    username = session.get("username")

    if not username:
        return {"error": "Not logged in"}, 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT likes, dislikes FROM likes WHERE post_id = %s AND username = %s",
        (post_id, username)
    )
    like_record = cursor.fetchone()

    if like_record:
        if like_record["likes"] == 1:
            cursor.execute(
                "DELETE FROM likes WHERE post_id = %s AND username = %s",
                (post_id, username)
            )
            conn.commit()
            flash("Like removed", "info")
        else:
            cursor.execute(
                "UPDATE likes SET likes = 1, dislikes = 0 WHERE post_id = %s AND username = %s",
                (post_id, username)
            )
            conn.commit()
            flash("Changed dislike to like.", "success")
    else:
        try:
            cursor.execute(
                "INSERT INTO likes (post_id, username, likes, dislikes) VALUES (%s, %s, 1, 0)",
                (post_id, username)
            )
            conn.commit()
            flash("Post liked", "success")
        except mysql.connector.IntegrityError:
            flash("You have already liked this post.", "danger")

    cursor.close()
    conn.close()
    return redirect(request.referrer)

# Route för att ogilla ett inlägg
@app.route('/forum/topic/dislike_post/<int:post_id>', methods=['POST'])
@login_required
def dislike_post(post_id):
    username = session.get("username")

    if not username:
        return {"error": "Not logged in"}, 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT likes, dislikes FROM likes WHERE post_id = %s AND username = %s",
        (post_id, username)
    )
    like_record = cursor.fetchone()

    if like_record:
        if like_record["dislikes"] == 1:
            cursor.execute(
                "DELETE FROM likes WHERE post_id = %s AND username = %s",
                (post_id, username)
            )
            conn.commit()
            flash("Dislike removed", "info")
        else:
            cursor.execute(
                "UPDATE likes SET likes = 0, dislikes = 1 WHERE post_id = %s AND username = %s",
                (post_id, username)
            )
            conn.commit()
            flash("Changed like to dislike.", "success")
    else:
        try:
            cursor.execute(
                "INSERT INTO likes (post_id, username, likes, dislikes) VALUES (%s, %s, 0, 1)",
                (post_id, username)
            )
            conn.commit()
            flash("Post disliked", "success")
        except mysql.connector.IntegrityError:
            flash("You have already disliked this post.", "danger")

    cursor.close()
    conn.close()
    return redirect(request.referrer)

# Route för att ta bort ett inlägg, endast av admin eller den som skrev inlägget
@app.route('/forum/topic/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):

    username = session.get("username")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT username, topic_id FROM posts WHERE id = %s", (post_id,))
    post = cursor.fetchone()

    cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if not post:
        flash("Post not found.", "danger")
        return redirect(url_for("index"))

    if user["role"] == "admin":
        pass
    elif post["username"] != username:
        flash("Not allowed to delete this post.", "danger")
        return redirect(url_for("open_topic", topic_id=post["topic_id"]))

    cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
    conn.commit()

    topic_id = post["topic_id"]

    cursor.close()
    conn.close()

    return redirect(url_for("open_topic", topic_id=topic_id))

# Route för adminpanelen
# Visas endast för admin-användare
@app.route('/admin')
@login_required
def admin():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    username = session.get('username')
    cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if user["role"] != "admin":
        flash("Access denied: Admins only", "danger")
        return redirect(url_for("index"))

    cursor.execute("SELECT id, name, username, email, role FROM users")
    users = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin.html", users=users)

# Route för att ta bort en användare, endast av admin
# POST: utför radering av användare i DB, kräver admin-roll
@app.route('/admin/delete_user/<username>', methods=['POST'])
@login_required
def delete_user(username):

    # Kontrollera att användaren är inloggad
    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    #Hämta den inloggade användarens roll
    cursor.execute("SELECT role FROM users WHERE username = %s", (session.get('username'),))
    user = cursor.fetchone()

    cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
    user_to_delete = cursor.fetchone()

    # Kontrollera om användaren är admin, isåfall nekas radering
    if user["role"] != "admin":
        flash("Access denied: Admins only", "danger")
        return redirect(url_for("index"))
    elif user_to_delete["role"] == "admin":
        flash("Cannot delete another admin.", "danger")
        return redirect(url_for("admin"))

    cursor.execute("DELETE FROM users WHERE username = %s", (username,))
    conn.commit()

    cursor.close()
    conn.close()

    flash("User deleted successfully.", "success")
    return redirect(url_for("index"))

# Route för realtidschatt
# Visar WebSocket-chattvy
@app.route('/realtidschatt')
@login_required
def realtidschatt():
    return render_template("realtidschatt.html")

if __name__ == '__main__':
    # Use SocketIO runner 
    socketio.run(app, debug=True, port=5500)
