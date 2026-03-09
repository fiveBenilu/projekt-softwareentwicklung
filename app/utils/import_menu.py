import csv
from app.models import db, Artikel

def import_menu(pfad):
    with open(pfad, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            artikel = Artikel(
                name=row['name'],
                preis=float(row['preis']),
                beschreibung=row.get('beschreibung', ''),
                kategorie=row.get('kategorie', '')
            )
            db.session.add(artikel)
        db.session.commit()