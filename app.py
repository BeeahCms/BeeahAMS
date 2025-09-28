from flask import Flask
import os

def create_app():
    app = Flask(__name__, template_folder='templates')
    app.secret_key = 'your_super_secret_key_for_sessions'
    
    data_dir = os.environ.get('RENDER_DATA_DIR', os.getcwd())
    upload_folder = os.path.join(data_dir, 'uploads', 'amcs')
    os.makedirs(upload_folder, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_folder

    def format_sap_id(value):
        try:
            return str(int(float(value)))
        except (ValueError, TypeError):
            return ""

    app.jinja_env.filters['int_sap'] = format_sap_id

    from routes.auth_routes import auth_bp
    from routes.accommodation_routes import acc_bp
    from routes.staff_routes import staff_bp
    from routes.maintenance_routes import maintenance_bp
    from routes.amcs_routes import amcs_bp
    from routes.settings_routes import settings_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(acc_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(amcs_bp)
    app.register_blueprint(settings_bp)
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)