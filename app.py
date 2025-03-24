import os
from flask import Flask, render_template, request, redirect, url_for, session, make_response
import psycopg2
import csv
import io


app = Flask(__name__)
app.jinja_env.autoescape = False
app.config['SESSION_COOKIE_HTTPONLY'] = False

app.secret_key = os.environ.get('SECRET_KEY', 'une_clé_secrète_par_défaut')

# Configuration de la base de données PostgreSQL (version locale)
DATABASE_CONFIG = {
    'dbname': os.environ.get('DB_NAME', 'cloud_app_local'),  # Le nom de la base de données locale
    'user': os.environ.get('DB_USER', 'postgres'),  # L'utilisateur PostgreSQL par défaut
    'password': os.environ.get('DB_PASSWORD', 'thefaster'),  # Le mot de passe de PostgreSQL local
    'host': os.environ.get('DB_HOST', 'localhost'),  # Connexion à localhost pour PostgreSQL local
    'port': os.environ.get('DB_PORT', '5432'),  # Port par défaut de PostgreSQL
    'sslmode': os.environ.get('DB_SSLMODE', 'disable')  # Désactiver SSL pour la connexion locale
}

# Fonction pour établir une connexion à la base de données
def get_db_connection():
    conn = psycopg2.connect(**DATABASE_CONFIG)
    return conn

# Fonction pour créer les tables
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Table des utilisateurs
        cursor.execute(''' 
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(100) NOT NULL,
                preferred_language VARCHAR(10),
                report_format VARCHAR(10)
            );
        ''')
        # Table des données des capteurs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_data (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(id),
                material_type VARCHAR(100),
                volume_processed FLOAT,
                loss_rate FLOAT,
                timestamp TIMESTAMP DEFAULT NOW()
            );
        ''')
        # Table des données opérationnelles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operational_data (
                id SERIAL PRIMARY KEY,
                user_id INT REFERENCES users(id),
                machine_hours FLOAT,
                loss_costs FLOAT,
                timestamp TIMESTAMP DEFAULT NOW()
            );
        ''')
        conn.commit()
        print("Tables créées avec succès.")
    except Exception as e:
        print(f"Erreur lors de la création des tables : {e}")
    finally:
        conn.close()

# Page d'accueil
@app.route('/')
def home():
    return render_template('home.html')

# Inscription
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        preferred_language = request.form.get('preferred_language', 'fr')
        report_format = request.form.get('report_format', 'PDF')

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (username, password, preferred_language, report_format)
                VALUES (%s, %s, %s, %s);
            ''', (username, password, preferred_language, report_format))
            conn.commit()
            return redirect(url_for('login'))
        except Exception as e:
            return f"Erreur lors de l'inscription : {e}"
        finally:
            conn.close()
    return render_template('register.html')

#edit profile
# Modification du nom d'utilisateur (Vulnérable à l'IDOR)
@app.route('/edit_username', methods=['GET', 'POST'])
def edit_username():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_username = request.form['new_username']
        target_user_id = request.form['user_id']  # L'ID est pris directement depuis le formulaire

        conn = get_db_connection()
        cursor = conn.cursor()

        # Vulnérable à l'IDOR : aucun contrôle si l'utilisateur connecté est bien le propriétaire
        query = f"UPDATE users SET username = '{new_username}' WHERE id = {target_user_id};"
        cursor.execute(query)
        conn.commit()
        session['username'] = new_username
        conn.close()

        return "Nom d'utilisateur modifié avec succès !"

    return render_template('edit.html')

#code contact
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Récupérer les données du formulaire
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        # Vous pouvez envoyer un e-mail ou enregistrer les informations dans la base de données
        # Exemple d'envoi d'e-mail (vous devez configurer un serveur SMTP, par exemple avec Flask-Mail)
        try:
            send_email(
                subject="Nouveau message de contact",
                recipient="contact@jeanrol.com",
                body=f"Nom: {name}\nEmail: {email}\n\nMessage: {message}"
            )
            flash('Votre message a été envoyé avec succès !', 'success')
        except Exception as e:
            flash('Une erreur est survenue lors de l\'envoi du message. Veuillez réessayer.', 'error')

        return redirect(url_for('contact'))

    return render_template('contact.html')


#oscommandinjectio
@app.route('/ping', methods=['GET', 'POST'])
def ping():
    if request.method == 'POST':
        target = request.form['target']
        output = os.popen(f"ping  -t 1 {target}").read()  # Dangerous: User input is directly used in a shell command
        return f"<pre>{output}</pre>"

    return '''
        <form method="post">
            Target: <input type="text" name="target">
            <input type="submit" value="Ping">
        </form>
    '''
#csrf
@app.route('/change_password')
def change_password():
    if 'user_id' not in session:
        return "Non autorisé", 403

    new_password = request.args.get('new_password')
    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET password = '{new_password}' WHERE id = {user_id};")
    conn.commit()
    conn.close()

    return "Mot de passe changé avec succès !"




# Connexion
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()

        cursor = conn.cursor()
        cursor.execute("SET client_encoding TO 'UTF8';")
        query = "SELECT id, username FROM users WHERE username = '" + username + "' AND password = '" + password + "';"
        cursor.execute(query)
        user = cursor.fetchone()
        conn.close()

        if user:
         session['user_id'] = user[0]
         session['username'] = user[1]
         return redirect(url_for('dashboard'))
        else:
         return "Identifiants incorrects."


    return render_template('login.html')

       # cursor.execute(SELECT id, username, password FROM users WHERE username = '"+username +"';")
       # user = cursor.fetchone()
       # conn.close()

        #if user and user[2] == password:  # Vérification simple du mot depasse
         #   session['user_id'] = user[0]
          #  session['username'] = user[1]
           # return redirect(url_for('dashboard'))
        #else:
         #   return "Identifiants incorrects."
    #return render_template('login.html')

# Tableau de bord
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT material_type, volume_processed, loss_rate, timestamp
        FROM sensor_data;
    ''' )
    sensor_data = cursor.fetchall()
    conn.close()

    return render_template('dashboard.html', sensor_data=sensor_data)

# Ajout de données des capteurs
@app.route('/add_sensor_data', methods=['GET', 'POST'])
def add_sensor_data():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        material_type = request.form['material_type']
        volume_processed = float(request.form['volume_processed'])
        loss_rate = float(request.form['loss_rate'])

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sensor_data (user_id, material_type, volume_processed, loss_rate)
            VALUES (%s, %s, %s, %s);
        ''', (session['user_id'], material_type, volume_processed, loss_rate))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('add_sensor_data.html')

# Génération de rapport
@app.route('/generate_report')
def generate_report():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT material_type, volume_processed, loss_rate, timestamp
        FROM sensor_data
        WHERE user_id = %s;
    ''', (session['user_id'],))
    sensor_data = cursor.fetchall()
    conn.close()

    # Générer un rapport CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Type de Matériau', 'Volume Traité (tonnes)', 'Taux de Perte (%)', 'Date'])
    for row in sensor_data:
        writer.writerow(row)

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=rapport.csv'
    response.headers['Content-type'] = 'text/csv'
    return response

# Déconnexion
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Point d'entrée de l'application
if __name__ == '__main__':
    create_tables()  # Crée les tables au démarrage
    app.run(debug=False, port=5001)
