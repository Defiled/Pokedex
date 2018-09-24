from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    password = Column(String(250))
    email = Column(String(250), nullable=False)
    picture = Column(String(250))

    pokemon = relationship("UserPokemon")
    # not gonna store pokemon on here

class Pokemon(Base):
    __tablename__ = 'pokemon'
    id = Column(Integer, primary_key=True)
    poke_id = Column(Integer)
    name = Column(String(250))
    description = Column(Text)
    weight = Column(Integer)
    height = Column(Integer)
    generation = Column(String(250))

    pokemon_sprite = relationship("PokemonSprites", uselist=False,
        back_populates="pokemon")
    user_pokemon = relationship("UserPokemon")
    # user_pokemon = relationship("UserPokemon", uselist=False, back_populates="pokemon")
    pokemon_type = relationship("PokemonTypes", back_populates="pokemon")

    @property
    def serialize(self):
       return {
           'id'      : self.id,
           'name'    : self.name,
           'weight'  : self.weight,
           'height'  : self.height
       }

class UserPokemon(Base):
    __tablename__ = 'user_pokemon'
    id = Column(Integer, primary_key=True)
    pokemon_id = Column(Integer, ForeignKey('pokemon.id'))
    user_id = Column(Integer, ForeignKey('user.id'))
    nickname = Column(String(250))
    level = Column(String(250))
    party_order = Column(Integer)

    pokemon = relationship("Pokemon")
    user = relationship("User")

class Types(Base):
    __tablename__ = 'types'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)

    pokemon_type = relationship("PokemonTypes", back_populates="type")

class PokemonTypes(Base):
    __tablename__ = 'pokemon_types'
    id = Column(Integer, primary_key=True)
    pokemon_id = Column(Integer, ForeignKey('pokemon.id'))
    type_id = Column(Integer, ForeignKey('types.id'))

    type = relationship("Types", back_populates="pokemon_type")
    pokemon = relationship('Pokemon', back_populates='pokemon_type')

class PokemonSprites(Base):
    __tablename__ = 'pokemon_sprites'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    sprite_url = Column(String(250), nullable=False)
    pokemon_id = Column(Integer, ForeignKey('pokemon.id'))

    pokemon = relationship("Pokemon", back_populates="pokemon_sprite")

    @property
    def serialize(self):
       return {
           'id'   : self.id,
           'name'  : self.name,
           'url'   : self.sprite_url,
           # 'pokemon'     : self.pokemon   .. pikachu, test this
       }

engine = create_engine('sqlite:///pokedex.db')
Base.metadata.create_all(engine)
