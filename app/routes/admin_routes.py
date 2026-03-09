from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db                    # <-- WICHTIG: Das db aus __init__.py importieren!
from app.models import Artikel       # <-- Modelle importieren
import os
import json 

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# -----------------------------
# QR-Codes generieren
# -----------------------------
@admin_bp.route('/qrcodes', methods=['GET', 'POST'])
def qrcodes():
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    config_path = os.path.join(data_dir, 'cafe.json')

    if not os.path.exists(config_path):
        return "⚠️ Setup-Datei nicht gefunden."

    with open(config_path) as f:
        config = json.load(f)

    tische = config.get("tische", 0)
    output_dir = os.path.join('app', 'static', 'qrcodes')
    os.makedirs(output_dir, exist_ok=True)

    generierter_qr = None

    if request.method == 'POST':
        tisch_id = int(request.form.get('tisch_id'))
        base_url = "http://localhost:5000/tisch/"
        url = f"{base_url}{tisch_id}"

        filename = f"tisch_{tisch_id}.png"
        filepath = os.path.join(output_dir, filename)

        qr = qrcode.make(url)
        qr.save(filepath)

        generierter_qr = {
            "tisch": tisch_id,
            "filename": filename,
            "link": url
        }

        flash(f"✅ QR-Code für Tisch {tisch_id} generiert!")

    qrs = []
    for file in sorted(os.listdir(output_dir)):
        if file.endswith(".png"):
            qrs.append(file)

    return render_template(
        'admin_qrcodes.html',
        anzahl_tische=tische,
        qrcodes=qrs,
        generierter_qr=generierter_qr
    )

# -----------------------------
# Speisekarte anzeigen / hinzufügen
# -----------------------------
@admin_bp.route('/menu', methods=['GET', 'POST'])
def menu():
    if request.method == 'POST':
        name = request.form.get('name')
        preis = float(request.form.get('preis'))
        beschreibung = request.form.get('beschreibung')
        kategorie = request.form.get('kategorie')  # <-- Ergänzt

        artikel = Artikel(name=name, preis=preis, beschreibung=beschreibung, kategorie=kategorie)
        db.session.add(artikel)
        db.session.commit()

        flash('✅ Produkt hinzugefügt!')
        return redirect(url_for('admin.menu'))

    menu = Artikel.query.all()
    return render_template('admin_menu.html', menu=menu)

# -----------------------------
# Produkt löschen
# -----------------------------
@admin_bp.route('/menu/delete/<int:produkt_id>', methods=['POST'])
def delete_produkt(produkt_id):
    artikel = Artikel.query.get_or_404(produkt_id)
    db.session.delete(artikel)
    db.session.commit()
    flash("❌ Produkt gelöscht!")
    return redirect(url_for('admin.menu'))

# -----------------------------
# Produkt bearbeiten
# -----------------------------

@admin_bp.route('/menu/edit/<int:produkt_id>', methods=['GET', 'POST'])
def edit_produkt(produkt_id):
    artikel = Artikel.query.get_or_404(produkt_id)

    if request.method == 'POST':
        try:
            artikel.name = request.form.get('name')
            artikel.preis = float(request.form.get('preis'))
            artikel.beschreibung = request.form.get('beschreibung')
            artikel.kategorie = request.form.get('kategorie')

            db.session.commit()
            flash("✅ Produkt aktualisiert")
            return redirect(url_for('admin.menu'))
        except ValueError:
            flash("❌ Ungültiger Preis!")

    return render_template('admin_edit_menu.html', produkt=artikel)

    return render_template('admin_edit_menu.html', produkt=artikel)

@admin_bp.route('/dashboard')
def dashboard():
    return render_template('admin_dashboard.html')

@admin_bp.route('/menu/toggle/<int:produkt_id>', methods=['POST'])
def toggle_verfuegbar(produkt_id):
    artikel = Artikel.query.get_or_404(produkt_id)
    artikel.verfuegbar = not artikel.verfuegbar
    db.session.commit()
    status = "verfügbar" if artikel.verfuegbar else "ausverkauft"
    flash(f"🔁 Produkt ist jetzt {status}.")
    return redirect(url_for('admin.menu'))
    
@admin_bp.route('/layout-editor')
def show_layout_editor():
    return render_template('layout_editor.html')