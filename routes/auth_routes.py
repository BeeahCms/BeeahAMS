from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from routes.staff_routes import all_employees

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/')
def login():
    return render_template('login.html')

@auth_bp.route('/login_action', methods=['POST'])
def login_action():
    username = request.form.get('username')
    password = request.form.get('password')
    # This should be replaced with your actual user loading logic
    if username == 'admin' and password == 'password123':
        session['username'] = username
        session['role'] = 'Admin' # Example role
        session['allowed_accommodations'] = [] # Example
        return redirect(url_for('auth_bp.dashboard'))
    else:
        flash('Invalid username or password. Please try again.')
        return redirect(url_for('auth_bp.login'))

@auth_bp.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('auth_bp.login'))

    search_query = request.args.get('search', '').lower()
    location_filter = request.args.get('location')
    status_filter = request.args.get('status')
    
    valid_employee_statuses = ['Active', 'Vacation', 'Resigned', 'Terminated']
    employee_rows = [e for e in all_employees if e.get('Status') in valid_employee_statuses]
    
    employees_to_show = employee_rows

    if search_query:
        employees_to_show = [
            emp for emp in employees_to_show 
            if search_query in str(emp.get('SAP ID', '')).lower() or 
               search_query in str(emp.get('Emp Name', '')).lower()
        ]

    if status_filter:
        if status_filter == 'Vacant':
            employees_to_show = [e for e in all_employees if e.get('Status') == 'Vacant']
        else:
            employees_to_show = [emp for emp in employees_to_show if emp.get('Status') == status_filter]
    
    if location_filter:
        employees_to_show = [emp for emp in employees_to_show if emp.get('Accommodation') == location_filter]

    locations = {}
    if employee_rows:
        locations = {emp['Accommodation']: sum(1 for e in employee_rows if e.get('Accommodation') == emp.get('Accommodation')) for emp in employee_rows if emp.get('Accommodation') != 'N/A'}
    
    stats = {
        "total": len(employee_rows),
        "vacant": sum(1 for e in all_employees if e.get('Status') == 'Vacant'),
        "on_vacation": sum(1 for e in employee_rows if e.get('Status') == 'Vacation'),
        "resigned": sum(1 for e in employee_rows if e.get('Status') == 'Resigned')
    }
    
    return render_template('dashboard.html', 
                           username=session.get('username'), 
                           employees=employees_to_show,
                           locations=locations,
                           stats=stats)

@auth_bp.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    session.pop('allowed_accommodations', None)
    return redirect(url_for('auth_bp.login'))