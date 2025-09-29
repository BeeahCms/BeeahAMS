from flask import Blueprint, render_template, session, redirect, url_for, request, flash, current_app, send_from_directory
from werkzeug.utils import secure_filename
from routes.staff_routes import all_employees
import json
import os
import time

contracts_bp = Blueprint('contracts_bp', __name__)

TYPES_FILE = 'contract_types.json'
CONTRACTS_FILE = 'contracts_data.json'

def load_data(file_path):
    try:
        with open(file_path, 'r') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return []

def save_data(data, file_path):
    with open(file_path, 'w') as f: json.dump(data, f, indent=4)

@contracts_bp.route('/contracts')
def contracts_report():
    if 'username' not in session:
        return redirect(url_for('auth_bp.login'))

    role = session.get('role')
    allowed = session.get('allowed_accommodations', [])
    
    all_contracts = load_data(CONTRACTS_FILE)
    contract_types = load_data(TYPES_FILE)

    if role in ['Admin', 'Manager']:
        contracts_to_show = all_contracts
        accommodations = sorted(list(set(emp['Accommodation'] for emp in all_employees)))
    else:
        contracts_to_show = [c for c in all_contracts if c.get('accommodation') in allowed]
        accommodations = allowed
    
    return render_template('contracts.html', 
                           contracts=contracts_to_show, 
                           accommodations=accommodations,
                           contract_types=contract_types)

@contracts_bp.route('/add_contract_type', methods=['POST'])
def add_contract_type():
    if session.get('role') not in ['Admin', 'Manager']:
        flash("Access Denied.")
        return redirect(url_for('contracts_bp.contracts_report'))
    
    type_name = request.form.get('type_name')
    contract_types = load_data(TYPES_FILE)
    if type_name and type_name not in contract_types:
        contract_types.append(type_name)
        save_data(sorted(contract_types), TYPES_FILE)
        flash(f"Contract type '{type_name}' added successfully.")
    else:
        flash("Type name is empty or already exists.")
    return redirect(url_for('contracts_bp.contracts_report'))

@contracts_bp.route('/add_contract', methods=['POST'])
def add_contract():
    if session.get('role') not in ['Admin', 'Manager']:
        flash("Access Denied.")
        return redirect(url_for('contracts_bp.contracts_report'))
    
    form_data = request.form
    file = request.files.get('attachment')
    
    filename = None
    if file and file.filename:
        safe_filename = secure_filename(file.filename)
        filename = f"{int(time.time())}_{safe_filename}"
        file_path = os.path.join(current_app.config['CONTRACTS_UPLOAD_FOLDER'], filename)
        file.save(file_path)
    
    new_contract = {
        'id': int(time.time() * 1000),
        'accommodation': form_data.get('accommodation'),
        'contract_type': form_data.get('contract_type'),
        'caption': form_data.get('caption'),
        'attachment': filename
    }
    
    all_contracts = load_data(CONTRACTS_FILE)
    all_contracts.append(new_contract)
    save_data(all_contracts, CONTRACTS_FILE)
    flash("New contract added successfully!")
    return redirect(url_for('contracts_bp.contracts_report'))

@contracts_bp.route('/delete_contract/<contract_id>', methods=['POST'])
def delete_contract(contract_id):
    if session.get('role') not in ['Admin', 'Manager']:
        flash("Access Denied.")
        return redirect(url_for('contracts_bp.contracts_report'))
        
    all_contracts = load_data(CONTRACTS_FILE)
    contract_to_delete = next((c for c in all_contracts if str(c.get('id')) == str(contract_id)), None)
    
    if contract_to_delete:
        if contract_to_delete.get('attachment'):
            try:
                os.remove(os.path.join(current_app.config['CONTRACTS_UPLOAD_FOLDER'], contract_to_delete['attachment']))
            except OSError as e:
                flash(f"Error deleting file: {e}")
        
        all_contracts = [c for c in all_contracts if str(c.get('id')) != str(contract_id)]
        save_data(all_contracts, CONTRACTS_FILE)
        flash("Contract deleted successfully.")
    else:
        flash("Error: Contract not found.")
        
    return redirect(url_for('contracts_bp.contracts_report'))

@contracts_bp.route('/uploads/contracts/<filename>')
def uploaded_contract_file(filename):
    if 'username' not in session:
        return redirect(url_for('auth_bp.login'))
    return send_from_directory(current_app.config['CONTRACTS_UPLOAD_FOLDER'], filename)