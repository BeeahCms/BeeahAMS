from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from utils.permissions import can_modify
import pandas as pd
from collections import Counter
import json
import os
import time

staff_bp = Blueprint('staff_bp', __name__)

DATA_FILE = 'data.json'

def load_data_from_json():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_data_to_json(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

all_employees = load_data_from_json()

def load_countries_data():
    file_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'data', 'countries.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

countries_data = load_countries_data()

@staff_bp.route('/get_employee_details/<sap_id>')
def get_employee_details(sap_id):
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    employee_details = {}
    for emp in all_employees:
        try:
            if int(float(emp.get('SAP ID'))) == int(float(sap_id)):
                employee_details = {
                    "Emp Name": emp.get('Emp Name'),
                    "Designation": emp.get('Designation'),
                    "Department": emp.get('Department')
                }
                break
        except (ValueError, TypeError):
            continue
    
    return jsonify(employee_details)

@staff_bp.route('/upload', methods=['POST'])
def upload_file():
    global all_employees
    if 'fileUpload' not in request.files:
        flash('No file part in the request.')
        return redirect(url_for('acc_bp.accommodation_data'))
    
    file = request.files['fileUpload']
    
    if file.filename == '':
        flash('No file selected.')
        return redirect(url_for('acc_bp.accommodation_data'))

    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        try:
            df = pd.read_excel(file).fillna('')
            df.dropna(subset=['SAP ID'], inplace=True)
            df.drop_duplicates(subset=['SAP ID'], keep='first', inplace=True)

            required_columns = ['Accommodation', 'Room', 'SAP ID', 'Emp Name', 'Designation', 'Status', 'Department', 'Nationality']
            
            if not all(col in df.columns for col in required_columns):
                flash(f'Excel file is missing required columns. Please ensure these columns exist: {required_columns}')
                return redirect(url_for('acc_bp.accommodation_data'))

            new_data = df.to_dict('records')
            all_employees.clear()
            all_employees.extend(new_data)
            save_data_to_json(all_employees)
            flash('File with duplicates removed was uploaded successfully!')
        except Exception as e:
            flash(f"Error processing file: {e}")
    else:
        flash('Invalid file format. Please upload an Excel file (.xlsx, .xls).')

    return redirect(url_for('acc_bp.accommodation_data'))

@staff_bp.route('/add_accommodation_data', methods=['POST'])
def add_accommodation_data():
    global all_employees
    if 'addAccomFile' not in request.files:
        flash('No file part in the request.')
        return redirect(url_for('acc_bp.accommodation_data'))

    file = request.files['addAccomFile']
    if file.filename == '':
        flash('No file selected for adding.')
        return redirect(url_for('acc_bp.accommodation_data'))

    if file and (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        try:
            df = pd.read_excel(file).fillna('')
            df.dropna(subset=['SAP ID'], inplace=True)
            new_data = df.to_dict('records')

            existing_sap_ids = {str(emp.get('SAP ID')) for emp in all_employees}
            added_count = 0
            skipped_count = 0

            for record in new_data:
                sap_id = str(record.get('SAP ID'))
                if sap_id and sap_id not in existing_sap_ids:
                    all_employees.append(record)
                    existing_sap_ids.add(sap_id)
                    added_count += 1
                else:
                    skipped_count += 1
            
            save_data_to_json(all_employees)
            flash(f"Data added successfully! {added_count} new records added, {skipped_count} duplicates skipped.")
        except Exception as e:
            flash(f"Error processing file: {e}")
    else:
        flash('Invalid file format. Please upload an Excel file (.xlsx, .xls).')
    
    return redirect(url_for('acc_bp.accommodation_data'))

@staff_bp.route('/manage_accommodation', methods=['POST'])
def manage_accommodation():
    global all_employees
    form_data = request.form
    source_acc = form_data.get('source_accommodation')
    action = form_data.get('action')

    if not source_acc:
        flash("Please select a source accommodation.")
        return redirect(url_for('acc_bp.accommodation_data'))

    if action == 'remove':
        original_count = len(all_employees)
        all_employees = [emp for emp in all_employees if emp.get('Accommodation') != source_acc]
        removed_count = original_count - len(all_employees)
        save_data_to_json(all_employees)
        flash(f"Successfully removed {removed_count} records from {source_acc}.")
    
    elif action == 'shift':
        target_acc = form_data.get('target_accommodation')
        if not target_acc or source_acc == target_acc:
            flash("Please select a valid and different target accommodation.")
            return redirect(url_for('acc_bp.accommodation_data'))
        
        shifted_count = 0
        for emp in all_employees:
            if emp.get('Accommodation') == source_acc:
                emp['Accommodation'] = target_acc
                shifted_count += 1
        save_data_to_json(all_employees)
        flash(f"Successfully shifted {shifted_count} records from {source_acc} to {target_acc}.")

    return redirect(url_for('acc_bp.accommodation_data'))

@staff_bp.route('/staff/<sap_id>')
def staff_details(sap_id):
    if 'username' not in session:
        return redirect(url_for('auth_bp.login'))
    
    employee_to_show = None
    for emp in all_employees:
        if emp.get('SAP ID'):
            try:
                if int(float(emp.get('SAP ID'))) == int(float(sap_id)):
                    employee_to_show = emp
                    break
            except (ValueError, TypeError):
                continue
            
    if not employee_to_show:
        flash(f"No employee found with SAP ID: {sap_id}")
        return redirect(url_for('auth_bp.dashboard'))
        
    role = session.get('role')
    if role in ['Admin', 'Manager']:
        accommodations = sorted(list(set(emp['Accommodation'] for emp in all_employees if emp.get('Accommodation'))))
    else:
        accommodations = session.get('allowed_accommodations', [])
        
    departments = sorted(list(set(emp.get('Department') for emp in all_employees if emp.get('Department'))))

    return render_template(
        'staff_details.html',
        employee=employee_to_show,
        accommodations=accommodations,
        departments=departments,
        countries=countries_data
    )
@staff_bp.route('/update_staff/<sap_id>', methods=['POST'])
def update_staff(sap_id):
    employee_to_update = None
    for emp in all_employees:
        if emp.get('SAP ID'):
            try:
                if int(float(emp.get('SAP ID'))) == int(float(sap_id)):
                    employee_to_update = emp
                    break
            except (ValueError, TypeError):
                continue

    if not employee_to_update:
        flash('Could not find employee to update.')
        return redirect(url_for('auth_bp.dashboard'))

    if not can_modify(employee_to_update.get('Accommodation')):
        return redirect(url_for('staff_bp.staff_details', sap_id=sap_id))
    
    form_data = request.form
    employee_to_update.update({
        'Emp Name': form_data.get('emp_name'),
        'Designation': form_data.get('designation'),
        'Department': form_data.get('department'),
        'Nationality': form_data.get('nationality'),
        'Status': form_data.get('status')
    })
    save_data_to_json(all_employees)
    flash('Employee details updated successfully!')
    return redirect(url_for('staff_bp.staff_details', sap_id=sap_id))

@staff_bp.route('/checkout_staff/<sap_id>', methods=['POST'])
def checkout_staff(sap_id):
    global all_employees
    for i, emp in enumerate(all_employees):
        if emp.get('SAP ID'):
            try:
                if int(float(emp.get('SAP ID'))) == int(float(sap_id)):
                    if not can_modify(emp.get('Accommodation')):
                        return redirect(url_for('staff_bp.staff_details', sap_id=sap_id))
                    
                    ex_employee_record = emp.copy()
                    ex_employee_record.update({'Status': 'Checked-Out', 'Accommodation': 'N/A', 'Room': 'N/A'})
                    
                    all_employees[i] = {
                        'Accommodation': emp.get('Accommodation'), 'Room': emp.get('Room'), 'SAP ID': '', 
                        'Emp Name': '', 'Designation': '', 'Department': '', 'Status': 'Vacant', 'Nationality': ''
                    }
                    all_employees.append(ex_employee_record)
                    save_data_to_json(all_employees)
                    flash(f"Employee {sap_id} has been checked out.")
                    return redirect(url_for('auth_bp.dashboard'))
            except (ValueError, TypeError):
                continue
            
    flash('Could not find employee to check out.')
    return redirect(url_for('auth_bp.dashboard'))
@staff_bp.route('/shift_staff/<sap_id>', methods=['POST'])
def shift_staff(sap_id):
    global all_employees
    
    original_record_index = -1
    employee_data = None

    for i, emp in enumerate(all_employees):
        if emp.get('SAP ID'):
            try:
                if int(float(emp.get('SAP ID'))) == int(float(sap_id)):
                    original_record_index = i
                    employee_data = emp.copy()
                    break
            except (ValueError, TypeError):
                continue

    if not employee_data:
        flash('Shift failed. Could not find original employee.')
        return redirect(url_for('auth_bp.dashboard'))

    if not can_modify(employee_data.get('Accommodation')):
        return redirect(url_for('staff_bp.staff_details', sap_id=sap_id))
    
    new_acc = request.form.get('new_accommodation')
    new_room = request.form.get('new_room')
    
    target_record_index = next((i for i, emp in enumerate(all_employees) if emp.get('Accommodation') == new_acc and emp.get('Room') == new_room and emp.get('Status') == 'Vacant'), None)
            
    if original_record_index != -1 and target_record_index is not None:
        all_employees[target_record_index].update(employee_data)
        all_employees[target_record_index].update({'Accommodation': new_acc, 'Room': new_room, 'Status': 'Active'})
        
        all_employees[original_record_index] = {
            'Accommodation': employee_data.get('Accommodation'), 'Room': employee_data.get('Room'),
            'SAP ID': '', 'Emp Name': '', 'Designation': '', 'Department': '', 'Status': 'Vacant', 'Nationality': ''
        }
        save_data_to_json(all_employees)
        flash(f"Employee {sap_id} shifted successfully.")
        return redirect(url_for('staff_bp.staff_details', sap_id=sap_id))

    flash('Shift failed. Could not find target vacant room.')
    return redirect(url_for('staff_bp.staff_details', sap_id=sap_id))
@staff_bp.route('/add_staff', methods=['POST'])
def add_staff():
    global all_employees
    form_data = request.form
    acc_name = form_data.get('accommodation_name')

    if not can_modify(acc_name):
        return redirect(url_for('acc_bp.accommodation_data'))

    new_sap_id = form_data.get('sap_id')

    for existing_emp in all_employees:
        try:
            if existing_emp.get('SAP ID') and int(float(existing_emp.get('SAP ID'))) == int(new_sap_id):
                flash("Error: Staff already exist in the data.")
                return redirect(url_for('acc_bp.accommodation_data'))
        except (ValueError, TypeError): continue

    room_num = form_data.get('room_number')
    for emp in all_employees:
        if emp.get('Accommodation') == acc_name and emp.get('Room') == room_num and emp.get('Status') == 'Vacant':
            emp.update({
                'SAP ID': int(new_sap_id), 'Emp Name': form_data.get('emp_name'),
                'Designation': form_data.get('designation'), 'Department': form_data.get('department'),
                'Nationality': form_data.get('nationality'), 'Status': 'Active'
            })
            save_data_to_json(all_employees)
            flash(f"Successfully added {emp['Emp Name']}.")
            return redirect(url_for('acc_bp.accommodation_data'))
    
    flash("Error: Could not find the selected vacant room.")
    return redirect(url_for('acc_bp.accommodation_data'))

@staff_bp.route('/get_vacant_rooms/<accommodation_name>')
def get_vacant_rooms(accommodation_name):
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    vacant_rooms = [emp['Room'] for emp in all_employees if emp.get('Accommodation') == accommodation_name and emp.get('Status') == 'Vacant']
    return jsonify(sorted(list(set(vacant_rooms))))

@staff_bp.route('/get_country_details/<country_name>')
def get_country_details(country_name):
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    for country in countries_data:
        if country['name'] == country_name:
            states = [state['name'] for state in country.get('states', [])]
            phone_code = country.get('phone_code', '')
            return jsonify({"states": sorted(states), "phone_code": phone_code})
    
    return jsonify({"states": [], "phone_code": ""})
