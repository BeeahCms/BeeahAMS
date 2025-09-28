from flask import Blueprint, render_template, session, redirect, url_for, request, flash, current_app, send_from_directory
from werkzeug.utils import secure_filename
from routes.staff_routes import all_employees
from utils.permissions import can_modify
import json
import os
import time

amcs_bp = Blueprint('amcs_bp', __name__)

DATA_DIR = os.environ.get('RENDER_DATA_DIR', '.')
DATA_FILE = os.path.join(DATA_DIR, 'amcs_data.json')

def load_amcs_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(DATA_FILE, 'r') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return []
def save_amcs_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

all_amcs = load_amcs_data()

@amcs_bp.route('/amcs')
def amcs_report():
    if 'username' not in session:
        return redirect(url_for('auth_bp.login'))
        
    role = session.get('role')
    allowed = session.get('allowed_accommodations', [])
    
    if role in ['Admin', 'Manager']:
        data_to_process = all_amcs
        accommodations = sorted(list(set(emp['Accommodation'] for emp in all_employees)))
    else:
        data_to_process = [amc for amc in all_amcs if amc.get('accommodation') in allowed]
        accommodations = allowed

    vendor_filter = request.args.get('vendor')
    type_filter = request.args.get('type')
    accommodation_filter = request.args.get('accommodation')

    amcs_to_show = data_to_process
    if vendor_filter:
        amcs_to_show = [a for a in amcs_to_show if a.get('vendor') == vendor_filter]
    if type_filter:
        amcs_to_show = [a for a in amcs_to_show if a.get('type') == type_filter]
    if accommodation_filter:
        amcs_to_show = [a for a in amcs_to_show if a.get('accommodation') == accommodation_filter]
    
    vendors = sorted(list(set(a.get('vendor') for a in data_to_process if a.get('vendor'))))
    types = sorted(list(set(a.get('type') for a in data_to_process if a.get('type'))))

    return render_template('amcs.html', 
                           amcs_records=amcs_to_show, 
                           vendors=vendors, 
                           types=types,
                           accommodations=accommodations)

@amcs_bp.route('/add_amc', methods=['POST'])
def add_amc():
    form_data = request.form
    accommodation = form_data.get('accommodation_name')
    if not can_modify(accommodation):
        return redirect(url_for('amcs_bp.amcs_report'))
        
    global all_amcs
    file = request.files.get('attachment')
    
    filename = None
    if file and file.filename:
        safe_filename = secure_filename(file.filename)
        filename = f"{int(time.time())}_{safe_filename}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

    new_amc = {
        'id': int(time.time() * 1000), 'accommodation': accommodation,
        'vendor': form_data.get('vendor'), 'service_date': form_data.get('service_date'),
        'expiry_date': form_data.get('expiry_date'), 'type': form_data.get('type'),
        'remarks': form_data.get('remarks'), 'attachment': filename
    }
    
    all_amcs.append(new_amc)
    save_amcs_data(all_amcs)
    flash('New AMC Service added successfully!')
    return redirect(url_for('amcs_bp.amcs_report'))

@amcs_bp.route('/uploads/amcs/<filename>')
def uploaded_file(filename):
    if 'username' not in session:
        return redirect(url_for('auth_bp.login'))
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)