import sys, os
import time

# Load Anki library
sys.path.append('/Users/admin/Dev/JavaScript/GameGogakuen/GG-AnkiScripts/anki')
from anki.storage import Collection
from anki.exporting import AnkiPackageExporter
from anki.importing import AnkiPackageImporter

from pymongo import MongoClient
from config import DB, MONGO_DB_URI, DROPBOX_AUTH_TOKEN

IMPORT_PATH = '/Users/admin/Dropbox/KevNI/Japanese Decks/Public Decks/'
BASE_DECK = 'Gamegogakuen JP'
OUTPUT_FILE_NAME = 'Gamegogakuen_JP.apkg'
OUTPUT_PATH = '/Users/admin/Desktop/' + OUTPUT_FILE_NAME

# Define the path to the Anki SQLite collection
COLLECTION_PATH = '/Users/admin/Library/Application Support/Anki2/User 1/collection.anki2'

# Load the Collection
col = Collection(COLLECTION_PATH, log=False) # Entry point to the API

# Clear collection
for did in col.decks.allIds():
    col.decks.rem(did, True)
col.save()

# Import game decks
for filename in os.listdir(IMPORT_PATH):
    apkg = IMPORT_PATH + filename
    AnkiPackageImporter(col, apkg).run()
col.save()

# Create a base dynamic deck
base_deck_id = col.decks.newDyn(BASE_DECK)

# Fetch db collections
client = MongoClient(MONGO_DB_URI)
db = client[DB]
deck_titles_collection = db.deckTitles
old_cards = db.oldCards

# Fetch deck titles
deck_titles = [
    doc['fullTitle']
    for doc
    in deck_titles_collection.find() ]

# Make new subdeck for every deck title
for title in deck_titles:

    tweeted_card_ids = [
        doc['cardId']
        for doc
        in old_cards.find({ 'game': title }) ]

    if len(tweeted_card_ids) > 0:
        tweeted_cards_query = ' or '.join(tweeted_card_ids)

        subdeck_name = "%s::%s" % (BASE_DECK, title)
        subdeck_id = col.decks.newDyn(subdeck_name)
        subdeck = col.decks.get(subdeck_id)

        # Fill the deck with appropriate notes
        subdeck['terms'] = [[
            tweeted_cards_query,
            100,
            0 ]]

        col.decks.save(subdeck)
        col.sched.rebuildDyn()

col.save()

# Export the filtered deck
exporter = AnkiPackageExporter(col)
exporter.did = base_deck_id
exporter.exportInto(OUTPUT_PATH)

# Clean up collection
for did in col.decks.allIds():
    col.decks.rem(did, True)
col.save()

print('Export Deck: Success')

# Clean up
client.close()
