import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, Operator, Obwod, Kandydat, Protokol, WynikKandydata, Dzielnica
from sqlalchemy import func

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(uid):
    return Operator.query.get(int(uid))

def is_admin():
    return current_user.is_authenticated and str(current_user.rola).upper() == 'ADMIN'

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_val = request.form.get('login')
        haslo_val = request.form.get('password')
        user = Operator.query.filter_by(login=login_val).first()
        if user and user.haslo_hash == haslo_val:
            user.data_ost_logowania = datetime.utcnow()
            db.session.commit()
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Błędny login lub hasło', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@app.route('/dashboard/<int:nr>')
@login_required
def dashboard(nr=None):
    # Logika uprawnień i menu bocznego
    if is_admin():
        obwody_all = Obwod.query.order_by(Obwod.nr_obwod).all()
    else:
        obwody_all = Obwod.query.filter_by(nr_obwod=current_user.nr_obwodu).all()
    
    lista_widocznych_obwodow = [o.nr_obwod for o in obwody_all]
    statusy = {p.nr_obwod: ('zatw' if p.zatw == 1 else 'edit') for p in Protokol.query.all()}

    if nr is None:
        return render_template('dashboard_empty.html', 
                               lista_widocznych_obwodow=lista_widocznych_obwodow, 
                               statusy=statusy)

    if not is_admin() and nr != current_user.nr_obwodu:
        flash('Brak uprawnień do tego obwodu.', 'danger')
        return redirect(url_for('dashboard'))

    obwod = Obwod.query.filter_by(nr_obwod=nr).first_or_404()
    
    # KLUCZOWE: Pobieranie protokołu
    protokol_db = Protokol.query.filter_by(nr_obwod=nr).first()
    
    if protokol_db:
        dane_dla_html = protokol_db
        # Pobieranie wyników kandydatów do słownika
        wyniki = {w.id_kandydat: w.l_glosow for w in WynikKandydata.query.filter_by(nr_obwod=nr).all()}
    else:
        # Jeśli nie ma w bazie, tworzymy "pusty" obiekt modelu Protokol
        # Dzięki temu {{ dane.l_wyborcow }} w HTML nie wyrzuci błędu, tylko pokaże 0
        dane_dla_html = Protokol(
            nr_obwod=nr, l_wyborcow=0, l_kart_wydanych=0, l_kart_wyjetych=0,
            l_kart_niewaznych=0, l_kart_waznych=0, l_glos_niewaznych=0,
            l_glos_niewaz_zlyx=0, l_glos_niewaz_inne=0, l_glos_waz=0, zatw=0
        )
        wyniki = {}

    kandydaci = Kandydat.query.filter_by(dzielnica=obwod.dzielnica).order_by(Kandydat.lp).all()

    return render_template('dashboard.html',
                           obwod=obwod,
                           dane=dane_dla_html, # Ta nazwa MUSI być 'dane'
                           kandydaci=kandydaci,
                           wyniki=wyniki,
                           lista_widocznych_obwodow=lista_widocznych_obwodow,
                           wybrano_nr=nr,
                           statusy=statusy)



@app.route('/save_protokol/<int:nr>', methods=['POST'])
@login_required
def save_protokol(nr):
    if not is_admin() and nr != current_user.nr_obwodu:
        return redirect(url_for('dashboard'))
    
    obwod = Obwod.query.filter_by(nr_obwod=nr).first_or_404()
    p = Protokol.query.filter_by(nr_obwod=nr).first()
    
    if not p:
        p = Protokol()
        p.nr_obwod = nr
        p.dzielnica = obwod.dzielnica
        db.session.add(p)
    
    if p.zatw == 1 and not is_admin():
        flash('Protokół zablokowany do edycji.', 'danger')
        return redirect(url_for('dashboard', nr=nr))
    
    # Pobieranie danych z formularza (k1-k8)
    p.l_wyborcow = int(request.form.get('k1', 0))
    p.l_kart_wydanych = int(request.form.get('k2', 0))
    p.l_kart_wyjetych = int(request.form.get('k3', 0))
    p.l_kart_niewaznych = int(request.form.get('k4', 0))
    p.l_kart_waznych = int(request.form.get('k5', 0))
    p.l_glos_niewaznych = int(request.form.get('k6', 0))
    p.l_glos_niewaz_zlyx = int(request.form.get('k7a', 0))
    p.l_glos_niewaz_inne = int(request.form.get('k7b', 0))
    p.l_glos_waz = int(request.form.get('k8', 0))
    p.data_edycji = datetime.utcnow()

    # Wyniki kandydatów - usuwamy stare i dodajemy nowe
    WynikKandydata.query.filter_by(nr_obwod=nr).delete()
    for key, value in request.form.items():
        if key.startswith('kandydat_'):
            k_id = int(key.split('_')[1])
            db.session.add(WynikKandydata(nr_obwod=nr, id_kandydat=k_id, l_glosow=int(value or 0)))
    
    db.session.commit()
    flash(f'Zapisano obwód {nr}', 'success')
    return redirect(url_for('dashboard', nr=nr))

# Zarządzanie administratorem (Kandydaci/Operatorzy)
@app.route('/kandydaci')
@login_required
def lista_kandydatow():
    if not is_admin(): return redirect(url_for('index'))
    dzielnice = [d.nazwa for d in Dzielnica.query.order_by(Dzielnica.nazwa).all()]
    kandydaci = Kandydat.query.order_by(Kandydat.dzielnica, Kandydat.lp).all()
    obwody_all = Obwod.query.order_by(Obwod.nr_obwod).all()
    lista_widocznych_obwodow = [o.nr_obwod for o in obwody_all]
    statusy = {p.nr_obwod: ('zatw' if p.zatw == 1 else 'edit') for p in Protokol.query.all()}
    return render_template('kandydaci.html', kandydaci=kandydaci, dzielnice=dzielnice, 
                           lista_widocznych_obwodow=lista_widocznych_obwodow, statusy=statusy)

@app.route('/operatorzy')
@login_required
def lista_operatorow():
    if not is_admin(): return redirect(url_for('index'))
    ops = Operator.query.all()
    obwody_all = Obwod.query.order_by(Obwod.nr_obwod).all()
    lista_widocznych_obwodow = [o.nr_obwod for o in obwody_all]
    statusy = {p.nr_obwod: ('zatw' if p.zatw == 1 else 'edit') for p in Protokol.query.all()}
    return render_template('operatorzy.html', operatorzy=ops, 
                           lista_widocznych_obwodow=lista_widocznych_obwodow, statusy=statusy)

@app.route('/zatwierdz_protokol/<int:nr>', methods=['POST'])
@login_required
def zatwierdz_protokol(nr):
    p = Protokol.query.filter_by(nr_obwod=nr).first_or_404()
    p.zatw = 1
    p.data_zatwierdzenia = datetime.utcnow()
    db.session.commit()
    return redirect(url_for('dashboard', nr=nr))

@app.route('/odblokuj_protokol/<int:nr>', methods=['POST'])
@login_required
def odblokuj_protokol(nr):
    if not is_admin(): return redirect(url_for('index'))
    p = Protokol.query.filter_by(nr_obwod=nr).first_or_404()
    p.zatw = 0
    db.session.commit()
    return redirect(url_for('dashboard', nr=nr))

if __name__ == '__main__':
    app.run(debug=True)