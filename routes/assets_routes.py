from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify, Response
from routes.staff_routes import all_employees
from utils.permissions import can_modify
import json
import os
import time
import pandas as pd
import io

assets_bp = Blueprint('assets_bp', __name__)

DATA_FILE = 'assets_data.json'

def load_assets_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_assets_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

all_assets = load_assets_data()

@assets_bp.route('/assets')
def assets_report():
    if 'username' not in session:
        return redirect(url_for('auth_bp.login'))

    role = session.get('role')
    allowed = session.get('allowed_accommodations', [])
    
    if role in ['Admin', 'Manager']:
        data_to_process = all_assets
        accommodations = sorted(list(set(emp['Accommodation'] for emp in all_employees)))
    else:
        data_to_process = [asset for asset in all_assets if asset.get('accommodation') in allowed]
        accommodations = allowed
    
    status_filter = request.args.get('status')
    assets_to_show = data_to_process
    if status_filter:
        assets_to_show = [asset for asset in data_to_process if asset.get('status') == status_filter]

    stats = {
        'Available': sum(asset.get('quantity', 0) for asset in data_to_process if asset.get('status') == 'Available'),
        'Scrap': sum(asset.get('quantity', 0) for asset in data_to_process if asset.get('status') == 'Scrap')
    }
    
    return render_template('assets.html', assets=assets_to_show, stats=stats, accommodations=accommodations)

@assets_bp.route('/add_asset', methods=['POST'])
def add_asset():
    form_data = request.form
    accommodation = form_data.get('accommodation')
    if not can_modify(accommodation):
        return redirect(url_for('assets_bp.assets_report'))
        
    global all_assets
    asset_name = form_data.get('asset_name')
    quantity = int(form_data.get('quantity', 0))
    asset_found = False
    for asset in all_assets:
        if asset.get('accommodation') == accommodation and asset.get('asset_name') == asset_name and asset.get('status') == 'Available':
            asset['quantity'] += quantity
            asset_found = True
            break

    if not asset_found:
        new_asset = {
            'id': int(time.time() * 1000), 'accommodation': accommodation,
            'asset_name': asset_name, 'quantity': quantity,
            'received_from': form_data.get('received_from'),
            'remarks': form_data.get('remarks'), 'status': 'Available'
        }
        all_assets.append(new_asset)
    
    save_assets_data(all_assets)
    flash(f"Successfully added/updated asset: {asset_name}")
    return redirect(url_for('assets_bp.assets_report'))

@assets_bp.route('/get_assets/<accommodation_name>/<status>')
def get_assets_by_status(accommodation_name, status):
    if 'username' not in session: return jsonify({"error": "Unauthorized"}), 401
    
    assets_in_accom = [asset['asset_name'] for asset in all_assets if asset.get('accommodation') == accommodation_name and asset.get('status') == status]
    return jsonify(sorted(list(set(assets_in_accom))))

@assets_bp.route('/shift_asset', methods=['POST'])
def shift_asset():
    global all_assets
    form_data = request.form
    source_acc = form_data.get('source_accommodation')
    target_acc = form_data.get('target_accommodation')
    asset_name = form_data.get('asset_name_shift')
    quantity_to_shift = int(form_data.get('quantity_shift', 0))

    if not can_modify(source_acc) or not can_modify(target_acc):
        return redirect(url_for('assets_bp.assets_report'))
    
    source_asset = next((asset for asset in all_assets if asset.get('accommodation') == source_acc and asset.get('asset_name') == asset_name and asset.get('status') == 'Available'), None)

    if not source_asset or source_asset['quantity'] < quantity_to_shift:
        flash("Not enough quantity in source accommodation to shift.")
        return redirect(url_for('assets_bp.assets_report'))

    source_asset['quantity'] -= quantity_to_shift
    
    target_asset = next((asset for asset in all_assets if asset.get('accommodation') == target_acc and asset.get('asset_name') == asset_name and asset.get('status') == 'Available'), None)
    if target_asset:
        target_asset['quantity'] += quantity_to_shift
    else:
        new_asset = {
            'id': int(time.time() * 1000), 'accommodation': target_acc,
            'asset_name': asset_name, 'quantity': quantity_to_shift,
            'received_from': f"Shifted from {source_acc}", 'remarks': '', 'status': 'Available'
        }
        all_assets.append(new_asset)

    all_assets = [asset for asset in all_assets if asset.get('quantity') > 0]
    
    save_assets_data(all_assets)
    flash(f"Successfully shifted {quantity_to_shift} of {asset_name}.")
    return redirect(url_for('assets_bp.assets_report'))

@assets_bp.route('/scrap_asset', methods=['POST'])
def scrap_asset():
    global all_assets
    form_data = request.form
    acc = form_data.get('scrap_accommodation')
    asset_name = form_data.get('asset_name_scrap')
    quantity_to_scrap = int(form_data.get('quantity_scrap', 0))
    
    if not can_modify(acc):
        return redirect(url_for('assets_bp.assets_report'))

    source_asset = next((asset for asset in all_assets if asset.get('accommodation') == acc and asset.get('asset_name') == asset_name and asset.get('status') == 'Available'), None)

    if not source_asset or source_asset['quantity'] < quantity_to_scrap:
        flash("Not enough quantity in available assets to scrap.")
        return redirect(url_for('assets_bp.assets_report'))
    
    source_asset['quantity'] -= quantity_to_scrap
    
    scrap_asset_record = next((asset for asset in all_assets if asset.get('accommodation') == acc and asset.get('asset_name') == asset_name and asset.get('status') == 'Scrap'), None)
    
    if scrap_asset_record:
        scrap_asset_record['quantity'] += quantity_to_scrap
    else:
        new_scrap_asset = {
            'id': int(time.time() * 1000), 'accommodation': acc,
            'asset_name': asset_name, 'quantity': quantity_to_scrap, 'status': 'Scrap',
            'sap_id': form_data.get('sap_id'), 'emp_name': form_data.get('emp_name'),
            'designation': form_data.get('designation'), 'department': form_data.get('department'),
            'scrap_date': form_data.get('scrap_date'), 'remarks': form_data.get('remarks')
        }
        all_assets.append(new_scrap_asset)

    all_assets = [asset for asset in all_assets if asset.get('quantity') > 0]
    
    save_assets_data(all_assets)
    flash(f"Successfully moved {quantity_to_scrap} of {asset_name} to scrap.")
    return redirect(url_for('assets_bp.assets_report'))

@assets_bp.route('/remove_scrap', methods=['POST'])
def remove_scrap():
    global all_assets
    form_data = request.form
    acc = form_data.get('remove_accommodation')
    asset_name = form_data.get('asset_name_remove')
    quantity_to_remove = int(form_data.get('quantity_remove', 0))
    
    if not can_modify(acc):
        return redirect(url_for('assets_bp.assets_report'))

    scrap_asset = next((asset for asset in all_assets if asset.get('accommodation') == acc and asset.get('asset_name') == asset_name and asset.get('status') == 'Scrap'), None)

    if not scrap_asset or scrap_asset['quantity'] < quantity_to_remove:
        flash("Not enough quantity in scrap to remove.")
        return redirect(url_for('assets_bp.assets_report'))
    
    scrap_asset['quantity'] -= quantity_to_remove
    
    all_assets = [asset for asset in all_assets if asset.get('quantity') > 0]

    save_assets_data(all_assets)
    flash(f"Successfully removed {quantity_to_remove} of {asset_name} from scrap.")
    return redirect(url_for('assets_bp.assets_report'))

@assets_bp.route('/download_assets_report', methods=['POST'])
def download_assets_report():
    role = session.get('role')
    allowed = session.get('allowed_accommodations', [])
    
    if role in ['Admin', 'Manager']:
        data_to_process = all_assets
    else:
        data_to_process = [asset for asset in all_assets if asset.get('accommodation') in allowed]

    status_filter = request.form.get('hidden_status')

    filtered_assets = data_to_process
    if status_filter:
        filtered_assets = [asset for asset in filtered_assets if asset.get('status') == status_filter]
    
    if not filtered_assets:
        flash("No data found for the selected filters to download.")
        return redirect(url_for('assets_bp.assets_report'))
        
    df = pd.DataFrame(filtered_assets)
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Assets_Report')
    writer.close()
    output.seek(0)
    
    return Response(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment;filename=assets_report.xlsx"}
    )