import os
from flask import Flask, redirect
from flask_migrate import Migrate
from app.models import db  # WICHTIG: Diese Instanz wird in models.py erzeugt


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafe.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.environ.get('SECRET_KEY', 'dein-geheimer-schluessel')

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
    from .routes.setup import main as main_setup_bp
    from .routes.auth_routes import auth_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(theke_bp)
    app.register_blueprint(tisch_bp)
    app.register_blueprint(layout_bp)
    app.register_blueprint(main_setup_bp)
    app.register_blueprint(auth_bp)

    @app.cli.command('create-admin')
    def create_admin():
        """Create an admin account from the command line."""
        from app.models import User
        from werkzeug.security import generate_password_hash
        import getpass

        username = input('Admin-Benutzername: ').strip()
        if not username:
            print('Benutzername darf nicht leer sein.')
            return
        password = getpass.getpass('Passwort: ')
        password_confirm = getpass.getpass('Passwort bestätigen: ')
        if password != password_confirm:
            print('Passwörter stimmen nicht überein.')
            return
        if User.query.filter_by(username=username).first():
            print('Benutzername existiert bereits.')
            return
        user = User(username=username, password_hash=generate_password_hash(password), is_admin=True)
        db.session.add(user)
        db.session.commit()
        print('Admin-Konto wurde erstellt.')

    return app

    @app.route('/')
    def index():
        return redirect('/home')

    return app