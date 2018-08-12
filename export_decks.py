import sys, os
import time
import dropbox

from dropbox.files import WriteMode
# Load Anki library
Sys.path.append(os.getcwd() + '/anki') 
from anki.storage import Collection
from anki.exporting import AnkiPackageExporter

from pymongo import MongoClient
from config import DB, MONGO_DB_URI, DROPBOX_AUTH_TOKEN

BASE_DECK = 'Gamegogakuen JP'
OUTPUT_FILE_NAME = 'Gamegogakuen_JP.apkg'
OUTPUT_PATH = '/Users/admin/Desktop/' + OUTPUT_FILE_NAME

# Define the path to the Anki SQLite collection
COLLECTION_PATH = '/Users/admin/Library/Application Support/Anki2/User 1/collection.anki2'

# Load the Collection
col = Collection(COLLECTION_PATH, log=False) # Entry point to the API

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

print('Export Deck: Success')

# Upload new deck to dropbox
dbx = dropbox.Dropbox(DROPBOX_AUTH_TOKEN)
file = open(OUTPUT_PATH, "rb")
dropbox_path = '/decks/' + OUTPUT_FILE_NAME

dbx.files_upload(
    file.read(),
    dropbox_path,
    mode=WriteMode.overwrite)

print('Upload to Dropbox: Success')

# Clean up exported deck
file.close()
os.remove(OUTPUT_PATH)

# Update LAST_MODIFIED timestamp in database
now = int(round(time.time() * 1000))
timestamps = db.timestamps

timestamps.update_one({}, {
    '$set': {
        'downloadUpdated': now
    }})

print('Update LAST_MODIFIED timestamp: Success')

client.close()
