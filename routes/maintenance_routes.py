from flask import Blueprint, render_template, session, redirect, url_for, request, flash, Response
from routes.staff_routes import all_employees
from utils.permissions import can_modify
import json
import os
import time
import pandas as pd
import io

maintenance_bp = Blueprint('maintenance_bp', __name__)

DATA_DIR = os.environ.get('RENDER_DATA_DIR', '.')
DATA_FILE = os.path.join(DATA_DIR, 'maintenance_data.json')

def load_maintenance_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(DATA_FILE, 'r') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return []

def save_maintenance_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

all_issues = load_maintenance_data()

@maintenance_bp.route('/maintenance')
def maintenance_report():
    if 'username' not in session:
        return redirect(url_for('auth_bp.login'))

    role = session.get('role')
    allowed = session.get('allowed_accommodations', [])
    
    if role in ['Admin', 'Manager']:
        data_to_process = all_issues
        accommodations = sorted(list(set(emp['Accommodation'] for emp in all_employees)))
    else:
        data_to_process = [issue for issue in all_issues if issue.get('accommodation') in allowed]
        accommodations = allowed

    status_filter = request.args.get('status')
    accommodation_filter = request.args.get('accommodation')
    
    issues_to_show = data_to_process
    if status_filter:
        issues_to_show = [issue for issue in issues_to_show if issue.get('status') == status_filter]
    if accommodation_filter:
        issues_to_show = [issue for issue in issues_to_show if issue.get('accommodation') == accommodation_filter]

    stats = {
        'Open': sum(1 for issue in data_to_process if issue.get('status') == 'Open'),
        'In-Process': sum(1 for issue in data_to_process if issue.get('status') == 'In-Process'),
        'Closed': sum(1 for issue in data_to_process if issue.get('status') == 'Closed')
    }
    
    return render_template('maintenance.html', issues=issues_to_show, stats=stats, accommodations=accommodations)

@maintenance_bp.route('/add_issue', methods=['POST'])
def add_issue():
    form_data = request.form
    accommodation = form_data.get('accommodation')
    if not can_modify(accommodation):
        return redirect(url_for('maintenance_bp.maintenance_report'))
        
    global all_issues
    new_issue = {
        'id': int(time.time() * 1000), 'accommodation': accommodation,
        'block': form_data.get('block'), 'section': form_data.get('section'),
        'report_date': form_data.get('report_date'), 'details': form_data.get('details'),
        'status': form_data.get('status'), 'closed_date': form_data.get('closed_date', ''),
        'concern': form_data.get('concern'), 'concern_other': form_data.get('concern_other', ''),
        'risk': form_data.get('risk'), 'remarks': form_data.get('remarks')
    }
    all_issues.append(new_issue)
    save_maintenance_data(all_issues)
    flash("New maintenance issue added successfully!")
    return redirect(url_for('maintenance_bp.maintenance_report'))

@maintenance_bp.route('/update_issue/<issue_id>', methods=['POST'])
def update_issue(issue_id):
    form_data = request.form
    accommodation = form_data.get('accommodation')
    if not can_modify(accommodation):
        return redirect(url_for('maintenance_bp.maintenance_report'))
        
    global all_issues
    for issue in all_issues:
        if str(issue.get('id')) == str(issue_id):
            issue.update({
                'accommodation': accommodation, 'block': form_data.get('block'), 
                'section': form_data.get('section'), 'report_date': form_data.get('report_date'),
                'details': form_data.get('details'), 'status': form_data.get('status'),
                'closed_date': form_data.get('closed_date'), 'concern': form_data.get('concern'),
                'concern_other': form_data.get('concern_other'), 'risk': form_data.get('risk'),
                'remarks': form_data.get('remarks')
            })
            break
            
    save_maintenance_data(all_issues)
    flash(f"Issue #{issue_id} updated successfully!")
    return redirect(url_for('maintenance_bp.maintenance_report'))

@maintenance_bp.route('/delete_issue/<issue_id>', methods=['POST'])
def delete_issue(issue_id):
    global all_issues
    
    issue_to_delete = next((issue for issue in all_issues if str(issue.get('id')) == str(issue_id)), None)

    if not issue_to_delete:
        flash(f"Error: Could not find issue #{issue_id}.")
        return redirect(url_for('maintenance_bp.maintenance_report'))

    if not can_modify(issue_to_delete.get('accommodation')):
        return redirect(url_for('maintenance_bp.maintenance_report'))
    
    all_issues = [issue for issue in all_issues if str(issue.get('id')) != str(issue_id)]
    save_maintenance_data(all_issues)
    flash(f"Issue #{issue_id} deleted successfully!")
        
    return redirect(url_for('maintenance_bp.maintenance_report'))

@maintenance_bp.route('/upload_maintenance_issues', methods=['POST'])
def upload_maintenance_issues():
    global all_issues
    if 'maintenance_file' not in request.files:
        flash('No file part in the request.')
        return redirect(url_for('maintenance_bp.maintenance_report'))

    file = request.files['maintenance_file']
    if file.filename == '':
        flash('No file selected for upload.')
        return redirect(url_for('maintenance_bp.maintenance_report'))

    if file and file.filename.endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(file).fillna('')
            df['Report Date'] = pd.to_datetime(df['Report Date']).dt.strftime('%Y-%m-%d')
            df['Closed Date'] = pd.to_datetime(df['Closed Date'], errors='coerce').dt.strftime('%Y-%m-%d')
            
            new_issues = df.to_dict('records')

            for issue in new_issues:
                issue['id'] = int(time.time() * 1000)
                all_issues.append(issue)
                time.sleep(0.001)

            save_maintenance_data(all_issues)
            flash(f"Successfully added {len(new_issues)} new maintenance issues from file.")
        except Exception as e:
            flash(f"Error processing maintenance file: {e}")
    else:
        flash("Invalid file format. Please upload an Excel file.")

    return redirect(url_for('maintenance_bp.maintenance_report'))

@maintenance_bp.route('/download_maintenance_report', methods=['POST'])
def download_maintenance_report():
    role = session.get('role')
    allowed = session.get('allowed_accommodations', [])
    
    if role in ['Admin', 'Manager']:
        data_to_process = all_issues
    else:
        data_to_process = [issue for issue in all_issues if issue.get('accommodation') in allowed]

    status_filter = request.form.get('hidden_status')
    accommodation_filter = request.form.get('hidden_accommodation')

    filtered_issues = data_to_process
    if status_filter:
        filtered_issues = [issue for issue in filtered_issues if issue.get('status') == status_filter]
    if accommodation_filter:
        filtered_issues = [issue for issue in filtered_issues if issue.get('accommodation') == accommodation_filter]
    
    if not filtered_issues:
        flash("No data found for the selected filters to download.")
        return redirect(url_for('maintenance_bp.maintenance_report'))
        
    df = pd.DataFrame(filtered_issues)
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Maintenance_Report')
    writer.close()
    output.seek(0)
    
    return Response(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment;filename=maintenance_report.xlsx"}
    )