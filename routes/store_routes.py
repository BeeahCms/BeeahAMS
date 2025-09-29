from flask import Blueprint, render_template, session, redirect, url_for, request, flash, Response
from routes.staff_routes import all_employees
from utils.permissions import can_modify, can_access_central_store
import json
import os
import time
from collections import defaultdict
import pandas as pd
import io

store_bp = Blueprint('store_bp', __name__)

ITEMS_FILE = 'store_items.json'
INVENTORY_FILE = 'store_inventory.json'
ISSUED_FILE = 'issued_items.json'

def load_data(file_path):
    try:
        with open(file_path, 'r') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return []

def save_data(data, file_path):
    with open(file_path, 'w') as f: json.dump(data, f, indent=4)

@store_bp.route('/store')
def store_report():
    if 'username' not in session: return redirect(url_for('auth_bp.login'))

    role = session.get('role')
    allowed = session.get('allowed_accommodations', [])
    
    inventory = load_data(INVENTORY_FILE)
    master_items = load_data(ITEMS_FILE)
    issued_items = load_data(ISSUED_FILE)
    search_query = request.args.get('search', '').lower()

    all_locations = ['Central Store'] + sorted(list(set(emp['Accommodation'] for emp in all_employees)))
    summary = defaultdict(lambda: {loc: {'stock': 0, 'issued': 0} for loc in all_locations})

    for item in inventory:
        if 'item_name' in item and 'accommodation' in item:
            summary[item['item_name']][item['accommodation']]['stock'] = item.get('quantity', 0)
    
    for item in issued_items:
        if 'item_name' in item and 'accommodation' in item:
            summary[item['item_name']][item['accommodation']]['issued'] += item.get('quantity', 0)

    if search_query:
        filtered_summary = {
            item_name: locations for item_name, locations in summary.items()
            if search_query in item_name.lower()
        }
        summary = filtered_summary

    if role in ['Admin', 'Manager']:
        visible_locations = all_locations
        accommodations_for_forms = all_locations
    else:
        visible_locations = [loc for loc in allowed if loc in all_locations]
        if not visible_locations and allowed: visible_locations = allowed
        accommodations_for_forms = allowed
    
    return render_template('store.html', 
                           summary=dict(summary),
                           all_locations=all_locations,
                           visible_locations=visible_locations,
                           accommodations=accommodations_for_forms,
                           master_items=master_items)

@store_bp.route('/add_store_item', methods=['POST'])
def add_store_item():
    if session.get('role') not in ['Admin', 'Manager']:
        flash("Access Denied.")
        return redirect(url_for('store_bp.store_report'))

    item_name = request.form.get('item_name')
    master_items = load_data(ITEMS_FILE)
    if item_name and item_name not in master_items:
        master_items.append(item_name)
        save_data(sorted(master_items), ITEMS_FILE)
        flash(f"Master Item '{item_name}' added.")
    else:
        flash("Item name is empty or already exists.")
    return redirect(url_for('store_bp.store_report'))

@store_bp.route('/upload_master_items', methods=['POST'])
def upload_master_items():
    if session.get('role') not in ['Admin', 'Manager']:
        flash("Access Denied.")
        return redirect(url_for('store_bp.store_report'))

    if 'master_items_file' not in request.files:
        flash('No file part in the request.')
        return redirect(url_for('store_bp.store_report'))

    file = request.files['master_items_file']
    if file.filename == '':
        flash('No file selected for upload.')
        return redirect(url_for('store_bp.store_report'))

    if file and file.filename.endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(file)
            if 'ItemName' not in df.columns:
                flash("Error: Excel file must have a column named 'ItemName'.")
                return redirect(url_for('store_bp.store_report'))

            master_items = load_data(ITEMS_FILE)
            master_items_set = set(master_items)
            
            new_items = df['ItemName'].dropna().astype(str).tolist()
            added_count = 0

            for item in new_items:
                if item not in master_items_set:
                    master_items_set.add(item)
                    added_count += 1
            
            save_data(sorted(list(master_items_set)), ITEMS_FILE)
            flash(f"{added_count} new master items added successfully. Duplicates were skipped.")
        except Exception as e:
            flash(f"Error processing file: {e}")
    else:
        flash("Invalid file format. Please upload an Excel file.")

    return redirect(url_for('store_bp.store_report'))

@store_bp.route('/receive_stock', methods=['POST'])
def receive_stock():
    form_data = request.form
    accommodation = form_data.get('accommodation')

    if accommodation == 'Central Store' and not can_access_central_store():
        flash("Access Denied to Central Store.")
        return redirect(url_for('store_bp.store_report'))
    if not can_modify(accommodation):
        return redirect(url_for('store_bp.store_report'))
        
    inventory = load_data(INVENTORY_FILE)
    item_name = form_data.get('item_name')
    quantity = int(form_data.get('quantity', 0))
    
    item_found = False
    for item in inventory:
        if item.get('accommodation') == accommodation and item.get('item_name') == item_name:
            item['quantity'] = item.get('quantity', 0) + quantity
            item_found = True
            break
    if not item_found:
        inventory.append({'accommodation': accommodation, 'item_name': item_name, 'quantity': quantity, 'remarks': ''})
        
    save_data(inventory, INVENTORY_FILE)
    flash(f"Received {quantity} of {item_name} at {accommodation}.")
    return redirect(url_for('store_bp.store_report'))

@store_bp.route('/distribute_stock', methods=['POST'])
def distribute_stock():
    if not can_access_central_store():
        flash("Access Denied: Only Central Store users can distribute stock.")
        return redirect(url_for('store_bp.store_report'))
    
    form_data = request.form
    target_acc = form_data.get('target_accommodation')
    item_name = form_data.get('item_name_dist')
    quantity = int(form_data.get('quantity_dist', 0))
    remarks = f"Received by {form_data.get('emp_name')} ({form_data.get('sap_id')}). Remarks: {form_data.get('remarks')}"
    inventory = load_data(INVENTORY_FILE)

    central_stock = next((item for item in inventory if item.get('accommodation') == 'Central Store' and item.get('item_name') == item_name), None)
    
    if not central_stock or central_stock.get('quantity', 0) < quantity:
        flash(f"Not enough stock for {item_name} in Central Store.")
        return redirect(url_for('store_bp.store_report'))
        
    central_stock['quantity'] -= quantity
    
    target_stock = next((item for item in inventory if item.get('accommodation') == target_acc and item.get('item_name') == item_name), None)
    if target_stock:
        target_stock['quantity'] = target_stock.get('quantity', 0) + quantity
        target_stock['remarks'] = remarks
    else:
        inventory.append({'accommodation': target_acc, 'item_name': item_name, 'quantity': quantity, 'remarks': remarks})
        
    save_data(inventory, INVENTORY_FILE)
    flash(f"Distributed {quantity} of {item_name} to {target_acc}.")
    return redirect(url_for('store_bp.store_report'))

@store_bp.route('/issue_to_employee', methods=['POST'])
def issue_to_employee():
    form_data = request.form
    accommodation = form_data.get('accommodation_issue')
    if not can_modify(accommodation):
        return redirect(url_for('store_bp.store_report'))
        
    item_name = form_data.get('item_name_issue')
    quantity = int(form_data.get('quantity_issue', 0))
    inventory = load_data(INVENTORY_FILE)
    
    stock = next((item for item in inventory if item.get('accommodation') == accommodation and item.get('item_name') == item_name), None)
    if not stock or stock.get('quantity', 0) < quantity:
        flash(f"Not enough stock for {item_name} at {accommodation}.")
        return redirect(url_for('store_bp.store_report'))
        
    stock['quantity'] -= quantity
    save_data(inventory, INVENTORY_FILE)
    
    issued_items = load_data(ISSUED_FILE)
    new_issue = {
        'id': int(time.time() * 1000), 'accommodation': accommodation,
        'item_name': item_name, 'quantity': quantity,
        'sap_id': form_data.get('sap_id'), 'emp_name': form_data.get('emp_name'),
        'designation': form_data.get('designation'), 'department': form_data.get('department'),
        'issue_date': form_data.get('issue_date'), 'remarks': form_data.get('remarks')
    }
    issued_items.append(new_issue)
    save_data(issued_items, ISSUED_FILE)
    
    flash(f"Issued {quantity} of {item_name} to {form_data.get('emp_name')}.")
    return redirect(url_for('store_bp.store_report'))

@store_bp.route('/issued_details/<accommodation>/<item_name>')
def issued_details(accommodation, item_name):
    if 'username' not in session: return redirect(url_for('auth_bp.login'))
    if not can_modify(accommodation): return redirect(url_for('store_bp.store_report'))
    
    issued_items = load_data(ISSUED_FILE)
    filtered_records = [item for item in issued_items if item.get('accommodation') == accommodation and item.get('item_name') == item_name]
    return render_template('issued_details.html', issued_records=filtered_records, accommodation=accommodation, item_name=item_name)

@store_bp.route('/download_issued_details/<accommodation>/<item_name>', methods=['POST'])
def download_issued_details(accommodation, item_name):
    if 'username' not in session: return redirect(url_for('auth_bp.login'))
    if not can_modify(accommodation): return redirect(url_for('store_bp.store_report'))
    
    issued_items = load_data(ISSUED_FILE)
    records_to_download = [item for item in issued_items if item.get('accommodation') == accommodation and item.get('item_name') == item_name]
    
    df = pd.DataFrame(records_to_download)
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Issued_Details')
    writer.close()
    output.seek(0)
    
    return Response(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={"Content-Disposition": f"attachment;filename=issued_{item_name}_{accommodation}.xlsx"})

@store_bp.route('/download_store_report', methods=['POST'])
def download_store_report():
    if 'username' not in session: return redirect(url_for('auth_bp.login'))

    acc_filter = request.form.get('accommodation_report')
    report_type = request.form.get('report_type')
    
    if acc_filter and not can_modify(acc_filter):
        return redirect(url_for('store_bp.store_report'))

    inventory = load_data(INVENTORY_FILE)
    issued = load_data(ISSUED_FILE)
    
    if acc_filter:
        inventory = [i for i in inventory if i.get('accommodation') == acc_filter]
        issued = [i for i in issued if i.get('accommodation') == acc_filter]

    if report_type == 'Stock':
        df = pd.DataFrame(inventory)
    elif report_type == 'Issued':
        df = pd.DataFrame(issued)
    elif report_type == 'Balance':
        summary = defaultdict(lambda: {'stock': 0, 'issued': 0})
        for item in inventory: summary[item['item_name']]['stock'] += item.get('quantity', 0)
        for item in issued: summary[item['item_name']]['issued'] += item.get('quantity', 0)
        balance_data = [{'item_name': name, 'balance': data['stock'] - data['issued']} for name, data in summary.items()]
        df = pd.DataFrame(balance_data)
    else:
        flash("Invalid report type selected.")
        return redirect(url_for('store_bp.store_report'))
    
    if df.empty:
        flash("No data found for the selected report.")
        return redirect(url_for('store_bp.store_report'))

    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name=report_type)
    writer.close()
    output.seek(0)
    
    return Response(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={"Content-Disposition": f"attachment;filename={acc_filter or 'Total'}_{report_type}_Report.xlsx"})