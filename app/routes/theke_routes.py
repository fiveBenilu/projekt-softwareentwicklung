from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from collections import defaultdict
from app.models import Bestellung, Artikel, TischLayout
from app import db
import os
import json

theke_bp = Blueprint('theke', __name__)


def _lade_tischanzahl_aus_setup(default=8):
    config_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'cafe.json')
    if not os.path.exists(config_file):
        return default

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return int(config.get('tische', default))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return default


def _default_layout(anzahl_tische):
    layout = []
    spalten = 4
    start_x = 30
    start_y = 30
    abstand_x = 150
    abstand_y = 140

    for i in range(anzahl_tische):
        tisch_id = str(i + 1)
        col = i % spalten
        row = i // spalten
        layout.append({
            'tisch_id': tisch_id,
            'pos_x': start_x + (col * abstand_x),
            'pos_y': start_y + (row * abstand_y),
            'width': 108,
            'height': 108
        })

    return layout

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
            tisch_status[tisch_id] = "Bestellung"
        elif letzter.aktion == "hilfe":
            tisch_status[tisch_id] = "Hilfe"
        elif letzter.aktion == "rechnung":
            tisch_status[tisch_id] = "Rechnung"
        else:
            tisch_status[tisch_id] = "Frei"

    anzahl_tische = _lade_tischanzahl_aus_setup(default=8)
    layout_db = TischLayout.query.all()

    if layout_db:
        tisch_layout = []
        for eintrag in layout_db:
            tisch_layout.append({
                'tisch_id': str(eintrag.tisch_id),
                'pos_x': eintrag.pos_x,
                'pos_y': eintrag.pos_y,
                'width': eintrag.width,
                'height': eintrag.height
            })
        tisch_layout.sort(key=lambda x: int(x['tisch_id']) if str(x['tisch_id']).isdigit() else 9999)
    else:
        tisch_layout = _default_layout(anzahl_tische)

    return render_template(
        'theke.html',
        bestellungen=gruppiert,
        tisch_status=tisch_status,
        anzahl_tische=anzahl_tische,
        tisch_layout=tisch_layout
    )

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
        if eintrag.aktion == 'bestellung':
            # Nur als bearbeitet markieren, damit Positionen fuer die Rechnung erhalten bleiben.
            eintrag.aktion = 'bestellung_erfasst'
        else:
            db.session.delete(eintrag)
        db.session.commit()
        flash(f'Eintrag {bestellungs_id} wurde erledigt.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen: {e}', 'danger')

    return redirect(url_for('theke.theke'))


@theke_bp.route('/theke/rechnung/<int:tisch_id>')
def rechnung_ansehen(tisch_id):
    bestell_eintraege = Bestellung.query.filter(
        Bestellung.tisch_id == tisch_id,
        Bestellung.aktion.in_(['bestellung', 'bestellung_erfasst'])
    ).order_by(Bestellung.zeit.asc()).all()

    positionen = defaultdict(lambda: {'menge': 0, 'einzelpreis': 0.0})

    for eintrag in bestell_eintraege:
        name = eintrag.artikel or 'Unbekannter Artikel'
        menge = int(eintrag.menge or 0)
        artikel = Artikel.query.filter_by(name=name).first()
        einzelpreis = float(artikel.preis) if artikel else 0.0

        positionen[name]['menge'] += menge
        positionen[name]['einzelpreis'] = einzelpreis

    rechnungs_positionen = []
    gesamt = 0.0
    for artikel_name, values in positionen.items():
        zeilen_summe = values['menge'] * values['einzelpreis']
        gesamt += zeilen_summe
        rechnungs_positionen.append({
            'artikel': artikel_name,
            'menge': values['menge'],
            'einzelpreis': values['einzelpreis'],
            'summe': zeilen_summe
        })

    rechnungs_positionen.sort(key=lambda x: x['artikel'])

    return render_template(
        'theke_rechnung.html',
        tisch_id=tisch_id,
        positionen=rechnungs_positionen,
        gesamt=gesamt,
        anzahl_bestellungen=len(bestell_eintraege)
    )


@theke_bp.route('/theke/tisch-abschliessen/<int:tisch_id>', methods=['POST'])
def tisch_abschliessen(tisch_id):
    try:
        geloescht = Bestellung.query.filter_by(tisch_id=tisch_id).delete(synchronize_session=False)
        db.session.commit()
        flash(f'Tisch {tisch_id} wurde abgeschlossen. {geloescht} Eintraege entfernt.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Abschliessen von Tisch {tisch_id}: {e}', 'danger')

    return redirect(url_for('theke.theke'))
