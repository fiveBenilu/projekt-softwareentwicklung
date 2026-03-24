from flask import Blueprint, request, jsonify
from app.models import db, TischLayout
import os
import json

layout_bp = Blueprint('layout_bp', __name__, url_prefix='/layout')


def _setup_config_pfad():
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    return os.path.join(data_dir, 'cafe.json')


def _lade_setup_config():
    config_file = _setup_config_pfad()
    if not os.path.exists(config_file):
        return {}

    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _speichere_setup_config(config):
    config_file = _setup_config_pfad()
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)


def _lade_tischanzahl_aus_setup():
    config = _lade_setup_config()
    try:
        return int(config.get('tische', 0))
    except (ValueError, TypeError):
        return 0


def _naechste_tisch_nummer():
    layouts = TischLayout.query.all()
    ids = []
    for layout in layouts:
        try:
            ids.append(int(layout.tisch_id))
        except (TypeError, ValueError):
            continue
    return (max(ids) + 1) if ids else 1


def _berechne_standard_position(index):
    spalten = 4
    start_x = 30
    start_y = 30
    abstand_x = 140
    abstand_y = 140

    col = index % spalten
    row = index // spalten
    return start_x + (col * abstand_x), start_y + (row * abstand_y)


def _erstelle_standard_layout(anzahl_tische):
    if anzahl_tische <= 0:
        return []

    default_layouts = []
    spalten = 4
    start_x = 30
    start_y = 30
    abstand_x = 140
    abstand_y = 140

    for i in range(anzahl_tische):
        tisch_nummer = i + 1
        col = i % spalten
        row = i // spalten

        layout = TischLayout(
            tisch_id=str(tisch_nummer),
            pos_x=start_x + (col * abstand_x),
            pos_y=start_y + (row * abstand_y),
            width=100,
            height=100
        )
        db.session.add(layout)
        default_layouts.append(layout)

    db.session.commit()
    return default_layouts


def _synchronisiere_layout_mit_setup(anzahl_tische):
    layouts = TischLayout.query.all()
    vorhandene_ids = set()
    for layout in layouts:
        try:
            vorhandene_ids.add(int(layout.tisch_id))
        except (TypeError, ValueError):
            continue

    angelegt = False
    for tisch_nummer in range(1, anzahl_tische + 1):
        if tisch_nummer in vorhandene_ids:
            continue

        pos_x, pos_y = _berechne_standard_position(tisch_nummer - 1)
        db.session.add(TischLayout(
            tisch_id=str(tisch_nummer),
            pos_x=pos_x,
            pos_y=pos_y,
            width=100,
            height=100
        ))
        angelegt = True

    if angelegt:
        db.session.commit()

@layout_bp.route('/all', methods=['GET'])
def get_layout():
    anzahl_tische = _lade_tischanzahl_aus_setup()
    layouts = TischLayout.query.all()

    if not layouts and anzahl_tische > 0:
        layouts = _erstelle_standard_layout(anzahl_tische)
    elif anzahl_tische > 0:
        _synchronisiere_layout_mit_setup(anzahl_tische)
        layouts = TischLayout.query.all()

    return jsonify([l.to_dict() for l in layouts])

@layout_bp.route('/save', methods=['POST'])
def save_layout():
    data = request.get_json()
    for tisch in data:
        layout = TischLayout.query.filter_by(tisch_id=tisch['tisch_id']).first()
        if layout:
            layout.pos_x = tisch['pos_x']
            layout.pos_y = tisch['pos_y']
            layout.width = tisch.get('width', 100)
            layout.height = tisch.get('height', 100)
        else:
            layout = TischLayout(
                tisch_id=tisch['tisch_id'],
                pos_x=tisch['pos_x'],
                pos_y=tisch['pos_y'],
                width=tisch.get('width', 100),
                height=tisch.get('height', 100)
            )
            db.session.add(layout)
    db.session.commit()
    return jsonify({"message": "Layout gespeichert."}), 200


@layout_bp.route('/add-table', methods=['POST'])
def add_table():
    config = _lade_setup_config()
    aktuelle_anzahl = int(config.get('tische', 0) or 0)
    neue_anzahl = aktuelle_anzahl + 1
    config['tische'] = neue_anzahl
    _speichere_setup_config(config)

    layouts = TischLayout.query.all()
    neuer_index = len(layouts)
    pos_x, pos_y = _berechne_standard_position(neuer_index)
    neue_nummer = _naechste_tisch_nummer()

    neuer_tisch = TischLayout(
        tisch_id=str(neue_nummer),
        pos_x=pos_x,
        pos_y=pos_y,
        width=100,
        height=100
    )
    db.session.add(neuer_tisch)
    db.session.commit()

    return jsonify({
        "message": f"Tisch {neue_nummer} wurde hinzugefuegt.",
        "table": neuer_tisch.to_dict(),
        "tables": neue_anzahl
    }), 201