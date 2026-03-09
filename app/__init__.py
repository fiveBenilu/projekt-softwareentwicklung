from flask import Flask, redirect
from flask_migrate import Migrate
from app.models import db  # WICHTIG: Diese Instanz wird in models.py erzeugt

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafe.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'dein-geheimer-schlüssel'

    # ✅ Datenbank-Instanz mit App verknüpfen
    db.init_app(app)

    # ✅ Flask-Migrate aktivieren
    migrate = Migrate(app, db)

    # 📌 Damit Flask-Migrate alle Modelle kennt (z. B. TischLayout)
    from app import models

    # ✅ Optional: Tabellen direkt erstellen (nur bei Bedarf)
    with app.app_context():
        db.create_all()

    # 🔹 Blueprints registrieren
    from .routes.home_routes import home_bp
    from .routes.admin_routes import admin_bp
    from .routes.theke_routes import theke_bp
    from .routes.tisch_routes import tisch_bp
    from .routes.layout_routes import layout_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(theke_bp)
    app.register_blueprint(tisch_bp)
    app.register_blueprint(layout_bp)

    @app.route('/')
    def index():
        return redirect('/home')

    return app