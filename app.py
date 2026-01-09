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
        dane_protokolu = protokol_db
        # Pobieranie wyników kandydatów do słownika
        wyniki = {w.id_kandydat: w.l_glosow for w in WynikKandydata.query.filter_by(nr_obwod=nr).all()}
          
    else:
        # Jeśli nie ma w bazie, tworzymy obiekt z poprawnymi nazwami pól
        dane_protokolu = Protokol(
            nr_obwod=nr, 
            l_uprawn=0,             # Poprawione z l_wyborcow
            l_kart_wydan=0,         # Poprawione z l_kart_wydanych
            l_kart_wyjet=0,         # Poprawione z l_kart_wyjetych
            l_glos_niewaz=0,        # Poprawione z l_glos_niewaznych
            l_kart_wyjet_waz=0,     # Poprawione z l_kart_waznych
            l_glos_niewaz_zlyx=0, 
            l_glos_niewaz_inne=0, 
            l_glos_waz=0, 
            zatw=0
        )
        wyniki = {}

    kandydaci = Kandydat.query.filter_by(dzielnica=obwod.dzielnica).order_by(Kandydat.lp).all()

    return render_template('dashboard.html',
                           obwod=obwod,
                           dane=dane_protokolu, # dane protokolu
                           kandydaci=kandydaci,
                           wyniki=wyniki,
                           lista_widocznych_obwodow=lista_widocznych_obwodow,
                           wybrano_nr=nr,
                           statusy=statusy)


@app.route('/save_protokol/<int:nr>', methods=['POST'])
@login_required
def save_protokol(nr):
    if not is_admin() and nr != current_user.nr_obwodu:
        flash('Brak uprawnień do edycji tego obwodu.', 'danger')
        return redirect(url_for('dashboard'))

    p = Protokol.query.filter_by(nr_obwod=nr).first()
    
    if not p:
        # Tworzymy nowy rekord jeśli nie istnieje
        obwod_info = Obwod.query.filter_by(nr_obwod=nr).first()
        p = Protokol(nr_obwod=nr)
        p.dzielnica = obwod_info.dzielnica if obwod_info else "Nieznana"
        db.session.add(p)
    
    # Jeśli protokół jest zatwierdzony, tylko admin może go edytować
    if p.zatw == 1 and not is_admin():
        flash('Protokół jest zatwierdzony i zablokowany do edycji.', 'danger')
        return redirect(url_for('dashboard', nr=nr))

    try:
        # MAPOWANIE NA TWOJE NAZWY Z KLASY PROTOKOL (models.py)
        p.l_uprawn = int(request.form.get('k1', 0))
        p.l_kart_wydan = int(request.form.get('k2', 0))
        p.l_kart_wyjet = int(request.form.get('k3', 0))
        p.l_kart_wyjet_niewaz = int(request.form.get('k4', 0))
        p.l_kart_wyjet_waz = int(request.form.get('k5', 0))
        p.l_glos_niewaz = int(request.form.get('k6', 0))
        p.l_glos_niewaz_zlyx = int(request.form.get('k7a', 0))
        p.l_glos_niewaz_inne = int(request.form.get('k7b', 0))
        p.l_glos_waz = int(request.form.get('k8', 0))
        
        p.data_edycji = datetime.utcnow()

        # Zapis głosów na kandydatów
        WynikKandydata.query.filter_by(nr_obwod=nr).delete()
        for key, value in request.form.items():
            if key.startswith('kandydat_'):
                try:
                    k_id = int(key.split('_')[1])
                    glosy = int(value) if value else 0
                    nowy_wynik = WynikKandydata(nr_obwod=nr, id_kandydat=k_id, l_glosow=glosy)
                    db.session.add(nowy_wynik)
                except:
                    continue

        db.session.commit()
        flash(f'Zapisano dane obwodu nr {nr}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Błąd zapisu: {str(e)}', 'danger')

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


@app.route('/operatorzy/delete/<int:id>', methods=['POST'])
@login_required
def delete_operator(id):
    if not is_admin():
        flash('Brak uprawnień', 'danger')
        return redirect(url_for('lista_operatorow'))

    op = Operator.query.get_or_404(id)
    db.session.delete(op)
    db.session.commit()

    flash('Operator usunięty', 'success')
    return redirect(url_for('lista_operatorow'))

@app.route('/operatorzy/save', methods=['POST'])
@login_required
def save_operator():
    if not is_admin():
        flash('Brak uprawnień', 'danger')
        return redirect(url_for('lista_operatorow'))

    op_id = request.form.get('id_operator')
    login = request.form.get('login')
    haslo = request.form.get('password')
    nr_obwodu = request.form.get('nr_obwodu')
    rola = request.form.get('rola', 'OPERATOR')

    if not login or not nr_obwodu:
        flash('Login i numer obwodu są wymagane', 'danger')
        return redirect(url_for('lista_operatorow'))

    # --- UPDATE ---
    if op_id:
        op = Operator.query.get_or_404(int(op_id))

        # sprawdzamy duplikat loginu, ale Z WYŁĄCZENIEM siebie
        dup = Operator.query.filter(
            Operator.login == login,
            Operator.id_operator != op.id_operator
        ).first()

        if dup:
            flash('Inny operator o takim loginie już istnieje', 'danger')
            return redirect(url_for('lista_operatorow'))

        op.login = login
        op.nr_obwodu = int(nr_obwodu)
        op.rola = rola

        if haslo:
            op.haslo_hash = haslo  # MVP

        db.session.commit()
        flash('Operator zaktualizowany', 'success')
        return redirect(url_for('lista_operatorow'))

    # --- CREATE ---
    if Operator.query.filter_by(login=login).first():
        flash('Operator o takim loginie już istnieje', 'danger')
        return redirect(url_for('lista_operatorow'))

    op = Operator(
        login=login,
        nr_obwodu=int(nr_obwodu),
        rola=rola,
        haslo_hash=haslo
    )

    if not haslo:
        flash('Hasło jest wymagane przy tworzeniu nowego operatora', 'danger')
        return redirect(url_for('lista_operatorow'))

    db.session.add(op)
    db.session.commit()
    flash('Operator dodany', 'success')
    return redirect(url_for('lista_operatorow'))


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