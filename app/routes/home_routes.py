from flask import Blueprint, render_template
import os, json

home_bp = Blueprint('home', __name__, url_prefix='/home')

@home_bp.route('/')
def home():
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    setup_file = os.path.join(data_dir, 'cafe.json')
    setup = None
    if os.path.exists(setup_file):
        with open(setup_file) as f:
            setup = json.load(f)
    return render_template('home.html', setup=setup)

@home_bp.route('/bestellung')
def bestellung():
    filepath = os.path.join(os.path.dirname(__file__), '..', 'data', 'cafe.json')
    tische = 0
    if os.path.exists(filepath):
        with open(filepath) as f:
            try:
                data = json.load(f)
                tische = int(data.get('tische', 0))
            except json.JSONDecodeError:
                pass

    return render_template('bestellung.html', tische=tische)