from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from collections import defaultdict
from app.models import Bestellung
from app import db

theke_bp = Blueprint('theke', __name__)

@theke_bp.route('/theke')
def theke():
    bestellungen = Bestellung.query.order_by(Bestellung.zeit).all()

    # Gruppieren nach Tisch-ID
    gruppiert = defaultdict(list)
    for eintrag in bestellungen:
        gruppiert[str(eintrag.tisch_id)].append(eintrag)

    # Letzte Aktion je Tisch analysieren
    tisch_status = {}
    for tisch_id, eintraege in gruppiert.items():
        letzter = eintraege[-1]
        if letzter.aktion == "bestellung":
            tisch_status[tisch_id] = "🛎️ Bestellung"
        elif letzter.aktion == "hilfe":
            tisch_status[tisch_id] = "🙋 Hilfe"
        elif letzter.aktion == "rechnung":
            tisch_status[tisch_id] = "💶 Rechnung"
        else:
            tisch_status[tisch_id] = "🟢"

    return render_template('theke.html', bestellungen=gruppiert, tisch_status=tisch_status)

# theke_routes.py
@theke_bp.route('/theke/api/bestellungen')
def api_bestellungen():
    bestellungen = Bestellung.query.order_by(Bestellung.zeit).all()

    daten = defaultdict(list)
    for eintrag in bestellungen:
        daten[str(eintrag.tisch_id)].append({
            "id": eintrag.id,  # 👈 hinzufügen
            "artikel": eintrag.artikel,
            "menge": eintrag.menge,
            "aktion": eintrag.aktion,
            "zeit": eintrag.zeit.strftime("%Y-%m-%d %H:%M:%S")
        })

    return jsonify(daten)

@theke_bp.route('/theke/erledigt/<int:bestellungs_id>', methods=['POST'])
def erledige_bestellung(bestellungs_id):
    eintrag = Bestellung.query.get_or_404(bestellungs_id)

    try:
        db.session.delete(eintrag)
        db.session.commit()
        flash(f'Eintrag {bestellungs_id} wurde gelöscht.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen: {e}', 'danger')

    return redirect(url_for('theke.theke'))
