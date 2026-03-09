import csv
from app import create_app
from app.models import db, Artikel

app = create_app()

with app.app_context():
    with open('menu.csv', newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            try:
                artikel = Artikel(
                    kategorie=row['kategorie'].strip(),
                    name=row['name'].strip(),
                    preis=float(row['preis']),
                    beschreibung=row['beschreibung'].strip() if row['beschreibung'] else None
                )
                db.session.add(artikel)
            except Exception as e:
                print(f"⚠️ Fehler bei Zeile: {row} → {e}")
        db.session.commit()

print("✅ Menü erfolgreich importiert.")