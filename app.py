import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, Operator, Obwod, Kandydat, Protokol, WynikKandydata

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(uid):
    return Operator.query.get(int(uid))

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
        flash('Błąd logowania', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/operatorzy')
@login_required
def lista_operatorow():
    if current_user.rola != 'ADMIN':
        flash('Brak uprawnień.', 'danger')
        return redirect(url_for('dashboard'))
    ops = Operator.query.all()
    return render_template('operatorzy.html', operatorzy=ops)

@app.route('/operator/save', methods=['POST'])
@login_required
def save_operator():
    if current_user.rola != 'ADMIN': return "Forbidden", 403
    
    op_id = request.form.get('id_operator')
    login_val = request.form.get('login')
    rola_val = request.form.get('rola')
    haslo_val = request.form.get('password')
    nr_obwodu_val = request.form.get('nr_obwodu')

    if op_id: 
        op = Operator.query.get(op_id)
        if haslo_val: op.haslo_hash = haslo_val
        op.login = login_val
        op.rola = rola_val
        op.nr_obwodu = nr_obwodu_val
    else:
        nowy_op = Operator(
            login=login_val, 
            haslo_hash=haslo_val, 
            rola=rola_val,
            nr_obwodu=nr_obwodu_val
        )
        db.session.add(nowy_op)
    
    db.session.commit()
    flash('Dane operatora zostały zapisane.', 'success')
    return redirect(url_for('lista_operatorow'))

@app.route('/operator/delete/<int:id>', methods=['POST'])
@login_required
def delete_operator(id):
    if current_user.rola != 'ADMIN': return "Forbidden", 403
    op = Operator.query.get_or_404(id)
    db.session.delete(op)
    db.session.commit()
    flash('Operator usunięty.', 'info')
    return redirect(url_for('lista_operatorow'))

@app.route('/dashboard')
@app.route('/dashboard/<int:nr>')
@login_required
def dashboard(nr=None):
    # Logika wyznaczania dostępnych obwodów
    if current_user.rola == 'ADMIN':
        lista_widocznych = list(range(1, app.config['OKW_COUNT'] + 1))
        if nr is None: nr = 1
    else:
        moj_nr = getattr(current_user, 'nr_obwodu', None)
        if moj_nr:
            lista_widocznych = [moj_nr]
            # Zabezpieczenie przed dostępem do innego obwodu
            if nr is None or nr != moj_nr:
                return redirect(url_for('dashboard', nr=moj_nr))
        else:
            flash('Błąd: Nie masz przypisanego obwodu.', 'danger')
            lista_widocznych = []
            if nr is not None:
                return redirect(url_for('dashboard'))

    obwod = Obwod.query.filter_by(nr_obwod=nr).first_or_404()
    kandydaci = Kandydat.query.filter_by(dzielnica=obwod.dzielnica).order_by(Kandydat.lp).all()
    protokol = Protokol.query.filter_by(nr_obwod=nr).first()
    glosy = WynikKandydata.query.filter_by(nr_obwod=nr).all()
    glosy_dict = {g.id_kandydat: g.l_glosow for g in glosy}
    
    statusy_db = Protokol.query.all()
    statusy = {p.nr_obwod: ('zatw' if p.zatw == 1 else 'edit') for p in statusy_db}
    
    return render_template('dashboard.html', 
                           obwod=obwod, 
                           wybrano_nr=nr,
                           kandydaci=kandydaci,
                           dane=protokol, 
                           glosy_dict=glosy_dict,
                           statusy=statusy,
                           lista_widocznych_obwodow=lista_widocznych)

@app.route('/save_protokol/<int:nr>', methods=['POST'])
@login_required
def save_protokol(nr):
    protokol = Protokol.query.filter_by(nr_obwod=nr).first()
    
    if protokol and protokol.zatw == 1 and current_user.rola != 'ADMIN':
        flash('Protokół jest zatwierdzony i zablokowany do edycji.', 'danger')
        return redirect(url_for('dashboard', nr=nr))

    obw = Obwod.query.filter_by(nr_obwod=nr).first_or_404()
    if not protokol:
        protokol = Protokol(nr_obwod=nr, dzielnica=obw.dzielnica)
        db.session.add(protokol)

    protokol.glos_od = request.form.get('glos_od', '08:00')
    protokol.glos_do = request.form.get('glos_do', '17:00')
    protokol.l_uprawn = int(request.form.get('k2', 0))
    protokol.l_kart_otrzym = int(request.form.get('k3', 0))
    protokol.l_kart_niewyk = int(request.form.get('k4', 0))
    protokol.l_kart_wydan = int(request.form.get('k5', 0))
    protokol.l_kart_wyjet = int(request.form.get('k6', 0))
    protokol.l_kart_wyjet_niewaz = int(request.form.get('k6a', 0))
    protokol.l_kart_wyjet_waz = int(request.form.get('k6b', 0))
    protokol.l_glos_niewaz = int(request.form.get('k7', 0))
    protokol.l_glos_niewaz_zlyx = int(request.form.get('k7a', 0))
    protokol.l_glos_niewaz_inne = int(request.form.get('k7b', 0))
    protokol.l_glos_waz = int(request.form.get('k8', 0))
    protokol.data_edycji = datetime.utcnow()

    WynikKandydata.query.filter_by(nr_obwod=nr).delete()
    for key, value in request.form.items():
        if key.startswith('kandydat_'):
            k_id = int(key.split('_')[1])
            db.session.add(WynikKandydata(nr_obwod=nr, id_kandydat=k_id, l_glosow=int(value or 0)))

    db.session.commit()
    flash(f'Zapisano zmiany w obwodzie {nr}', 'success')
    return redirect(url_for('dashboard', nr=nr))

@app.route('/zatwierdz_protokol/<int:nr>', methods=['POST'])
@login_required
def zatwierdz_protokol(nr):
    protokol = Protokol.query.filter_by(nr_obwod=nr).first_or_404()
    protokol.zatw = 1
    protokol.data_zatwierdzenia = datetime.utcnow()
    db.session.commit()
    flash(f'Protokół nr {nr} został ZATWIERDZONY.', 'warning')
    return redirect(url_for('dashboard', nr=nr))

@app.route('/odblokuj_protokol/<int:nr>', methods=['POST'])
@login_required
def odblokuj_protokol(nr):
    if current_user.rola != 'ADMIN':
        flash('Brak uprawnień.', 'danger')
        return redirect(url_for('dashboard', nr=nr))
    protokol = Protokol.query.filter_by(nr_obwod=nr).first_or_404()
    protokol.zatw = 0
    db.session.commit()
    flash(f'Admin odblokował obwód {nr}.', 'info')
    return redirect(url_for('dashboard', nr=nr))

if __name__ == '__main__':
    app.run(debug=True)