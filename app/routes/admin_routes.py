from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db                    # <-- WICHTIG: Das db aus __init__.py importieren!
from app.models import Artikel, Bestellung       # <-- Modelle importieren
from sqlalchemy import func
import os
import json 
import qrcode

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# -----------------------------
# QR-Codes generieren
# -----------------------------
@admin_bp.route('/qrcodes', methods=['GET', 'POST'])
def qrcodes():
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    config_path = os.path.join(data_dir, 'cafe.json')

    if not os.path.exists(config_path):
        return "Setup-Datei nicht gefunden."

    with open(config_path) as f:
        config = json.load(f)

    tische = config.get("tische", 0)
    output_dir = os.path.join('app', 'static', 'qrcodes')
    os.makedirs(output_dir, exist_ok=True)

    generierter_qr = None

    if request.method == 'POST':
        tisch_id = int(request.form.get('tisch_id'))
        # Dynamisch die URL für den Tisch generieren
        url = url_for('tisch.tisch', tisch_id=tisch_id, _external=True)

        filename = f"tisch_{tisch_id}.png"
        filepath = os.path.join(output_dir, filename)

        qr = qrcode.make(url)
        qr.save(filepath)

        generierter_qr = {
            "tisch": tisch_id,
            "filename": filename,
            "link": url
        }

        flash(f"QR-Code fuer Tisch {tisch_id} wurde generiert.")

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
        try:
            preis = float(request.form.get('preis', 0.0))
        except ValueError:
            flash("Ungueltiger Preis.")
            return redirect(url_for('admin.menu'))
            
        beschreibung = request.form.get('beschreibung')
        kategorie = request.form.get('kategorie')  # <-- Ergänzt

        artikel = Artikel(name=name, preis=preis, beschreibung=beschreibung, kategorie=kategorie)
        db.session.add(artikel)
        db.session.commit()

        flash('Produkt wurde hinzugefuegt.')
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
    flash("Produkt wurde geloescht.")
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
            flash("Produkt wurde aktualisiert.")
            return redirect(url_for('admin.menu'))
        except ValueError:
            flash("Ungueltiger Preis.")

    return render_template('admin_edit_menu.html', produkt=artikel)

@admin_bp.route('/dashboard')
@admin_bp.route('/statistik')
def dashboard():
    gesamt_aktionen = Bestellung.query.count()
    anzahl_bestellungen = Bestellung.query.filter(
        Bestellung.aktion.in_(['bestellung', 'bestellung_erfasst'])
    ).count()
    anzahl_hilfe = Bestellung.query.filter_by(aktion='hilfe').count()
    anzahl_rechnung = Bestellung.query.filter_by(aktion='rechnung').count()

    gesamt_umsatz = db.session.query(
        func.coalesce(func.sum(Bestellung.menge * Artikel.preis), 0.0)
    ).join(
        Artikel, Bestellung.artikel == Artikel.name
    ).filter(
        Bestellung.aktion.in_(['bestellung', 'bestellung_erfasst'])
    ).scalar() or 0.0

    top_artikel_raw = db.session.query(
        Bestellung.artikel,
        func.sum(Bestellung.menge).label('anzahl'),
        func.coalesce(func.sum(Bestellung.menge * Artikel.preis), 0.0).label('umsatz')
    ).join(
        Artikel, Bestellung.artikel == Artikel.name
    ).filter(
        Bestellung.aktion.in_(['bestellung', 'bestellung_erfasst'])
    ).group_by(
        Bestellung.artikel
    ).order_by(
        func.sum(Bestellung.menge).desc()
    ).limit(5).all()

    top_artikel = [
        {
            'name': eintrag.artikel,
            'anzahl': int(eintrag.anzahl or 0),
            'umsatz': float(eintrag.umsatz or 0.0)
        }
        for eintrag in top_artikel_raw
    ]

    tagesumsatz_raw = db.session.query(
        func.date(Bestellung.zeit).label('tag'),
        func.coalesce(func.sum(Bestellung.menge * Artikel.preis), 0.0).label('umsatz')
    ).join(
        Artikel, Bestellung.artikel == Artikel.name
    ).filter(
        Bestellung.aktion.in_(['bestellung', 'bestellung_erfasst'])
    ).group_by(
        func.date(Bestellung.zeit)
    ).order_by(
        func.date(Bestellung.zeit).desc()
    ).limit(7).all()

    tagesumsatz_raw = list(reversed(tagesumsatz_raw))
    chart_labels = [str(eintrag.tag) for eintrag in tagesumsatz_raw]
    chart_values = [round(float(eintrag.umsatz or 0.0), 2) for eintrag in tagesumsatz_raw]

    return render_template(
        'admin_dashboard.html',
        gesamt_aktionen=gesamt_aktionen,
        anzahl_bestellungen=anzahl_bestellungen,
        anzahl_hilfe=anzahl_hilfe,
        anzahl_rechnung=anzahl_rechnung,
        gesamt_umsatz=round(float(gesamt_umsatz), 2),
        top_artikel=top_artikel,
        chart_labels=chart_labels,
        chart_values=chart_values
    )

@admin_bp.route('/menu/toggle/<int:produkt_id>', methods=['POST'])
def toggle_verfuegbar(produkt_id):
    artikel = Artikel.query.get_or_404(produkt_id)
    artikel.verfuegbar = not artikel.verfuegbar
    db.session.commit()
    status = "verfügbar" if artikel.verfuegbar else "ausverkauft"
    flash(f"Produktstatus ist jetzt {status}.")
    return redirect(url_for('admin.menu'))
    
@admin_bp.route('/layout-editor')
def show_layout_editor():
    return render_template('layout_editor.html')