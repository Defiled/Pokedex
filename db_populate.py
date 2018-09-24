import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_setup import Base, User, Pokemon, PokemonSprites, PokemonTypes, Types, UserPokemon

# Connect to Database and create DB session
engine = create_engine('sqlite:///pokedex.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Populate Types table
pokemon_types = 18
i = 1
while i <= pokemon_types:
    request_url = "https://pokeapi.co/api/v2/type/" + str(i)
    r = requests.get(request_url)
    d = r.json()

    type = Types(name=d["name"])
    session.add(type)
    session.commit()
    i += 1

print "Pokemon Types added!"
print "Fetching pokemon data from https://pokeapi.co..."


# Fetch Pokemon data and populate table
pokemon_wanted = 151 # There are only 151 pokemon in the Kanto region..
id = 1
while id <= pokemon_wanted:
    request_url = "https://pokeapi.co/api/v2/pokemon/" + str(id) + "/"
    r = requests.get(request_url)
    d = r.json()
    # Store Pokemon data
    pokemon = Pokemon(name=d["name"], poke_id=d["id"], weight=d["weight"],
        height=d["height"])
    session.add(pokemon)
    session.commit()
    # Store PokemonTypes data
    for t in d["types"]:
        type = session.query(Types).filter_by(name=t["type"]["name"]).one()
        if type:
            pokemon_type = PokemonTypes(pokemon_id=pokemon.id, type_id=type.id,
                pokemon=pokemon)
            session.add(pokemon_type)
            session.commit()
    # Let user know we've added the pokemon and increment id
    print "Added " + pokemon.name
    id += 1


print "Added %s pokemon!" % pokemon_wanted
print "Fetching and storing pokedex data..."


# Get Pokedex data and update Pokemon
my_pokemon = session.query(Pokemon).all()
progress = 1
for p in my_pokemon:
    request_url = "https://pokeapi.co/api/v2/pokemon-species/" + str(p.id) + "/"
    r = requests.get(request_url)
    d = r.json()

    pokemon = session.query(Pokemon).filter_by(id=p.id).one()
    pokemon.generation = d["generation"]["name"]
    for entry in d["flavor_text_entries"]:
        if entry["language"]["name"] == "en":
            pokemon.description = entry["flavor_text"]
    session.add(pokemon)
    session.commit()
    print str(progress) + " of " + str(len(my_pokemon)) + "..."
    progress += 1


print "Done!"
print "Building sprite url's..."


# Build a sprite URL for each pokemon and store in DB
pokemon = session.query(Pokemon).all()
sprite_base_url = "https://img.pokemondb.net/sprites/ruby-sapphire/normal/"
for p in pokemon:
    sprite_url = sprite_base_url + p.name + ".png"
    sprite = PokemonSprites(name=p.name, sprite_url=sprite_url, pokemon_id=p.id,
        pokemon=p)

    session.add(sprite)
    session.commit()


count = session.query(PokemonSprites).count()
print "Added %s pokemon sprites to PokemonSprites table" % count


# Create a user account with pokemon in party for testing
testUser = User(name="John Doe", email="johndoe@gmail.com",
             password="password", picture="http://www.pngmart.com/?p=10161")
             # use local .png or something pikachu
session.add(testUser)
session.commit()

pokemon_array = [
    UserPokemon(pokemon_id=59, user_id=testUser.id, nickname="Woof", level="99", party_order=1),
    UserPokemon(pokemon_id=131, user_id=testUser.id, nickname="Blister", level="78", party_order=2),
    UserPokemon(pokemon_id=142, user_id=testUser.id, nickname="Stones", level="81", party_order=3),
]
for pm in pokemon_array:
    session.add(pm)
    pokemon = session.query(Pokemon).filter_by(id=pm.pokemon_id).first()
    print pokemon.name
    print pm.user_id
    pm.user = testUser
    pm.pokemon = pokemon
session.commit()

print "Test user account created with %s pokemon." % len(testUser.pokemon)

print "The app is ready!"
