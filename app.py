from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response, flash
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import cv2
from utils.detection import BulletDetector
from db_config import DB_CONFIG

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

detection_state = {
    'active': False,
    'bullets_shot': 0,
    'bullets_detected': 0,
    'user_id': None,
    'camera_source': '0'  # Default camera source
}

# Instanciation de BulletDetector 
detector = BulletDetector(camera_source=detection_state['camera_source'])


import logging
def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Erreur de connexion à la base de données : {e}")
        raise Exception("Impossible de se connecter à la base de données.")

# Admin signup
@app.route("/")
def index():
    return redirect(url_for('login'))

@app.route('/admin/signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        hashed_password = generate_password_hash(password)
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Check if admin exists
            cur.execute("SELECT * FROM admins WHERE username = %s", (username,))
            if cur.fetchone():
                flash('Ce nom d\'utilisateur existe déjà', 'error')
                return redirect(url_for('admin_signup'))
            
            # Create new admin
            cur.execute(
                "INSERT INTO admins (username, password_hash, full_name) VALUES (%s, %s, %s)",
                (username, hashed_password, full_name)
            )
            conn.commit()
            
            flash('Inscription admin réussie! Veuillez vous connecter', 'success')
            return redirect(url_for('admin_login'))
            
        except Exception as e:
            conn.rollback()
            flash(f"Erreur lors de l'inscription: {str(e)}", 'error')
        finally:
            cur.close()
            conn.close()
    
    return render_template('admin_signup.html')

# Admin login
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM admins WHERE username = %s", (username,))
        admin = cur.fetchone()
        conn.close()
        
        if admin and check_password_hash(admin[2], password):
            session['admin_username'] = username
            session['admin_full_name'] = admin['full_name']
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Identifiants incorrects', 'error')
    
    return render_template('admin_login.html')

# Admin logout
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_username', None)
    session.pop('admin_full_name', None)
    return redirect(url_for('admin_login'))

# Admin dashboard (list of users)
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_username' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Get list of active users
    cur.execute("SELECT id, matricule, full_name FROM users WHERE is_active = TRUE ORDER BY matricule")
    users = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('admin_dashboard.html', users=users, admin_name=session['admin_full_name'])

# Admin add user
@app.route('/admin/add_user', methods=['GET', 'POST'])
def add_user():
    if 'admin_username' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        matricule = request.form['matricule']
        full_name = request.form['full_name']
        
        if not matricule or not full_name:
            flash('Matricule et nom complet sont requis', 'error')
            return redirect(url_for('add_user'))
        
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # Check if matricule exists
            cur.execute("SELECT * FROM users WHERE matricule = %s", (matricule,))
            if cur.fetchone():
                flash('Ce matricule existe déjà', 'error')
                return redirect(url_for('add_user'))
            
            # Insert new user
            cur.execute(
                "INSERT INTO users (matricule, full_name) VALUES (%s, %s)",
                (matricule, full_name)
            )
            conn.commit()
            flash('Utilisateur ajouté avec succès', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            conn.rollback()
            flash(f"Erreur lors de l'ajout: {str(e)}", 'error')
        finally:
            cur.close()
            conn.close()
    
    return render_template('add_user.html')

# Admin view user dashboard
@app.route('/admin/user_dashboard/<int:user_id>')
def admin_user_dashboard(user_id):
    if 'admin_username' not in session:
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Get user info
    cur.execute("SELECT id, matricule, full_name FROM users WHERE id = %s AND is_active = TRUE", (user_id,))
    user = cur.fetchone()
    if not user:
        flash('Utilisateur non trouvé ou inactif', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Get user sessions
    cur.execute('''
        SELECT id, session_date, bullets_shot, bullets_detected, accuracy
        FROM shooting_sessions 
        WHERE user_id = %s 
        ORDER BY session_date DESC
    ''', (user_id,))
    sessions = cur.fetchall()
    
    # Calculate accuracy if not present in the database
    formatted_sessions = []
    for sess in sessions:  # Renamed 'session' to 'sess' to avoid shadowing Flask's 'session'
        session_dict = dict(sess)
        if session_dict['accuracy'] is None and session_dict['bullets_shot'] > 0:
            session_dict['accuracy'] = session_dict['bullets_detected'] / session_dict['bullets_shot']
        elif session_dict['accuracy'] is None:
            session_dict['accuracy'] = 0
        formatted_sessions.append(session_dict)
    
    # Get overall statistics
    cur.execute('''
        SELECT 
            SUM(bullets_shot) as total_shot, 
            SUM(bullets_detected) as total_detected,
            AVG(accuracy) as avg_accuracy
        FROM shooting_sessions 
        WHERE user_id = %s
    ''', (user_id,))
    stats = cur.fetchone()
    
    # Ensure stats are not None
    stats_dict = dict(stats) if stats else {'total_shot': 0, 'total_detected': 0, 'avg_accuracy': 0}
    if stats_dict['avg_accuracy'] is None:
        stats_dict['avg_accuracy'] = 0
    
    cur.close()
    conn.close()
    
    return render_template('dashboard.html', 
                         user=user,
                         sessions=formatted_sessions,
                         stats=stats_dict,
                         is_admin=True)

# User login 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        matricule = request.form['matricule']
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM users WHERE matricule = %s ", (matricule,))
        user = cur.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['user_matricule'] = matricule
            session['user_full_name'] = user['full_name']
            return redirect(url_for('detection'))
        else:
            flash('Matricule invalide ou utilisateur inactif', 'error')
    
    return render_template('login.html')

# User logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_matricule', None)
    session.pop('user_full_name', None)
    return redirect(url_for('login'))

# Home route
@app.route('/')
def home():
    if 'admin_username' in session:
        return redirect(url_for('admin_dashboard'))
    if 'user_id' in session:
        return redirect(url_for('detection'))
    return redirect(url_for('login'))

# User dashboard (restricted)
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        flash('Accès interdit. Les utilisateurs ne peuvent accéder qu\'à la page de détection.', 'error')
        return redirect(url_for('detection'))
    return redirect(url_for('login'))

# Detection page
@app.route('/detection', methods=['GET', 'POST'])
def detection():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if 'admin_username' in session:
        flash('Les admins ne peuvent pas démarrer de sessions de détection.', 'error')
        return redirect(url_for('admin_dashboard'))
    return render_template('detection.html', user_full_name=session['user_full_name'])

@app.route('/video_feed')
def video_feed():
    global detection_state
    
    if 'user_id' not in session:
        return Response('Non connecté', status=401)
    
    # Activate detection with the selected camera source
    detection_state = {
        'active': True,
        'bullets_shot': 0,
        'bullets_detected': 0,
        'user_id': session['user_id'],
        'camera_source': detection_state.get('camera_source', '0'),  # Par défaut, caméra 0
        'need_calibration': False,
        'request_calibration': False
    }
    
    return Response(detector.generate_frames(detection_state),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_detection', methods=['POST'])
def start_detection():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'})
    
    data = request.get_json()
    bullets_shot = data.get('bullets_shot', 0)
    camera_source = data.get('camera_source', '0')  # Récupérer la valeur entrée par l'utilisateur
    
    # Mettre à jour l'état global
    detection_state['active'] = True
    detection_state['bullets_shot'] = bullets_shot
    detection_state['bullets_detected'] = 0
    detection_state['user_id'] = session['user_id']
    detection_state['camera_source'] = camera_source  # Mettre à jour avec la valeur entrée
    
    # Mettre à jour la source de la caméra dans le détecteur
    detector.camera_source = camera_source  # Assigner la nouvelle valeur
    
    return jsonify({'status': 'success'})
    
@app.route('/detection_updates')
def detection_updates():
    def event_stream():
        while True:
            if detection_state['active']:
                data = {
                    'detected': detection_state['bullets_detected'],
                    'shot': detection_state['bullets_shot']
                }
                yield f"data: {json.dumps(data)}\n\n"
    
    return Response(event_stream(), mimetype="text/event-stream")



@app.route('/stop_detection', methods=['POST'])
def stop_detection():
    global detection_state
    detection_state['active'] = False
    return jsonify({'status': 'success'})

@app.route('/save_results', methods=['POST'])
def save_results():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'})
    
    data = request.get_json()
    bullets_shot = data.get('bullets_shot', 0)
    bullets_detected = data.get('bullets_detected', 0)
    accuracy = (bullets_detected / bullets_shot) if bullets_shot > 0 else 0
    
    
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT INTO shooting_sessions (user_id, bullets_shot, bullets_detected,accuracy)
            VALUES (%s, %s, %s,%s)
        ''', (session['user_id'], bullets_shot, bullets_detected,accuracy))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        cur.close()
        conn.close()
@app.route('/update_camera_source', methods=['POST'])
def update_camera_source():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'})
    
    data = request.get_json()
    camera_source = data.get('camera_source', '0')
    
    # Mettre à jour la source de la caméra
    detection_state['camera_source'] = camera_source
    detector.camera_source = camera_source
    detector.close_camera()  # Forcer la fermeture de l'ancienne caméra
    
    return jsonify({'status': 'success'})

@app.route('/filter_sessions', methods=['POST'])
def filter_sessions():
    if 'admin_username' not in session:
        return jsonify({'status': 'error', 'message': 'Not authorized'})
    
    data = request.get_json()
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    user_id = data.get('user_id')
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    query = '''
        SELECT id, session_date, bullets_shot, bullets_detected, accuracy
        FROM shooting_sessions 
        WHERE user_id = %s
    '''
    params = [user_id]
    
    if start_date and end_date:
        query += ' AND session_date BETWEEN %s AND %s'
        params.extend([start_date, end_date + ' 23:59:59'])
    elif start_date:
        query += ' AND session_date >= %s'
        params.append(start_date)
    elif end_date:
        query += ' AND session_date <= %s'
        params.append(end_date + ' 23:59:59')
    
    query += ' ORDER BY session_date DESC'
    
    cur.execute(query, params)
    sessions = cur.fetchall()
    
    # Calculate accuracy if absent
    formatted_sessions = []
    for sess in sessions:  # Renamed 'session' to 'sess' to avoid shadowing Flask's 'session'
        session_dict = dict(sess)
        if session_dict['accuracy'] is None and session_dict['bullets_shot'] > 0:
            session_dict['accuracy'] = session_dict['bullets_detected'] / session_dict['bullets_shot']
        elif session_dict['accuracy'] is None:
            session_dict['accuracy'] = 0
        formatted_sessions.append(session_dict)
    
    cur.close()
    conn.close()
    
    return jsonify({
        'status': 'success',
        'sessions': formatted_sessions
    })

@app.route('/get_session_details')
def get_session_details():
    if 'admin_username' not in session:
        return jsonify({'status': 'error', 'message': 'Not authorized'})
    
    session_id = request.args.get('id')
    user_id = request.args.get('user_id')
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('''
        SELECT session_date, bullets_shot, bullets_detected, accuracy
        FROM shooting_sessions 
        WHERE id = %s AND user_id = %s
    ''', (session_id, user_id))
    
    session_data = cur.fetchone()
    
    if session_data:
        session_dict = dict(session_data)
        if session_dict['accuracy'] is None and session_dict['bullets_shot'] > 0:
            session_dict['accuracy'] = session_dict['bullets_detected'] / session_dict['bullets_shot']
        elif session_dict['accuracy'] is None:
            session_dict['accuracy'] = 0
        cur.close()
        conn.close()
        return jsonify({'status': 'success', **session_dict})
    else:
        cur.close()
        conn.close()
        return jsonify({'status': 'error', 'message': 'Session not found'})

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8080,debug=True)
