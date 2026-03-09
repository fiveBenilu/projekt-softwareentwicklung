# create_db.py
from app import create_app
from app.models import db
from app.utils.import_menu import import_menu # falls du CSV importieren willst

app = create_app()

with app.app_context():
    db.drop_all()  # Entfernt alle Tabellen (optional, nur beim Neuaufsetzen)
    db.create_all()
    print("✅ Datenbanktabellen erfolgreich erstellt.")

    # Falls gewünscht, hier direkt die CSV einlesen:
    import_menu("app/static/menu.csv")
    print("📥 CSV-Daten erfolgreich importiert.")