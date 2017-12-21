# Installation - pip3 install Flask

from flask import Flask, request, session
from flask import render_template

from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, Float, Boolean, select

import hashlib

app = Flask(__name__)
app.config.from_pyfile('config.cfg')

# Base de données (e.g. SQLite)
# SQL Alchemy - http://www.sqlalchemy.org/

db = create_engine('sqlite:///sqlite.bdd', echo=True, convert_unicode=True)
metadata = MetaData(bind=db)

# Création des tables
users = Table('users', metadata,
              Column('name', String(30), primary_key=True),
              Column('email', String(50)),
              Column('password', String),
              Column('admin', Boolean, default=False),
              Column('elo', Float, default=1200),
              Column('nbGame', Integer, default=0),
              )


salt = '00eb8b6ceaae4d49ba7444344ecbee2e'


def hash(password):
    return hashlib.sha512(password.encode('utf-8') + salt.encode('utf-8')).hexdigest()


def create_user(**kwargs):
    return users.insert().execute(**kwargs)


def p(D):
    return 1/(1+10**(-D/400))


def new_elo(player1, player2, score1, score2):
    K = 40 if player1.nbGame < 30 else 20 if player1.elo < 2400 else 10
    W = 1 if score1 > score2 else 0.5 if score1 == score2 else 0
    D = player1.elo-player2.elo
    return player1.elo + K*(W-p(D))


def do_match(player1, player2, score1, score2):
    if player1 == player2:
        return
    player1 = select(
        [users.c.name, users.c.elo, users.c.nbGame]
    ).where(
        users.c.name == player1
    ).execute().first()

    player2 = select(
        [users.c.name, users.c.elo, users.c.nbGame]
    ).where(
        users.c.name == player2
    ).execute().first()

    elo1 = new_elo(player1, player2, score1, score2)
    elo2 = new_elo(player2, player1, score2, score1)

    users.update().values(
        nbGame=player1.nbGame+1,
        elo=elo1
        ).where(users.c.name == player1.name).execute()
    users.update().values(
        nbGame=player2.nbGame+1,
        elo=elo2
        ).where(users.c.name == player2.name).execute()


@app.route('/', methods=['GET', 'POST'])
def dashboard():
    if request.method == 'POST':
        if request.form['type'] == 'match':
            do_match(
                request.form['player1'],
                request.form['player2'],
                request.form['score1'],
                request.form['score2'],
            )
        elif request.form['type'] == 'player':
            create_user(
                name=request.form['name'],
                email=request.form['email'],
                password=hash(request.form['password']),
            )

    players = select([users.c.name, users.c.elo]).order_by(users.c.elo.desc()).execute()

    players = tuple(map(dict, players))
    for i in range(len(players)):
        if i != 0 and players[i]['elo'] == players[i-1]['elo']:
            players[i]['rank'] = players[i-1]['rank']
        else:
            players[i]['rank'] = i+1
    return render_template('dashboard.html', players=players)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        u = select(
            [users.c.name, users.c.password, users.c.admin]
        ).where(
            users.c.name == request.form['name']
        ).where(
            users.c.password == hash(request.form['password']),
        ).execute()
        print(request.form['password'])
        print(hash(request.form['password']))
        print(list(select(
            [users.c.password]
        ).execute()))
        try:
            a = u.first()
            session['name'], session['password'], session['admin'] = a
        except Exception as e:
            return 'Wrong username/password\n'+str(e)

    try:
        u = select(
            [users.c.name, users.c.password, users.c.admin]
        ).where(
            users.c.name == session['name']
        ).where(
            users.c.password == session['password'],
        ).execute()
        try:
            a = u.first()
            session['name'], session['password'], session['admin'] = a
        except Exception as e:
            return 'Wrong username/password\n'+str(e)

        return str(list(users.select().execute()))
    except:
        return render_template('login.html')


@app.route('/bdd')
def bdd():

    users.create(checkfirst=True)

    # Requête Delete
    db.execute('delete from users')

    # Insert de users
    users.insert().execute(name='Tiaosheng', email='pozuelomar@eisti.eu', password=hash('secret'), admin=True)

    return 'bdd reset'


app.run()
