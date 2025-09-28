from flask import session, flash

def can_modify(accommodation_name):
    """Checks if the current user has modification rights for a given accommodation."""
    role = session.get('role')

    if role in ['Admin', 'Manager']:
        return True

    allowed = session.get('allowed_accommodations', [])
    if accommodation_name in allowed:
        return True
    
    flash(f"Access Denied: You do not have permission to modify data for {accommodation_name}.")
    return False