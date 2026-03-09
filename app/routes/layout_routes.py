from flask import Blueprint, request, jsonify
from app.models import db, TischLayout

layout_bp = Blueprint('layout_bp', __name__, url_prefix='/layout')

@layout_bp.route('/all', methods=['GET'])
def get_layout():
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