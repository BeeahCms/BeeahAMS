from flask import session, flash

def can_modify(accommodation_name):
    role = session.get('role')
    if role in ['Admin', 'Manager']:
        return True
    allowed = session.get('allowed_accommodations', [])
    if accommodation_name in allowed:
        return True
    flash(f"Access Denied: You do not have permission for {accommodation_name}.")
    return False

def can_access_central_store():
    role = session.get('role')
    if role in ['Admin', 'Manager']:
        return True
    allowed = session.get('allowed_accommodations', [])
    if 'Sultan Accommodation' in allowed:
        return True
    return False