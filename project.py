#!/usr/bin/env python

#                    #
# <---- Setup -----> #
#                    #

from flask import Flask, render_template, request, redirect,jsonify, url_for
from flask import flash, make_response
from flask import session as login_session
import httplib2, json, requests, random, string

from sqlalchemy import create_engine, desc, exists
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from db_setup import Base, User, Pokemon, UserPokemon, Types, PokemonTypes
from db_setup import PokemonSprites

app = Flask(__name__)

# Connect to Database and create DB session
engine = create_engine('sqlite:///pokedex.db', pool_pre_ping=True, connect_args={'check_same_thread': False}, poolclass=StaticPool) #, poolclass=SingletonThreadPool
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

#                             #
# <---- Authentication -----> #
#                             #

#  Signup
@app.route('/signup', methods=['GET', 'POST'])
def signUp():
    if request.method == 'POST':
        if request.form['email']:
            email = request.form['email']
            exists = session.query(User).filter_by(email=email).first()
            if exists:
                flash("A user with this email is already registered.")
                return redirect(url_for('login'))
            if request.form['password'] and request.form['password_confirm']:
                pass1 = request.form['password']
                pass2 = request.form['password_confirm']
                if pass1 != pass2:
                    flash("Passwords do not match!")
                    return redirect(url_for('login'))
            if request.form['username']:
                name = request.form['username']
                user = User(name=name, email=email, password=pass1)
                session.add(user)
                session.commit()
                setSession(user_info=user)
                flash("Account succesfully created!")
                return redirect(url_for('home'))
            else:
                return flash("No username entered")

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        state = ''.join(random.choice(string.ascii_uppercase + string.digits)
            for x in xrange(32))
        login_session['state'] = state
    if request.method == 'POST':
        if request.form['email'] and request.form['password']:
            email = request.form['email']
            password = request.form['password']
            user = session.query(User).filter_by(email=email, password=password).first()
            if user.id:
                setSession(user_info=user)
                flash("Logged in as %s" % login_session['username'])
                return redirect(url_for('showTrainer', user_id=login_session['user_id']))
        else:
            return flash("Email or password not entered.")
    return render_template('login.html', STATE=state)

# Facebook login
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    print "Made it here and state is now" + login_session['state']
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.8/me?access_token=%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    print "url sent for API access:%s"% url
    print "API JSON result: %s" % result
    data = json.loads(result)

    test = session.query(User).filter_by(email="waldorabie@gmail.com").first()
    session.delete(test)

    # Check if user exists
    user = session.query(User).filter_by(email=data["email"]).first()
    if not user:
        user = createUser(data)
        # Get user picture
        url = 'https://graph.facebook.com/v2.8/me/picture?access_token=%s&redirect=0&height=200&width=200' % token
        h = httplib2.Http()
        result = h.request(url, 'GET')[1]
        d = json.loads(result)

        user.picture = d["data"]["url"]
        session.commit()
    setSession(user_info=user)

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token
    login_session['facebook_id'] = data["id"]
    login_session['provider'] = 'facebook'

    flash("Welcome %s" % login_session['username'])
    return redirect(url_for('showTrainer', user_id=login_session['user_id']))

# Logout
@app.route('/logout')
def logout():
    if 'access_token' in login_session:
        access_token = login_session['access_token']
        facebook_id = login_session['facebook_id']
        url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
        h = httplib2.Http()
        result = h.request(url, 'DELETE')[1]
    login_session.clear()
    flash("you have been logged out")
    return redirect(url_for('index'))

#                           #
# <---- CRUD Methods -----> #
#                           #

# Home page
@app.route('/')
@app.route('/pokemon/')
def index():
  session.close()
  pokemon = session.query(Pokemon).order_by(Pokemon.poke_id)
  if 'username' not in login_session:
      user = False
  else:
      user = login_session["username"]
  return render_template('pokemon.html', pokemon=pokemon, user=user)
  # TODO add functionality that allows showPokemon to filter based on region id

# Show details of a specific pokemon
@app.route('/pokemon/<int:pokemon_id>')
def pokemonDetail(pokemon_id):
  session.close()
  pokemon = findPokemon(pokemon_id)
  return render_template('pokemon_detail.html', pokemon=pokemon, user=
    login_session)

# Show pokemon trainer profile page (users)
@app.route('/trainer/<int:user_id>/')
def showTrainer(user_id):
    user = session.query(User).filter_by(id=user_id).first() # pikachu
    if not user:
        print user
        flash("There is no trainer with that ID...")
        return redirect(url_for('home'))
    if 'username' not in login_session:
        flash("You must login to view trainer profiles.")
        return redirect('/login')
    if user_id == login_session["user_id"]:
        flash("This is your trainer profile. You may make changes to your party.")
        canEditDelete = True
    if user_id != login_session["user_id"]:
        flash("You may not make changes to another trainer's party.")
        canEditDelete = False
    party = getPartyOrdered(user_id)
    return render_template('trainer_detail.html', trainer=user, party=party,
        canEditDelete=canEditDelete, isEditing=False, user=login_session)
    # TODO abstract user and party DB calls to seperate functions and update other functions

# Edit a pokemon in your party
@app.route('/trainer/<int:user_id>/edit/<int:user_pokemon_id>', methods=['GET','POST'])
def editPartyMember(user_id, user_pokemon_id):
    # Authorization pikachu simplify authorization process on all these functions
    if 'username' not in login_session: # does this need to be so verbose? better way to do it..
        flash("You must be logged in to edit pokemon in a party.")
        return redirect('/login')
    if user_id != login_session["user_id"]:
        flash("You may not make changes to another trainer's party.")
        return redirect('/pokemon')
    if user_id == login_session["user_id"]:
        session.close()
        user_pokemon = session.query(UserPokemon).filter_by(id=user_pokemon_id).one() #findUserPokemon(user_pokemon_id pikachu
        if request.method == 'POST':
            if request.form['nickname']:
                user_pokemon.nickname = request.form['nickname']
            if request.form['level']:
                user_pokemon.level = request.form['level']
            if request.form['party_order']:
                party = session.query(UserPokemon).filter_by(user_id=
                    user_id).all()
                # If duplicate party_order found, set to None
                # pikachu figure out why the fuck this isnt matchin
                print type(request.form['party_order']) + ", " + request.form['party_order']
                print type(user_pokemon.party_order) + ", " + user_pokemon.party_order
                for p in party:
                    print type(p.party_order) + ", " + p.party_order
                    # not finding match, and then setting matches order to None
                    if p.party_order == request.form['party_order']:
                        print "match found"
                        p.party_order = user_pokemon.party_order
                        session.commit()
                user_pokemon.party_order = request.form['party_order']
            session.add(user_pokemon)
            flash("Successfully updated!")
            session.commit()
            return redirect(url_for('showTrainer', user_id=user_id))
        if request.method == 'GET':
            flash("Editing your party.")
            user = session.query(User).filter_by(id=user_id).first()
            party = getPartyOrdered(user_id)
            for p in party:
                if user_pokemon_id == p.id:
                    p.isEditing = True
            return render_template('trainer_detail.html', trainer=user,
                party=party, canEditDelete=True, user=login_session)

# Add a pokemon to party (max of 6)
@app.route('/pokemon/<int:pokemon_id>/add')
def addToParty(pokemon_id):
    if 'username' not in login_session:
        flash("You must login to add Pokemon to your party!")
        return redirect('/login')
    user_id = login_session["user_id"]
    party = session.query(UserPokemon).filter(UserPokemon.user_id==user_id)
    remaining_slots = (party.count() - 6) * -1
    if remaining_slots < 1:
        flash("Your party is full. Release a pokemon to add another.")
        return redirect(url_for('showTrainer', user_id=user_id))
    pokemon = session.query(Pokemon).filter_by(id=pokemon_id).one() # pikachu findPokemon(pokemon_id)
    newPokemon = UserPokemon(pokemon_id=pokemon_id, user_id=user_id,
        pokemon=pokemon)
    session.add(newPokemon)
    session.commit()
    flash("%s has been added to your party! %s slots remaining."
        % (pokemon.name.capitalize(), remaining_slots - 1))
    return redirect(url_for('index'))

# Delete a pokemon from your party
@app.route('/trainer/<int:user_id>/delete/<int:user_pokemon_id>', methods=['POST'])
def releasePokemon(user_id, user_pokemon_id):
    if 'username' not in login_session:
        flash("You must be logged in to delete pokemon from a party.")
        return redirect('/login')
    if user_id != login_session["user_id"]:
        flash("You may not make changes to another trainer's party.")
        return redirect('/pokemon')
    if user_id == login_session["user_id"]:
        user_pokemon = findUserPokemon(id=user_pokemon_id)
        session.delete(user_pokemon)
        session.commit()
        return redirect(url_for('showTrainer', user_id=user_id))

#                               #
# <---- Helper Functions -----> #
#                               #
def createUser(data):
    newUser = User(name=data['name'], email=data['email'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=data['email']).one()
    return user

def setSession(user_info):
    login_session['user_id'] = user_info.id
    login_session['username'] = user_info.name
    login_session['email'] = user_info.email
    login_session['picture'] = user_info.picture
    return login_session

def getUserInfo(id):
    return session.query(User).filter_by(id=id).one()

def getPartyOrdered(id):
    return session.query(UserPokemon).filter(UserPokemon.user_id==id).order_by(
        UserPokemon.party_order.isnot(None).desc(),
        UserPokemon.party_order.asc())

def findPokemon(id):
    return session.query(Pokemon).filter_by(id=id).one()

def findUserPokemon(id):
    return session.query(UserPokemon).filter_by(id=id).one()

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
