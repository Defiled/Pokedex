#!/usr/bin/env python

#                    #
# <---- Setup -----> #
#                    #

from flask import Flask, render_template, request, redirect,jsonify, url_for
from flask import flash, make_response
from flask import session as login_session
import httplib2, json, requests, random, string
from oauth2client.client import flow_from_clientsecrets #pikachu, do i need?
from oauth2client.client import FlowExchangeError # pikachu, do i need?

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import SingletonThreadPool
from db_setup import Base, User, Pokemon, UserPokemon, Types, PokemonTypes
from db_setup import PokemonSprites

app = Flask(__name__)

# Connect to Database and create DB session
engine = create_engine('sqlite:///pokedex.db', poolclass=SingletonThreadPool)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

#                                     #
# <---- Login & Authentication -----> #
#                                     #

# For google sign in # pikachu, scratch this and just use facebook.
# CLIENT_ID = json.loads(
#     open('client_secrets.json', 'r').read())['web']['client_id']
# APPLICATION_NAME = "Restaurant Menu App"

# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
        for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

# Facebook login pikachu
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    print "Get Facebook login setup here!"

@app.route('/fbdisconnect')
def fbdisconnect():
    print "Get Facebook logout setup here!"

#                           #
# <---- CRUD Methods -----> #
#                           #

# Show all pokemon
@app.route('/')
@app.route('/pokemon/')
def showPokemon():
  pokemon = session.query(Pokemon).order_by(Pokemon.poke_id)
  return render_template('pokemon.html', pokemon=pokemon)
  # TODO create pokemon.html

# View info about a specific pokemon
@app.route('/pokemon/<int:pokemon_id>')
def viewPokemon(pokemon_id):
  pokemon = findPokemon(pokemon_id)
  return render_template('view_pokemon.html', pokemon=pokemon)
  # TODO create view_pokemon.html ...Height (m), Weight (kgs)
    # Get types
    # pokemonAndTypes = session.query(PokemonTypes).all()

# Add a pokemon to party (max of 6)
@app.route('/pokemon/<int:pokemon_id>/add/', methods=['POST'])
def addToParty(pokemon_id):
    if 'username' not in login_session:
        return redirect('/login')
    pokemon = findPokemon(pokemon_id)
    # Make sure the user doesn't already have 6 members in their party
    partyCount = session.query(UserPokemon).all()
    if partyCount.len() < 6: # make sure this works
        newPartyMember = UserPokemon(pokemon_id=pokemon_id, user_id=
            login_session['user_id'])
        session.add(newPartyMember)
        session.commit()
        return redirect()
    else:
        flash("Your party is full. You must release a Pokemon to add %s"
            % pokemon.name)
        return redirect(url_for('showParty', user_id=login_session['user_id']))

# Show the Pokemon in your party
@app.route('/party/<int:user_id>/', methods = ['GET'])
def showParty(user_id):
    if 'username' not in login_session:
        return redirect('/login')
    party = session.query(UserPokemon).filter_by(user_id=user_id).all()
    return render_template('show_party.html', party=party)
    # TODO create show_party template (must have edit and delete buttons that route)

# Edit a pokemon in your party
@app.route('/party/<int:user_id>/edit/<int:user_pokemon_id>/', methods=['GET','POST'])
def editPartyMember(user_id, user_pokemon_id):
    if 'username' not in login_session:
        return redirect('/login')
    partyMem = findUserPokemon(user_pokemon_id)
    if request.method == 'POST':
        if request.form['nickname']:
            partyMem.nickname = request.form['nickname']
        if request.form['level']:
            partyMem.level = request.form['level']
        if request.form['party_order']:
            # pikachu, some validation will be needed here...
            partyMem.party_order = request.form['party_order']
        session.add(partyMem)
        session.commit()
        flash('Your %s was successfully updated!') % partyMem.name
        return redirect(url_for('showParty', user_id=partyMem.user_id))
    else:
        return render_template('edit_party_member.html', partyMem=partyMem)
        # TODO add edit_party_member.html and make sure this works??
        # TODO should have nickname, party_order, level fields...

# Delete a pokemon from your party
@app.route('/party/<int:user_id>/delete/<int:user_pokemon_id>/', methods = ['GET'])
def deletePartyMember(restaurant_id,menu_id):
    if 'username' not in login_session:
        return redirect('/login')
    partyMem = findUserPokemon(user_pokemon_id)
    # TODO add ALERT "are you sure you want to delete %s from your party?" % partyMem.name
    # TODO might need to handle a post here to continue after confirming
    session.delete(partyMem)
    session.commit()
    flash('Successfully removed.')
    return redirect(url_for('showParty', user_id=partyMem.user_id)) # might be delete? pikachu

#                               #
# <---- Helper Functions -----> #
#                               #

def createUser(login_session):
    newUser = User(name=login_session['name'], email=login_session['email'],
        picture=login_session['email'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

def getUserId(user_email):
    user = session.query(User).filter_by(email=user_email).one()
    return user.id

def findPokemon(pokemon_id):
    return session.query(Pokemon).filter_by(id=pokemon_id).one()
    # TODO test if this works...

def findUserPokemon(user_pokemon_id):
    return session.query(UserPokemon).filter_by(id=user_pokemon_id).one()
    # TODO test if this works...

#                       #
# <---- JSON API -----> #
#                       #

#JSON APIs to view Restaurant Information
# @app.route('/restaurant/<int:restaurant_id>/menu/JSON')
# def restaurantMenuJSON(restaurant_id):
#     restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
#     items = session.query(MenuItem).filter_by(restaurant_id = restaurant_id).all()
#     return jsonify(MenuItems=[i.serialize for i in items])
#
#
# @app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON')
# def menuItemJSON(restaurant_id, menu_id):
#     Menu_Item = session.query(MenuItem).filter_by(id = menu_id).one()
#     return jsonify(Menu_Item = Menu_Item.serialize)
#
# @app.route('/restaurant/JSON')
# def restaurantsJSON():
#     restaurants = session.query(Restaurant).all()
#     return jsonify(restaurants= [r.serialize for r in restaurants])

#                       #
# <----- Run App -----> #
#                       #

if __name__ == '__main__':
  app.secret_key = 'super_secret_key' # pikachu, wtf is this for
  app.debug = True
  app.run(host = '0.0.0.0', port = 8000)
