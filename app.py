# Installation - pip3 install Flask

from flask import Flask, session, redirect, url_for, escape, request
from flask import render_template

from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, Float, Boolean, select

app = Flask(__name__)

# Base de données (e.g. SQLite)
# SQL Alchemy - http://www.sqlalchemy.org/

db = create_engine('sqlite:///sqlite.bdd', echo=True, convert_unicode=True)
metadata = MetaData(bind=db)

# Création des tables
users = Table('users', metadata,
              Column('name', String(30), primary_key=True),
              Column('email', String(50)),
              Column('password', String, default=''),
              Column('admin', Boolean),
              Column('elo', Float, default=1200),
              Column('nbGame', Integer, default=0),
              )


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

    print(elo1, elo2)


@app.route('/')
def default():
    players = select([users.c.name, users.c.elo]).order_by(users.c.elo.desc()).execute()

    players = tuple(map(dict, players))
    for i in range(len(players)):
        if i != 0 and players[i]['elo'] == players[i-1]['elo']:
            players[i]['rank'] = players[i-1]['rank']
        else:
            players[i]['rank'] = i+1
    return render_template('dashboard.html', players=players)


@app.route('/hello')
def hello():
    return 'Hello, World'


@app.route('/match', methods=['POST'])
def match():
    if request.method == 'POST':
        print('posted')
        player1 = select([users.c.name, users.c.elo, users.c.nbGame]).where(users.c.name == 'Tiaosheng').execute().first()
        player2 = select([users.c.name, users.c.elo, users.c.nbGame]).where(users.c.name == 'test0').execute().first()
        do_match(player1, player2, 2, 0)
        return 'done'
    else:
        return 'not done'


@app.route('/bdd')
def bdd():

    users.create(checkfirst=True)

    # Requête Delete
    db.execute('delete from users')

    # Insert de users
    users.insert().execute(name='Tiaosheng', email='pozuelomar@eisti.eu', password='secret', elo='1200')

    for i in range(10):
        create_user(name='test%s' % i, email='test%s' % i)

    """
    # Update

    q = users.update().values(name='New Name'). \
        where(users.c.age <= 40). \
        where(users.c.name.contains('ar'))
    db.execute(q)
    """
    """
    # Select
    x = users.select(users.c.name == 'John').execute().first()

    y = db.execute('select * from users where name = :1', ['Carl']).first()

    rs = users.select().execute()
    """
    return 'ok'


app.run()
