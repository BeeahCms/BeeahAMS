from flask import Blueprint, render_template, session, redirect, url_for, request, flash, Response
from routes.staff_routes import all_employees, countries_data
from collections import Counter
import io
import pandas as pd

acc_bp = Blueprint('acc_bp', __name__)

@acc_bp.route('/accommodation')
def accommodation_data():
    if 'username' not in session:
        return redirect(url_for('auth_bp.login'))

    role = session.get('role')
    allowed = session.get('allowed_accommodations', [])

    if role in ['Admin', 'Manager']:
        accommodations = sorted(list(set(emp['Accommodation'] for emp in all_employees)))
        data_to_process = all_employees
    else:
        accommodations = allowed
        data_to_process = [emp for emp in all_employees if emp.get('Accommodation') in allowed]

    departments = sorted(list(set(emp.get('Department') for emp in data_to_process if emp.get('Department'))))
    
    acc_filter = request.args.get('accommodation')
    department_summary = {}
    
    if acc_filter:
        if role not in ['Admin', 'Manager'] and acc_filter not in allowed:
            flash("Access Denied.")
            return redirect(url_for('acc_bp.accommodation_data'))
        
        filtered_employees = [emp for emp in data_to_process if emp['Accommodation'] == acc_filter and emp.get('Status') != 'Vacant']
        department_summary = dict(Counter(emp['Department'] for emp in filtered_employees))
    else:
        all_emp_for_summary = [emp for emp in data_to_process if emp.get('Status') != 'Vacant']
        department_summary = dict(Counter(emp['Department'] for emp in all_emp_for_summary if emp.get('Department')))

    return render_template(
        'accommodation.html', 
        accommodations=accommodations,
        departments=departments,
        selected_acc=acc_filter,
        department_summary=department_summary,
        countries=countries_data
    )

@acc_bp.route('/download_data', methods=['POST'])
def download_data():
    filtered_data = all_employees
    acc_filter = request.form.get('filter_accommodation')
    status_filter = request.form.get('filter_status')
    dept_filter = request.form.get('filter_department')

    if acc_filter:
        filtered_data = [d for d in filtered_data if d.get('Accommodation') == acc_filter]
    if status_filter:
        filtered_data = [d for d in filtered_data if d.get('Status') == status_filter]
    if dept_filter:
        filtered_data = [d for d in filtered_data if d.get('Department') == dept_filter]
    
    if not filtered_data:
        flash('No data found for the selected filters.')
        return redirect(url_for('acc_bp.accommodation_data'))

    df = pd.DataFrame(filtered_data)
    
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Report')
    writer.close()
    output.seek(0)

    return Response(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment;filename=beeah_cms_report.xlsx"}
    )