from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

class Dzielnica(db.Model):
    __tablename__ = 'DZIELNICE'
    id_dzielnica = db.Column('ID_DZIELNICA', db.Integer, primary_key=True, autoincrement=True)
    nazwa = db.Column('NAZWA', db.Text, nullable=False, unique=True)
    mandaty = db.Column('MANDATY', db.Integer, nullable=False)

class Obwod(db.Model):
    __tablename__ = 'OBWODY'
    id_obwod = db.Column('ID_OBWOD', db.Integer, primary_key=True, autoincrement=True)
    dzielnica = db.Column('DZIELNICA', db.Text, db.ForeignKey('DZIELNICE.NAZWA'), nullable=False)
    nr_obwod = db.Column('NR_OBWOD', db.Integer, nullable=False, unique=True)
    gran_obwod = db.Column('GRAN_OBWOD', db.Text)
    siedz_obwod = db.Column('SIEDZ_OBWOD', db.Text)
    niepelnospr = db.Column('NIEPELNOSPR', db.Integer, default=1)

class Kandydat(db.Model):
    __tablename__ = 'KANDYDACI'
    id_kandydat = db.Column('ID_KANDYDAT', db.Integer, primary_key=True, autoincrement=True)
    dzielnica = db.Column('DZIELNICA', db.Text, db.ForeignKey('DZIELNICE.NAZWA'), nullable=False)
    lp = db.Column('LP', db.Integer, nullable=False)
    imie = db.Column('IMIE', db.Text, nullable=False)
    nazwisko = db.Column('NAZWISKO', db.Text, nullable=False)

class Protokol(db.Model):
    __tablename__ = 'PROTOKOLY'
    id_protokol = db.Column('ID_PROTOKOL', db.Integer, primary_key=True, autoincrement=True)
    nr_obwod = db.Column('NR_OBWOD', db.Integer, db.ForeignKey('OBWODY.NR_OBWOD'), nullable=False, unique=True)
    dzielnica = db.Column('DZIELNICA', db.Text, nullable=False)
    glos_od = db.Column('GLOS_OD', db.Text)
    glos_do = db.Column('GLOS_DO', db.Text)
    l_uprawn = db.Column('L_UPRAWN', db.Integer, default=0)
    l_kart_otrzym = db.Column('L_KART_OTRZYM', db.Integer, default=0)
    l_kart_niewyk = db.Column('L_KART_NIEWYK', db.Integer, default=0)
    l_kart_wydan = db.Column('L_KART_WYDAN', db.Integer, default=0)
    l_kart_wyjet = db.Column('L_KART_WYJET', db.Integer, default=0)
    l_kart_wyjet_niewaz = db.Column('L_KART_WYJET_NIEWAZ', db.Integer, default=0)
    l_kart_wyjet_waz = db.Column('L_KART_WYJET_WAZ', db.Integer, default=0)
    l_glos_niewaz = db.Column('L_GLOS_NIEWAZ', db.Integer, default=0)
    l_glos_niewaz_zlyx = db.Column('L_GLOS_NIEWAZ_ZLYX', db.Integer, default=0)
    l_glos_niewaz_inne = db.Column('L_GLOS_NIEWAZ_INNE', db.Integer, default=0)
    l_glos_waz = db.Column('L_GLOS_WAZ', db.Integer, default=0)
    zatw = db.Column('ZATW', db.Integer, default=0)
    data_zatwierdzenia = db.Column('DATA_ZATWIERDZENIA', db.DateTime)
    data_edycji = db.Column('DATA_EDYCJI', db.DateTime, default=datetime.utcnow)

class WynikKandydata(db.Model):
    __tablename__ = 'PROTOKOL_KANDYDAT_GLOSY'
    nr_obwod = db.Column('NR_OBWOD', db.Integer, db.ForeignKey('PROTOKOLY.NR_OBWOD'), primary_key=True)
    id_kandydat = db.Column('ID_KANDYDAT', db.Integer, db.ForeignKey('KANDYDACI.ID_KANDYDAT'), primary_key=True)
    l_glosow = db.Column('L_GLOSOW', db.Integer, default=0)

class Operator(db.Model, UserMixin):
    __tablename__ = 'OPERATORZY'
    id_operator = db.Column('ID_OPERATOR', db.Integer, primary_key=True, autoincrement=True)
    login = db.Column('LOGIN', db.Text, nullable=False, unique=True)
    haslo_hash = db.Column('HASLO_HASH', db.Text, nullable=False)
    rola = db.Column('ROLA', db.Text, nullable=False)
    nr_obwodu = db.Column('NR_OBWODU', db.Integer)
    aktywny = db.Column('AKTYWNY', db.Integer, default=1)
    
    def get_id(self):
        return str(self.id_operator)

class Setup(db.Model):
    __tablename__ = 'SETUP'
    variable_txt = db.Column('VARIABLE_TXT', db.Text, primary_key=True)
    value_txt = db.Column('VALUE_TXT', db.Text)