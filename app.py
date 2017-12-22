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
              Column('email', String(50), default=''),
              Column('password', String, default=''),
              Column('admin', Boolean, default=False),
              Column('elo', Float, default=1200),
              Column('nbGame', Integer, default=0),
              )


def hash(password):
    return hashlib.sha512(password.encode('utf-8') + app.config['SALT'].encode('utf-8')).hexdigest()


def create_user(**kwargs):
    return users.insert().execute(**kwargs)


def delete_user(name):
    return users.delete().where(users.c.name == name).execute()


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
        if request.form['type'] == 'player':
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


def admin_page():
    players = select([users]).order_by(users.c.elo.desc()).execute()
    players = tuple(map(dict, players))
    return render_template('admin.html', players=players, attr=sorted(players[0].keys()))


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        print('post')
        if request.form['type'] == 'login':
            u = select(
                [users.c.name, users.c.password, users.c.admin]
            ).where(
                users.c.name == request.form['name']
            ).where(
                users.c.password == hash(request.form['password']),
            ).execute()

        if request.form['type'] == 'modify':
            try:
                u = select(
                    [users.c.name, users.c.password, users.c.admin]
                ).execute()
                a = u.first()
                session['name'], session['password'], session['admin'] = a
            except Exception as e:
                return render_template('login.html', error=e)
            else:
                modif = {
                    'name': request.form['name'],
                    'email': request.form['email'],
                    'password': request.form['password'],
                    'elo': float(request.form['elo']),
                    'nbGame': int(request.form['nbGame']),
                    'admin': request.form['admin'] == 'True',
                }
                users.update().values(
                    **modif
                ).where(users.c.name == request.form['name']).execute()
        if request.form['type'] == 'create':
            new = {}
            for k, v in request.form.items():
                if v:
                    new[k] = v
            create_user(**new)
        if request.form['type'] == 'delete':
            print(request.form['name'])
            delete_user(request.form['name'])

    try:
        u = select(
            [users.c.name, users.c.password, users.c.admin]
        ).where(
            users.c.name == session['name']
        ).where(
            users.c.password == session['password'],
        ).execute()
    except Exception as e:
        return render_template('login.html', error=e)
    else:
        try:
            session['name'], session['password'], session['admin'] = u.first()
            assert session['admin'] is True, 'User is not admin'
        except Exception as e:
            return render_template('login.html', error=e)
        else:
            return admin_page()


@app.route('/bdd')
def bdd():

    users.create(checkfirst=True)

    # Requête Delete
    db.execute('delete from users')

    # Insert de users
    users.insert().execute(
        name=app.config['ADMIN'],
        email=app.config['ADMIN_EMAIL'],
        password=hash(app.config['ADMIN_PASSWORD']),
        admin=True,
    )

    return 'bdd reset'


app.run()
