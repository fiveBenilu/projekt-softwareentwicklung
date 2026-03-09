from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz

db = SQLAlchemy()

def get_local_time():
    return datetime.now(pytz.timezone("Europe/Berlin"))

class Artikel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    preis = db.Column(db.Float, nullable=False)
    beschreibung = db.Column(db.String(255))
    kategorie = db.Column(db.String(50), nullable=True)
    verfuegbar = db.Column(db.Boolean, default=True)

class CafeSetup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    adresse = db.Column(db.String(200))
    sprache = db.Column(db.String(10))
    anzahl_tische = db.Column(db.Integer)

class QRCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tisch_id = db.Column(db.Integer, nullable=False)
    image_path = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Bestellung(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tisch_id = db.Column(db.Integer, nullable=False)
    aktion = db.Column(db.String(50), nullable=False)  # "bestellung", "hilfe", "rechnung"
    artikel = db.Column(db.String(100), nullable=True)
    menge = db.Column(db.Integer, nullable=True)
    zeit = db.Column(db.DateTime, default=get_local_time)  
    
class TischLayout(db.Model):
    __tablename__ = 'tisch_layouts'

    id = db.Column(db.Integer, primary_key=True)
    tisch_id = db.Column(db.String, nullable=False)
    pos_x = db.Column(db.Integer, nullable=False)
    pos_y = db.Column(db.Integer, nullable=False)
    width = db.Column(db.Integer, default=100)
    height = db.Column(db.Integer, default=100)

    def to_dict(self):
        return {
            "id": self.id,
            "tisch_id": self.tisch_id,
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
            "width": self.width,
            "height": self.height
        }