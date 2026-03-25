# app/routes/tisch_routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
import os
import json
from datetime import datetime
import uuid
from app import db
from app.models import Artikel, Bestellung
from collections import defaultdict

tisch_bp = Blueprint('tisch', __name__, url_prefix='/tisch')

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
BESTELLUNGEN_FILE = os.path.join(DATA_DIR, 'orders.json')


@tisch_bp.route('/<int:tisch_id>', methods=['GET'])
def tisch(tisch_id):
    return render_template('tisch_menu.html', tisch_id=tisch_id)


@tisch_bp.route('/<int:tisch_id>/speisekarte', methods=['GET'])
def speisekarte(tisch_id):
    # Menü direkt aus der DB laden

    # Artikel nach Kategorie gruppieren
    artikel_liste = Artikel.query.all()
    artikel_gruppen = defaultdict(list)
    
    for artikel in artikel_liste:
        artikel_gruppen[artikel.kategorie or "Sonstiges"].append(artikel)

    # Warenkorb aus Session holen
    cart_key = f"warenkorb_{tisch_id}"
    cart = session.get(cart_key, [])

    # Einzelnes Produkt löschen (via Query-Parameter z.B. ?remove=1)
    remove_index = request.args.get('remove')
    if remove_index is not None:
        try:
            remove_index = int(remove_index)
            if 0 <= remove_index < len(cart):
                del cart[remove_index]
                session[cart_key] = cart
                flash("🗑️ Artikel entfernt!")
                return redirect(url_for('tisch.speisekarte', tisch_id=tisch_id))
        except ValueError:
            pass

    return render_template('tisch_bestellen.html', artikel_gruppen=artikel_gruppen, tisch_id=tisch_id, cart=cart)


@tisch_bp.route('/<int:tisch_id>/in_warenkorb', methods=['POST'])
def in_warenkorb(tisch_id):
    artikel_name = request.form.get('artikel')
    menge = request.form.get('menge')

    if not artikel_name or not menge:
        flash("❌ Bitte Artikel und Menge angeben!")
        return redirect(url_for('tisch.speisekarte', tisch_id=tisch_id))

    artikel_obj = Artikel.query.filter_by(name=artikel_name).first()
    if not artikel_obj:
        flash("❌ Artikel nicht gefunden!")
        return redirect(url_for('tisch.speisekarte', tisch_id=tisch_id))

    eintrag = {
        "artikel_id": artikel_obj.id,
        "artikel": artikel_obj.name,
        "menge": int(menge),
        "preis": float(artikel_obj.preis)
    }

    cart_key = f"warenkorb_{tisch_id}"
    warenkorb = session.get(cart_key, [])
    warenkorb.append(eintrag)
    session[cart_key] = warenkorb

    flash("✅ Zum Warenkorb hinzugefügt!")
    return redirect(url_for('tisch.speisekarte', tisch_id=tisch_id))


@tisch_bp.route('/<int:tisch_id>/warenkorb/remove')
def warenkorb_entfernen(tisch_id):
    remove_index = request.args.get('remove')
    cart_key = f"warenkorb_{tisch_id}"
    cart = session.get(cart_key, [])

    if remove_index is not None:
        try:
            idx = int(remove_index)
            if 0 <= idx < len(cart):
                del cart[idx]
                session[cart_key] = cart
                flash("🗑️ Artikel entfernt!")
        except ValueError:
            pass

    return redirect(url_for('tisch.warenkorb_ansehen', tisch_id=tisch_id))


@tisch_bp.route('/<int:tisch_id>/bestellen', methods=['POST'])
def bestellen(tisch_id):
    warenkorb = session.get(f'warenkorb_{tisch_id}', [])

    if not warenkorb:
        flash("🛒 Der Warenkorb ist leer.")
        return redirect(url_for('tisch.speisekarte', tisch_id=tisch_id))

    for eintrag in warenkorb:
        speichere_bestellung(
            tisch_id,
            "bestellung",
            artikel_id=eintrag.get("artikel_id"),
            artikel=eintrag.get("artikel"),
            menge=eintrag["menge"]
        )

    session.pop(f'warenkorb_{tisch_id}', None)
    flash("✅ Bestellung wurde gesendet!")
    return redirect(url_for('tisch.danke', tisch_id=tisch_id, typ='bestellung'))

@tisch_bp.route('/<int:tisch_id>/danke')
def danke(tisch_id):
    typ = request.args.get('typ', 'bestellung')
    return render_template("danke.html", tisch_id=tisch_id, typ=typ)

@tisch_bp.route('/<int:tisch_id>/hilfe', methods=['POST'])
def hilfe(tisch_id):
    speichere_bestellung(tisch_id, "hilfe")
    return redirect(url_for('tisch.danke', tisch_id=tisch_id, typ='hilfe'))


@tisch_bp.route('/<int:tisch_id>/rechnung', methods=['POST'])
def rechnung(tisch_id):
    speichere_bestellung(tisch_id, "rechnung")
    return redirect(url_for('tisch.danke', tisch_id=tisch_id, typ='rechnung'))



def speichere_bestellung(tisch_id, aktion, artikel_id=None, artikel=None, menge=None):
    bestellung = Bestellung(
        tisch_id=tisch_id,
        aktion=aktion,
        artikel_id=artikel_id,
        artikel=artikel,
        menge=menge
    )
    db.session.add(bestellung)
    db.session.commit()

@tisch_bp.route('/<int:tisch_id>/warenkorb')
def warenkorb_ansehen(tisch_id):
    cart_key = f"warenkorb_{tisch_id}"
    cart = session.get(cart_key, [])  # ⬅️ WICHTIG: cart definieren, bevor du es nutzt

    gesamtpreis = 0
    for item in cart:
        artikel_obj = None
        if item.get("artikel_id") is not None:
            artikel_obj = Artikel.query.get(item["artikel_id"])

        if artikel_obj is None and item.get("artikel"):
            artikel_obj = Artikel.query.filter_by(name=item["artikel"]).first()

        if artikel_obj:
            item["artikel_id"] = artikel_obj.id
            item["artikel"] = artikel_obj.name
            item["preis"] = artikel_obj.preis  # Preis wird nur temporär dem dict hinzugefügt
            gesamtpreis += artikel_obj.preis * item["menge"]
        else:
            item["preis"] = 0.0  # Fallback falls Artikel nicht gefunden wird

    return render_template('warenkorb.html', tisch_id=tisch_id, cart=cart, gesamtpreis=gesamtpreis)

@tisch_bp.route('/tisch/<int:tisch_id>')
def tisch_view(tisch_id):
    artikel_liste = Artikel.query.all()  # ⛔️ ersetzt
    # 👉 Besser:
    artikel_liste = Artikel.query.order_by(Artikel.kategorie, Artikel.name).all()

    return render_template("tisch.html", artikel=artikel_liste, tisch_id=tisch_id)