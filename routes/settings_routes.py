from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from functools import wraps
import json
from routes.staff_routes import all_employees

settings_bp = Blueprint('settings_bp', __name__)
USERS_FILE = 'users.json'

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'Admin':
            flash('Access Denied: You do not have permission to view this page.')
            return redirect(url_for('auth_bp.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

@settings_bp.route('/settings')
def settings_page():
    if 'username' not in session:
        return redirect(url_for('auth_bp.login'))
    
    users = load_users()
    accommodations = sorted(list(set(emp['Accommodation'] for emp in all_employees)))
    return render_template('settings.html', users=users, accommodations=accommodations)

@settings_bp.route('/add_user', methods=['POST'])
@admin_required
def add_user():
    users = load_users()
    form_data = request.form
    username = form_data.get('username')

    if any(u['username'] == username for u in users):
        flash(f"Error: Username '{username}' already exists.")
        return redirect(url_for('settings_bp.settings_page'))

    new_user = {
        "username": username,
        "email": form_data.get('email'),
        "password": form_data.get('password'),
        "role": form_data.get('role'),
        "allowed_accommodations": request.form.getlist('allowed_accommodations')
    }
    users.append(new_user)
    save_users(users)
    flash("User added successfully!")
    return redirect(url_for('settings_bp.settings_page'))

@settings_bp.route('/edit_user/<username>', methods=['GET'])
@admin_required
def edit_user(username):
    users = load_users()
    user_to_edit = next((u for u in users if u['username'] == username), None)
    if not user_to_edit:
        flash("User not found.")
        return redirect(url_for('settings_bp.settings_page'))

    accommodations = sorted(list(set(emp['Accommodation'] for emp in all_employees)))
    return render_template('edit_user.html', user=user_to_edit, accommodations=accommodations)

@settings_bp.route('/update_user/<username>', methods=['POST'])
@admin_required
def update_user(username):
    users = load_users()
    form_data = request.form
    
    for user in users:
        if user['username'] == username:
            user['email'] = form_data.get('email', user['email'])
            user['role'] = form_data.get('role', user['role'])
            user['allowed_accommodations'] = request.form.getlist('allowed_accommodations')
            
            new_password = form_data.get('password')
            if new_password:
                user['password'] = new_password
            
            save_users(users)
            flash(f"User '{username}' updated successfully!")
            return redirect(url_for('settings_bp.settings_page'))
            
    flash("User not found.")
    return redirect(url_for('settings_bp.settings_page'))

@settings_bp.route('/delete_user/<username>', methods=['POST'])
@admin_required
def delete_user(username):
    if username == 'admin':
        flash("Error: The default admin user cannot be deleted.")
        return redirect(url_for('settings_bp.settings_page'))
        
    users = load_users()
    users = [u for u in users if u['username'] != username]
    save_users(users)
    flash(f"User '{username}' deleted successfully.")
    return redirect(url_for('settings_bp.settings_page'))