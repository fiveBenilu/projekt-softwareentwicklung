from flask import Blueprint, render_template, request, redirect, url_for, flash
import json
import os

main = Blueprint('main', __name__)

@main.route('/setup', methods=['GET', 'POST'])
def setup():
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    filepath = os.path.join(data_dir, 'cafe.json')

    if request.method == 'POST':
        cafe_data = {
            'name': request.form['name'],
            'address': request.form['address'],
            'phone': request.form['phone'],
            'language': request.form['language'],
            'tische': int(request.form['tables'])
        }

        os.makedirs(data_dir, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(cafe_data, f, indent=2)

        flash('Café erfolgreich gespeichert!')
        return redirect(url_for('home.home'))

    # GET → zeige Setup-Formular immer
    return render_template('setup.html')

