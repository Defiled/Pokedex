import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_setup import Base, User, Pokemon, PokemonSprites, PokemonTypes, Types
from db_setup import UserPokemon

# Connect to Database and create DB session
engine = create_engine('postgresql://catalog:catalog@localhost/pokedex')
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
pokemon_wanted = 721
id = 1
while id <= pokemon_wanted:
    request_url = "https://pokeapi.co/api/v2/pokemon/" + str(id) + "/"
    r = requests.get(request_url)
    d = r.json()

    # Handle name exceptions for Alola region pokemon sprites
    # if d["name"] == "minior-red-meteor":
    #     d["name"] = "minior"
    # if d["name"] == "mimikyu-disguised":
    #     d["name"] = "mimikyu"
    if d["name"] == "basculin-red-striped":
        d["name"] = "basculin"

    # Store Pokemon data
    pokemon = Pokemon(name=d["name"], weight=d["weight"], height=d["height"])
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
    req_url = "https://pokeapi.co/api/v2/pokemon-species/" + str(p.id) + "/"
    r = requests.get(req_url)
    d = r.json()

    pokemon = session.query(Pokemon).filter_by(id=p.id).one()
    # Store generation & region_name on pokemon object
    gen = d["generation"]["name"]
    if gen == 'generation-i':
        pokemon.region_name = "kanto"
    if gen == 'generation-ii':
        pokemon.region_name = "johto"
    if gen == 'generation-iii':
        pokemon.region_name = "hoenn"
    if gen == 'generation-iv':
        pokemon.region_name = "sinnoh"
    if gen == 'generation-v':
        pokemon.region_name = "unova"
    if gen == 'generation-vi':
        pokemon.region_name = "kalos"
    if gen == 'sun-moon':
        pokemon.region_name = "alola"
    pokemon.generation = gen
    # Get English description
    for entry in d["flavor_text_entries"]:
        if entry["language"]["name"] == "en":
            pokemon.description = entry["flavor_text"]
    session.add(pokemon)
    session.commit()
    print str(progress) + " of " + str(len(my_pokemon)) + "..."
    print "Current region: " + p.region_name
    progress += 1

print "Done!"
print "Building sprite url's..."

# Build a sprite URL for each pokemon and store in DB
pokemon = session.query(Pokemon).all()
progress = 1
for p in pokemon:
    # if p.region_name in ["kanto", "johto", "hoenn"]:
    #     sprite_base_url = "https://img.pokemondb.net/sprites/ruby-sapphire/normal/"  # noqa
    # if p.region_name in ["sinnoh", "unova"]:
    #     sprite_base_url = "https://img.pokemondb.net/sprites/black-white/normal/"  # noqa
    # if p.region_name == "kalos":
    #     sprite_base_url = "https://img.pokemondb.net/sprites/x-y/normal/"
    # if p.region_name == "alola":
    #     sprite_base_url = "https://img.pokemondb.net/sprites/sun-moon/dex/normal/"  # noqa
    sprite_base_url = "https://img.pokemondb.net/sprites/x-y/normal/"
    sprite_url = sprite_base_url + p.name + ".png"
    sprite = PokemonSprites(name=p.name, sprite_url=sprite_url,
                            pokemon_id=p.id, pokemon=p)

    session.add(sprite)
    session.commit()
    print str(progress) + " of " + str(len(pokemon)) + "sprites added..."
    progress += 1

count = session.query(PokemonSprites).count()
print "Added %s pokemon sprites to PokemonSprites table" % count


# Strip pokemon names of hyphens
pokemon = session.query(Pokemon).all()
for p in pokemon:
    if p.name.find("-") != -1 and p.id not in [122, 250, 439, 474, 772, 782,
                                               783, 784, 785, 786, 787, 788]:
        print "fixing " + p.name
        split = p.name.split("-")
        p.name = split[0]
        session.add(p)
        session.commit()

# Create a user account with pokemon in party for testing
testUser = User(name="John Doe", email="johndoe@gmail.com",
                password="password",
                picture="{{ url_for('static', filename='amber-heard.jpg') }}")
session.add(testUser)
session.commit()

pokemon_array = [
    UserPokemon(pokemon_id=59, user_id=testUser.id, nickname="Woof",
                level="99", party_order=1),
    UserPokemon(pokemon_id=131, user_id=testUser.id, nickname="Blister",
                level="78", party_order=2),
    UserPokemon(pokemon_id=142, user_id=testUser.id, nickname="Stones",
                level="81", party_order=3),
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
