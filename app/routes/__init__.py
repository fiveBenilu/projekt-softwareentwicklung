from flask import Blueprint

main = Blueprint('main', __name__)

@main.route('/setup')
def setup():
    return 'Setup-Seite funktioniert!'