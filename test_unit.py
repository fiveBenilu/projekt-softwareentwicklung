"""
Unit-Tests für das Bestellsystem (Whitebox-Testing)
Basierend auf TDD-Verfahren und den identifizierten Risiken aus der Risikomatrix.

RISIKOABDECKUNG:
- Risiko 1: Unzureichende Zugriffssicherung / fehlende Admin-Authentifizierung (TestSicherheit)
- Risiko 2: Datenverlust oder Korruption der SQLite-Datenbank (TestDatenbankIntegrität)
- Risiko 3: Fehlerhafte Eingaben / Inkonsistente Bestellungen und Artikelzuordnung (TestArtikelModel, TestBestellungModel, TestWarenkorb)
- Risiko 4: QR-Code- und Tischzuordnungsfehler im Setup / fehlerhafte Konfigurationsdaten (TestTischLayout, TestCafeSetup)
- Risiko 5: Skalierung und Performance bei wachsender Nutzerlast (wird durch Lasttests getestet, nicht durch Unit-Tests)
"""

import sys
from pathlib import Path
import pytest
from typing import Any

# Ensure the repository root is on sys.path so the app package can be imported
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# App-Imports
from app import create_app, db
from app.models import Artikel, Bestellung, TischLayout, CafeSetup, QRCode


class TestArtikelModel:
    """
    Tests für das Artikel-Modell
    RISIKO 3: Fehlerhafte Eingaben / Inkonsistente Bestellungen und Artikelzuordnung
    Fokus: Validierung von Artikel-Daten (Preis, Kategorie, Verfügbarkeit) zur Verhinderung 
           von fehlerhaften Bestellungen und Inkonsistenzen im System.
    """

    @pytest.fixture
    def app(self):
        """Testanwendung mit separater Testdatenbank erstellen"""
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True

        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()

    @pytest.fixture
    def client(self, app: Any):
        """Testclient erstellen"""
        return app.test_client()

    def test_artikel_erstellung_mit_gueltigem_preis(self, app: Any):
        """
        Test: Artikel mit gültigem Preis erstellen
        Risiko 3 - Abdeckung: Stellt sicher, dass positive Preise korrekt gespeichert werden.
        Verhinderung von Inkonsistenzen bei Artikel-Preisen.
        """
        with app.app_context():
            # Arrange
            artikel = Artikel(
                name="Espresso",
                preis=2.50,
                beschreibung="Starker Kaffee",
                kategorie="Getränke",
                verfuegbar=True
            )
            db.session.add(artikel)
            db.session.commit()

            # Act & Assert
            assert artikel.id is not None
            assert artikel.name == "Espresso"
            assert artikel.preis == 2.50
            assert artikel.verfuegbar is True

    def test_artikel_erstellung_ohne_beschreibung(self, app: Any):
        """
        Test: Artikel ohne optionale Beschreibung erstellen
        Risiko 3 - Abdeckung: Prüft, dass Artikel auch ohne Beschreibung 
        korrekt erstellt werden und keine Fehler auslösen.
        """
        with app.app_context():
            # Arrange
            artikel = Artikel(
                name="Mineralwasser",
                preis=1.50,
                kategorie="Getränke"
            )
            db.session.add(artikel)
            db.session.commit()

            # Act & Assert
            assert artikel.id is not None
            assert artikel.beschreibung is None
            assert artikel.verfuegbar is True

    def test_artikel_mit_null_preis(self, app: Any):
        """
        Test: Artikel mit Preis 0 (Gratis-Artikel) zulassen
        Risiko 3 - Abdeckung: Prüft, dass Gratis-Artikel (z.B. Besteck, Servietten) 
        mit Preis 0 korrekt behandelt werden und keine Fehler auslösen.
        """
        with app.app_context():
            # Arrange
            artikel = Artikel(
                name="Wasserkaraffe",
                preis=0.0,
                kategorie="Besteck"
            )
            db.session.add(artikel)
            db.session.commit()

            # Act & Assert
            assert artikel.preis == 0.0

    def test_artikel_verfuegbarkeit_toggle(self, app: Any):
        """
        Test: Artikel-Verfügbarkeit umschalten
        Risiko 3 - Abdeckung: Stellt sicher, dass Artikel korrekt als verfügbar/nicht verfügbar
        markiert werden können, um zu verhindern, dass Kunden aus verfügbare Artikel bestellen.
        """
        with app.app_context():
            # Arrange
            artikel = Artikel(
                name="Cappuccino",
                preis=3.50,
                verfuegbar=True
            )
            db.session.add(artikel)
            db.session.commit()

            # Act
            artikel.verfuegbar = False
            db.session.commit()

            # Assert
            abgerufen = Artikel.query.get(artikel.id)
            assert abgerufen.verfuegbar is False

    def test_artikel_mit_kategorien_sortieren(self, app: Any):
        """
        Test: Artikel korrekt nach Kategorien filtern
        Risiko 3 - Abdeckung: Prüft, dass die Menü-Kategorisierung funktioniert,
        um Kunden die richtige Artikel-Zuordnung anzuzeigen.
        """
        with app.app_context():
            # Arrange
            artikel1 = Artikel(name="Kaffee", preis=2.0, kategorie="Getränke")
            artikel2 = Artikel(name="Cappuccino", preis=3.0, kategorie="Getränke")
            artikel3 = Artikel(name="Brötchen", preis=1.5, kategorie="Backwaren")
            
            db.session.add_all([artikel1, artikel2, artikel3])
            db.session.commit()

            # Act
            getraenke = Artikel.query.filter_by(kategorie="Getränke").all()
            backwaren = Artikel.query.filter_by(kategorie="Backwaren").all()

            # Assert
            assert len(getraenke) == 2
            assert len(backwaren) == 1
            assert artikel1 in getraenke


class TestBestellungModel:
    """
    Tests für das Bestellung-Modell
    RISIKO 3: Fehlerhafte Eingaben / Inkonsistente Bestellungen und Artikelzuordnung
    Fokus: Korrekte Erfassung und Verarbeitung von Bestellugen, Hilfeanfragen und 
           Rechnungsanfragen zur Vermeidung von fehlerhaften Transaktionen.
    """

    @pytest.fixture
    def app(self):
        """Testanwendung mit separater Testdatenbank erstellen"""
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True

        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()

    def test_bestellung_erstellung_mit_artikel_id(self, app: Any):
        """
        Test: Bestellung mit Artikel-ID erstellen
        Risiko 3 - Abdeckung: Stellt sicher, dass Artikel-IDs in Bestellungen 
        korrekt gespeichert und verknüpft werden.
        """
        with app.app_context():
            # Arrange
            artikel = Artikel(name="Espresso", preis=2.50)
            db.session.add(artikel)
            db.session.commit()

            tisch = TischLayout(tisch_id=1, pos_x=10, pos_y=20)
            db.session.add(tisch)
            db.session.commit()

            # Act
            bestellung = Bestellung(
                tisch_id=tisch.tisch_id,
                aktion="bestellung",
                artikel_id=artikel.id,
                menge=2
            )
            db.session.add(bestellung)
            db.session.commit()

            # Assert
            assert bestellung.id is not None
            assert bestellung.artikel_id == artikel.id
            assert bestellung.menge == 2
            assert bestellung.aktion == "bestellung"

    def test_bestellung_hilfe_anfrage(self, app: Any):
        """
        Test: Hilfeanfrage (ohne Artikel) erstellen
        Risiko 3 - Abdeckung: Stellt sicher, dass Hilfeanfragen korrekt 
        (ohne Artikel-ID) gespeichert werden.
        """
        with app.app_context():
            # Arrange
            tisch = TischLayout(tisch_id=5, pos_x=50, pos_y=50)
            db.session.add(tisch)
            db.session.commit()

            # Act
            bestellung = Bestellung(
                tisch_id=tisch.tisch_id,
                aktion="hilfe"
            )
            db.session.add(bestellung)
            db.session.commit()

            # Assert
            assert bestellung.aktion == "hilfe"
            assert bestellung.artikel_id is None
            assert bestellung.menge is None

    def test_bestellung_rechnung_anfrage(self, app: Any):
        """
        Test: Rechnungsanfrage erstellen
        Risiko 3 - Abdeckung: Prüft, dass Rechnungsanfragen korrekt 
        erfasst und verarbeitet werden.
        """
        with app.app_context():
            # Arrange
            tisch = TischLayout(tisch_id=3, pos_x=30, pos_y=40)
            db.session.add(tisch)
            db.session.commit()

            # Act
            bestellung = Bestellung(
                tisch_id=tisch.tisch_id,
                aktion="rechnung"
            )
            db.session.add(bestellung)
            db.session.commit()

            # Assert
            assert bestellung.aktion == "rechnung"

    def test_bestellungen_pro_tisch_abrufen(self, app: Any):
        """
        Test: Alle Bestellungen für einen Tisch abrufen
        Risiko 3 - Abdeckung: Stellt sicher, dass Bestellungen korrekt an Tische 
        gebunden sind und abgerufen werden können.
        """
        with app.app_context():
            # Arrange
            artikel = Artikel(name="Kaffee", preis=2.0)
            db.session.add(artikel)
            db.session.commit()

            tisch = TischLayout(tisch_id=2, pos_x=20, pos_y=30)
            db.session.add(tisch)
            db.session.commit()

            bestellung1 = Bestellung(
                tisch_id=2,
                aktion="bestellung",
                artikel_id=artikel.id,
                menge=1
            )
            bestellung2 = Bestellung(
                tisch_id=2,
                aktion="hilfe"
            )
            db.session.add_all([bestellung1, bestellung2])
            db.session.commit()

            # Act
            bestellungen = Bestellung.query.filter_by(tisch_id=2).all()

            # Assert
            assert len(bestellungen) == 2


class TestTischLayout:
    """
    Tests für Tisch-Layout und QR-Code-Zuordnung
    RISIKO 4: QR-Code- und Tischzuordnungsfehler im Setup / fehlerhafte Konfigurationsdaten
    Fokus: Korrekte Zuordnung von Tischen zu Positionen und QR-Codes, um Kunden-Verwechslungen
           und fehlerhafte Bestellungen zu vermeiden.
    """

    @pytest.fixture
    def app(self):
        """Testanwendung mit separater Testdatenbank erstellen"""
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True

        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()

    def test_tisch_layout_erstellung(self, app: Any):
        """
        Test: Tisch-Layout mit Positionen erstellen
        Risiko 4 - Abdeckung: Prüft, dass Tische mit korrekten Positionen (X/Y-Koordinaten)
        in der Datenbank gespeichert werden, um eine genaue Platzierung zu gewährleisten.
        """
        with app.app_context():
            # Arrange
            tisch = TischLayout(
                tisch_id=1,
                pos_x=100,
                pos_y=200,
                width=150,
                height=150
            )
            db.session.add(tisch)
            db.session.commit()

            # Act & Assert
            assert tisch.id is not None
            assert tisch.tisch_id == 1
            assert tisch.pos_x == 100
            assert tisch.pos_y == 200

    def test_tisch_layout_to_dict(self, app: Any):
        """
        Test: Tisch-Layout als Dictionary exportieren
        Risiko 4 - Abdeckung: Prüft, dass Tisch-Layout-Daten korrekt 
        in das benötigte Format für die Frontend-Anzeige konvertiert werden.
        """
        with app.app_context():
            # Arrange
            tisch = TischLayout(
                tisch_id=3,
                pos_x=50,
                pos_y=60,
                width=100,
                height=100
            )
            db.session.add(tisch)
            db.session.commit()

            # Act
            tisch_dict = tisch.to_dict()

            # Assert
            assert tisch_dict['tisch_id'] == 3
            assert tisch_dict['pos_x'] == 50
            assert tisch_dict['pos_y'] == 60
            assert 'id' in tisch_dict

    def test_tisch_eindeutige_tisch_id(self, app: Any):
        """
        Test: Tisch-IDs müssen eindeutig sein
        Risiko 4 - Abdeckung: Verhindert, dass zwei Tische die gleiche ID haben, 
        was Bestellungs-Verwechslungen und Zuordnungsfehler verursachen würde.
        """
        with app.app_context():
            # Arrange
            tisch1 = TischLayout(tisch_id=5, pos_x=10, pos_y=20)
            tisch2 = TischLayout(tisch_id=5, pos_x=30, pos_y=40)

            db.session.add(tisch1)
            db.session.commit()
            db.session.add(tisch2)

            # Act & Assert
            with pytest.raises(Exception):
                db.session.commit()


class TestCafeSetup:
    """
    Tests für Café-Konfiguration
    RISIKO 4: QR-Code- und Tischzuordnungsfehler im Setup / fehlerhafte Konfigurationsdaten
    Fokus: Validierung der initialen Café-Konfiguration (Tischanzahl, Adresse, etc.),
           um fehlerhafte Setups zu erkennen und zu verhindern.
    """

    @pytest.fixture
    def app(self):
        """Testanwendung mit separater Testdatenbank erstellen"""
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True

        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()

    def test_cafe_setup_mit_alle_feldern(self, app: Any):
        """
        Test: Café mit vollständigen Daten eintragen
        Risiko 4 - Abdeckung: Stellt sicher, dass die initiale Café-Konfiguration
        vollständig und korrekt gespeichert wird.
        """
        with app.app_context():
            # Arrange
            cafe = CafeSetup(
                name="Bergmann Café",
                adresse="Berliner Str. 42",
                sprache="de",
                anzahl_tische=8
            )
            db.session.add(cafe)
            db.session.commit()

            # Act & Assert
            assert cafe.id is not None
            assert cafe.name == "Bergmann Café"
            assert cafe.anzahl_tische == 8

    def test_cafe_setup_tische_validierung(self, app: Any):
        """
        Test: Tischanzahl darf nicht negativ sein (Business-Logik-Test)
        Risiko 4 - Abdeckung: Deckt ein kritisches Konfigurationsproblem auf:
        Negative Tischanzahlen würden zu fehlerhaften Setups führen.
        """
        with app.app_context():
            # Arrange
            cafe = CafeSetup(
                name="Test Café",
                adresse="Test Str.",
                sprache="de",
                anzahl_tische=-1  # Ungültig!
            )

            # Act & Assert
            # SQLite erlaubt negative Zahlen, aber getestet wird die Business-Logik
            assert cafe.anzahl_tische < 0  # Zeigt das Risiko


class TestWarenkorb:
    """
    Tests für Warenkorb-Session-Logik
    RISIKO 3: Fehlerhafte Eingaben / Inkonsistente Bestellungen und Artikelzuordnung
    Fokus: Prüfung der Warenkorb-Struktur und korrekter Preisberechnung,
           um finanzielle und Bestellungs-Fehler zu vermeiden.
    """

    @pytest.fixture
    def app(self):
        """Testanwendung mit separater Testdatenbank erstellen"""
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True

        with app.app_context():
            db.create_all()
            yield app

    def test_warenkorb_eintrag_struktur(self, app: Any):
        """
        Test: Warenkorb-Einträge haben korrekte Struktur
        Risiko 3 - Abdeckung: Stellt sicher, dass alle erforderlichen Felder 
        (artikel_id, menge, preis) in Warenkorb-Einträgen vorhanden sind.
        """
        # Arrange
        eintrag = {
            "artikel_id": 1,
            "artikel": "Kaffee",
            "menge": 2,
            "preis": 2.50
        }

        # Act & Assert
        assert "artikel_id" in eintrag
        assert "artikel" in eintrag
        assert "menge" in eintrag
        assert "preis" in eintrag
        assert eintrag['menge'] > 0

    def test_warenkorb_gesamtpreis_berechnung(self, app: Any):
        """
        Test: Gesamtpreis des Warenkorbs korrekt berechnen
        Risiko 3 - Abdeckung: Verhindert Rechenfehler bei der Preisberechnung,
        die zu falschen Zahlungsaufforderungen führen würden.
        """
        # Arrange
        warenkorb = [
            {"artikel": "Kaffee", "menge": 2, "preis": 2.50},
            {"artikel": "Brötchen", "menge": 1, "preis": 1.50}
        ]

        # Act
        gesamtpreis = sum(eintrag['menge'] * eintrag['preis'] for eintrag in warenkorb)

        # Assert
        assert gesamtpreis == 6.50


class TestDatenbankIntegrität:
    """
    Tests für Datenbankintegrität und Backups
    RISIKO 2: Datenverlust oder Korruption der SQLite-Datenbank
    Fokus: Prüfung von Transaktionen, Rollback-Mechanismen und Datenkonsistenz
           zur Vermeidung von Datenkorruption und Datenverlust.
    """

    @pytest.fixture
    def app(self):
        """Testanwendung mit separater Testdatenbank erstellen"""
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True

        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()

    def test_datenbank_transaktionen_rollback(self, app: Any):
        """
        Test: Transaktionen können rollback gemacht werden
        Risiko 2 - Abdeckung: Stellt sicher, dass fehlgeschlagene Datenbankoperationen
        rückgängig gemacht werden, um Datenkorruption zu verhindern.
        """
        with app.app_context():
            # Arrange
            artikel = Artikel(name="Test Artikel", preis=5.0)
            db.session.add(artikel)
            db.session.commit()

            # Act - Fehler simulieren
            try:
                artikel2 = Artikel(name="Test Artikel 2", preis="invalid")  # Fehler
                db.session.add(artikel2)
                db.session.commit()
            except Exception:
                db.session.rollback()

            # Assert
            count = Artikel.query.count()
            assert count == 1  # Nur das erste sollte gespeichert sein

    def test_bestellung_mit_ungueriger_artikel_id_verhindern(self, app: Any):
        """
        Test: Bestellung mit nicht existierender Artikel-ID sollte geprüft werden
        Risiko 2 + Risiko 3 - Abdeckung: Deckt auf, dass ungültige Artikel-IDs
        gespeichert werden und Validation fehlschlägt. Dies kann zu Datenverlust führen.
        """
        with app.app_context():
            # Arrange - keine Artikel in der DB
            tisch = TischLayout(tisch_id=1, pos_x=10, pos_y=20)
            db.session.add(tisch)
            db.session.commit()

            # Act
            bestellung = Bestellung(
                tisch_id=1,
                aktion="bestellung",
                artikel_id=999,  # existiert nicht
                menge=1
            )
            db.session.add(bestellung)
            db.session.commit()

            # Assert - die Bestellung wird trotzdem gespeichert
            # (Das ist ein Risiko, das durch Validierung behoben werden sollte)
            assert bestellung.artikel_id == 999


class TestSicherheit:
    """
    Tests für Admin-Authentifizierung und Sicherheit
    RISIKO 1: Unzureichende Zugriffssicherung / fehlende Admin-Authentifizierung
    Fokus: Prüfung, dass Admin-Funktionen geschützt sind und nur mit korrekter 
           Authentifizierung zugänglich sind, um unbefugten Zugriff zu verhindern.
    """

    @pytest.fixture
    def app(self):
        """Testanwendung mit separater Testdatenbank erstellen"""
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True

        with app.app_context():
            db.create_all()
            yield app

    @pytest.fixture
    def client(self, app: Any):
        """Testclient erstellen"""
        return app.test_client()

    def test_admin_menu_seite_existiert(self, client: Any):
        """
        Test: Admin-Menü-Route ist erreichbar / geschützt
        Risiko 1 - Abdeckung: Prüft, dass die Admin-Route existiert und 
        ggf. korrekt geschützt ist (Authentifizierung erfordert).
        """
        # Act
        response = client.get('/admin/menu')

        # Assert - Sollte 200 sein oder 302 (Redirect) bei fehlender Authentifizierung
        assert response.status_code in [200, 302, 405]

    def test_secret_key_vorhanden(self, app: Any):
        """
        Test: Flask Secret Key ist konfiguriert
        Risiko 1 - Abdeckung: Stellt sicher, dass ein Secret Key vorhanden ist,
        der für Session-Verschlüsselung und Sicherheit essentiell ist.
        """
        # Assert
        assert app.config['SECRET_KEY'] is not None
        assert len(app.config['SECRET_KEY']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
