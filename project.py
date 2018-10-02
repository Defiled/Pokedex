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
engine = create_engine('sqlite:///pokedex.db', pool_pre_ping=True, poolclass=
            StaticPool, connect_args={'check_same_thread': False})
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
        email = request.form['email']
        exists = session.query(User).filter_by(email=email).first()
        if exists:
            flash("A user with this email is already registered.")
            return redirect(url_for('login'))
        pass1 = request.form['password']
        pass2 = request.form['passwordConfirm']
        if pass1 != pass2:
            flash("Passwords do not match. Please try again.")
            return redirect(url_for('login'))
        name = request.form['username']
        user = User(name=name, email=email, password=pass1)
        session.add(user)
        session.commit()
        setSession(user_info=user)
        flash("You are logged in registered!")
        return redirect(url_for('index'))

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        state = ''.join(random.choice(string.ascii_uppercase + string.digits)
            for x in xrange(32))
        login_session['state'] = state
        return render_template('login.html', STATE=state)
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = session.query(User).filter_by(email=email, password=
            password).first()
        if user.id:
            setSession(user_info=user)
            flash("Logged in as %s" % login_session['username'])
            return redirect(url_for('showTrainer', user_id=user.id))

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

    # Check if user exists
    user = session.query(User).filter_by(email=data["email"]).first()
    if not user:
        print "making user"
        user = createUser(data)
        print "user made"
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
        url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (
            facebook_id,access_token)
        h = httplib2.Http()
        result = h.request(url, 'DELETE')[1]
    login_session.clear()
    flash("You have been logged out.")
    return redirect(url_for('login'))

#                           #
# <---- CRUD Methods -----> #
#                           #

# Display all pokemon (Home)
@app.route('/')
@app.route('/pokemon/')
def index():
    pokemon = session.query(Pokemon).order_by(Pokemon.id).all()
    types = session.query(Types).all()
    regions = session.query(Pokemon).group_by(Pokemon.region_name).all()
    user = False
    if 'username' in login_session:
        # Pass the user obj through here to be used in main.html throughout site
        user = login_session["username"]
    return render_template('pokemon.html', pokemon=pokemon, types=types,
        regions=regions, user=user)

# Filter pokemon by type
@app.route('/pokemon/type/<string:type>')
def pokemonByType(type):
    # TODO: Come up with a more eloquent solution to do this ya idiot...
    pokemon = session.query(Pokemon).all()
    pokemon_filtered = []
    type_id = session.query(Types.id).filter_by(name=type).one()
    pokemon_ids = session.query(PokemonTypes.pokemon_id).filter_by(type_id=type_id[0]).all()
    for p in pokemon[:]:
        for pi in pokemon_ids:
            if p.id == pi[0]:
                pokemon_filtered.append(p)
    types = session.query(Types).all()
    regions = session.query(Pokemon).group_by(Pokemon.region_name).all()
    return render_template('pokemon.html', pokemon=pokemon_filtered, types=types,
        regions=regions)

# Filter pokemon by region
@app.route('/pokemon/region/<string:region_name>')
def pokemonByRegion(region_name):
    # TODO: Shouldn't need to have to load types and regions and again...
    # perhaps separate pokemon.html and filters into separate templates and only
    # rerender pokemon.html each time
    pokemon = session.query(Pokemon).filter_by(region_name=region_name).all()
    types = session.query(Types).all()
    regions = session.query(Pokemon).group_by(Pokemon.region_name).all()
    return render_template('pokemon.html', pokemon=pokemon, types=types,
        regions=regions)

# Get details of a specific pokemon
@app.route('/pokemon/detail', methods=['POST'])
def pokemonDetail():
    # session.close()
    pokemon_id = request.data
    pokemon = findPokemon(pokemon_id)
    return render_template('pokemon_detail.html', pokemon=pokemon)

# Show trainer profile page (users)
@app.route('/trainer/<int:user_id>/')
def showTrainer(user_id):
    user = getUser(user_id)
    if not user:
        print user
        flash("There is no trainer with that ID...")
        return redirect(url_for('index'))
    if 'username' not in login_session:
        flash("You must login to view trainer profiles.")
        return redirect('/login')
    if user_id == login_session["user_id"]:
        flash("You may add, edit and delete pokemon in your party.")
        canEditDelete = True
    if user_id != login_session["user_id"]:
        flash("You may not make changes to another trainer's party.")
        canEditDelete = False
    party = getPartyOrdered(user_id)
    return render_template('trainer_detail.html', trainer=user, party=party,
        canEditDelete=canEditDelete, isEditing=False, user=login_session)

# Edit a pokemon in your party
@app.route('/trainer/<int:user_id>/edit/<int:user_pokemon_id>', methods=['GET','POST'])
def editPartyMember(user_id, user_pokemon_id):
    # Authorization pikachu simplify authorization process on all these functions
    if 'username' not in login_session:
        flash("You must be logged in to edit pokemon in a party.")
        return redirect('/login')
    if user_id != login_session["user_id"]:
        flash("You may not make changes to another trainer's party.")
        return redirect('/pokemon')
    if user_id == login_session["user_id"]:
        session.close()
        user_pokemon = findUserPokemon(user_pokemon_id)
        if request.method == 'POST':
            if request.form['nickname']:
                user_pokemon.nickname = request.form['nickname']
            if request.form['level']:
                user_pokemon.level = request.form['level']
            if request.form['party_order']:
                # Set party_order of party members with same party_order to None
                party = session.query(UserPokemon).filter_by(user_id=
                    user_id).all()
                for p in party:
                    if p.party_order == int(request.form['party_order']):
                        p.party_order = None
                        session.commit()
                user_pokemon.party_order = int(request.form['party_order'])
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
    pokemon = findPokemon(pokemon_id)
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

def getUser(id):
    return session.query(User).filter_by(id=id).first()

def getPartyOrdered(id):
    return session.query(UserPokemon).filter(UserPokemon.user_id==id).order_by(
        UserPokemon.party_order.isnot(None).desc(),
        UserPokemon.party_order.asc())

def findPokemon(id):
    return session.query(Pokemon).filter_by(id=id).one()

def findUserPokemon(id):
    return session.query(UserPokemon).filter_by(id=id).one()

# def filterPokemon(filters):
#     # pikachu, clean this up
#     if 'name_id' in filters:
#         for p in pokemon:
#             if p.name.find(name_id) != -1 or p.id == name_id:
#                 matches.append(p)
#     if 'region' in filters:
#         if len(matches) == 0:
#             for p in pokemon:
#                 if p.region == region:
#                     matches.append(p)
#         else:
#             for m in matches:
#                 if m.region == region:
#                     matches.append(m)
#     if 'type' in filters:
#         if len(matches) == 0:
#             for p in pokemon:
#                 if p.type.type.name == type:
#                     matches.append(p)
#         else:
#             for m in matches:
#                 if m.type.type.name == type:
#                     matches.append(m)
#     return matches

#                               #
# <---- Filter Functions -----> #
#                               #
# def filterByType(type): pikachu delete
#     pokemon = session.query(Pokemon).filter_by(Pokemon.type.type.name=type).all()


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
  app.secret_key = 'super_secret_key' # pikachu
  app.debug = True
  app.run(host = '0.0.0.0', port = 8000)
