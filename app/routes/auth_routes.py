from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/admin')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username, is_admin=True).first()
        if user and check_password_hash(user.password_hash, password):
            session['admin_logged_in'] = True
            session['admin_username'] = user.username
            next_page = request.args.get('next') or url_for('admin.dashboard')
            if not next_page.startswith('/'):
                next_page = url_for('admin.dashboard')
            flash('Login erfolgreich.')
            return redirect(next_page)

        flash('Benutzername oder Passwort ist falsch.')

    admins_exist = User.query.filter_by(is_admin=True).count() > 0
    return render_template('admin_login.html', admins_exist=admins_exist)

@auth_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('Sie wurden abgemeldet.')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    admin_exists = User.query.filter_by(is_admin=True).first()
    if admin_exists:
        flash('Ein Admin-Konto existiert bereits. Bitte melden Sie sich an.')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        if not username or not password:
            flash('Bitte Benutzername und Passwort eingeben.')
            return redirect(url_for('auth.register'))

        if password != password_confirm:
            flash('Die Passwörter stimmen nicht überein.')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(username=username).first():
            flash('Der Benutzername ist bereits vergeben.')
            return redirect(url_for('auth.register'))

        user = User(username=username, password_hash=generate_password_hash(password), is_admin=True)
        db.session.add(user)
        db.session.commit()
        flash('Admin-Konto wurde angelegt. Bitte melden Sie sich an.')
        return redirect(url_for('auth.login'))

    return render_template('admin_register.html')
