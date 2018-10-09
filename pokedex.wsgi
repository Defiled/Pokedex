import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, "/var/www/Pokedex/")
sys.path.insert(1, "/var/www/")

from Pokedex import app as application
application.secret_key = 'pikachu'
