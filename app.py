from flask import Flask, render_template, request, redirect, url_for, flash, g
import sqlite3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import csv
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'your secret key'

ALLY_CODE = 668135442

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()

def get_star_counts():
    conn = get_db_connection()
    character_counts = {i: 0 for i in range(1, 8)}
    ship_counts = {i: 0 for i in range(1, 8)}

    # Count characters by star level
    character_rows = conn.execute('SELECT stars, COUNT(*) as count FROM characters GROUP BY stars').fetchall()
    for row in character_rows:
        character_counts[row['stars']] = row['count']

    # Count ships by star level
    ship_rows = conn.execute('SELECT stars, COUNT(*) as count FROM ships GROUP BY stars').fetchall()
    for row in ship_rows:
        ship_counts[row['stars']] = row['count']

    conn.close()
    return character_counts, ship_counts

def get_characters():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM characters').fetchall()
    return [{
        'characterID': row['characterID'],
        'characterName': row['characterName'],
        'characterImage': row['characterImage'],
        'stars': row['stars'],
        'level': row['level'],
        'gear': row['gear'],
        'relic': row['relic'],
        'tags': row['tags']
    } for row in rows]
    conn.close()

def get_ships():
    conn = get_db_connection()
    query = """
        SELECT ships.*, 
               GROUP_CONCAT(characters.characterName) AS pilotNames 
        FROM ships 
        LEFT JOIN characters ON ',' || ships.pilotID || ',' LIKE '%,' || characters.characterID || ',%' 
        GROUP BY ships.shipID
    """
    rows = conn.execute(query).fetchall()
    conn.close()
    return [{
        'shipID': row['shipID'],
        'shipName': row['shipName'],
        'shipImage': row['shipImage'],
        'stars': row['stars'],
        'level': row['level'],
        'tags': row['tags'],
        'pilotNames': row['pilotNames'] if row['pilotNames'] else "No Pilots"
    } for row in rows]

soup = ""

def get_level_counts():
    conn = get_db_connection()
    
    # Define level ranges
    level_ranges = {
        '85': 'level = 85',
        '80-84': 'level BETWEEN 80 AND 84',
        '70-79': 'level BETWEEN 70 AND 79',
        '60-69': 'level BETWEEN 60 AND 69',
        '1-59': 'level BETWEEN 1 AND 59'
    }

    character_counts = {key: 0 for key in level_ranges.keys()}
    ship_counts = {key: 0 for key in level_ranges.keys()}

    # Count characters by level range
    for key, condition in level_ranges.items():
        row = conn.execute(f'SELECT COUNT(*) as count FROM characters WHERE {condition}').fetchone()
        character_counts[key] = row['count']

    # Count ships by level range
    for key, condition in level_ranges.items():
        row = conn.execute(f'SELECT COUNT(*) as count FROM ships WHERE {condition}').fetchone()
        ship_counts[key] = row['count']

    conn.close()
    return character_counts, ship_counts

def get_relic_counts():
    conn = get_db_connection()
    
    # Define relic level groups
    relic_ranges = {
        '9': 'relic = 9',
        '8': 'relic = 8',
        '6-7': 'relic BETWEEN 6 AND 7',
        '4-5': 'relic BETWEEN 4 AND 5',
        '1-3': 'relic BETWEEN 1 AND 3'
    }

    relic_counts = {key: 0 for key in relic_ranges.keys()}

    # Count characters by relic level range
    for key, condition in relic_ranges.items():
        row = conn.execute(f'SELECT COUNT(*) as count FROM characters WHERE {condition}').fetchone()
        relic_counts[key] = row['count']

    conn.close()
    return relic_counts

def get_gear_counts():
    conn = get_db_connection()
    
    # Define gear level groups
    gear_ranges = {
        '13': 'gear = 13',
        '12': 'gear = 12',
        '11': 'gear = 11',
        '9-10': 'gear BETWEEN 9 AND 10',
        '7-8': 'gear BETWEEN 7 AND 8',
        '1-6': 'gear BETWEEN 1 AND 6'
    }

    gear_counts = {key: 0 for key in gear_ranges.keys()}

    # Count characters by gear level range
    for key, condition in gear_ranges.items():
        row = conn.execute(f'SELECT COUNT(*) as count FROM characters WHERE {condition}').fetchone()
        gear_counts[key] = row['count']

    conn.close()
    return gear_counts

@app.route('/')
def index():
    character_counts, ship_counts = get_star_counts()
    character_levels, ship_levels = get_level_counts()
    relic_counts = get_relic_counts()
    gear_counts = get_gear_counts()

    return render_template('index.html', 
                           character_counts=character_counts, 
                           ship_counts=ship_counts, 
                           character_levels=character_levels, 
                           ship_levels=ship_levels, 
                           relic_counts=relic_counts,
                           gear_counts=gear_counts)

@app.route('/characters', methods=['GET'])
def characters():
    return render_template('characters.html', characters=get_characters())

@app.route('/ships', methods=['GET'])
def ships():
    return render_template('ships.html', ships=get_ships())

@app.route('/add_character', methods=['GET', 'POST'])
def add_character():
    if request.method == 'POST':
        conn = get_db_connection()
        conn.execute('INSERT INTO characters (characterName, characterImage, stars, level, gear, relic, tags) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (request.form['characterName'], request.form['characterImage'], request.form['stars'], request.form['level'], 
                      request.form['gear'], request.form['relic'], request.form['tags']))
        conn.commit()
        conn.close()
        return redirect(url_for('characters'))
    return render_template('create_character.html')

@app.route('/add_ship', methods=['GET', 'POST'])
def add_ship():
    if request.method == 'POST':
        conn = get_db_connection()
        try:
            shipName = request.form['shipName']
            shipImage = request.form['shipImage']
            stars = request.form['stars']
            level = request.form['level']
            tags = request.form['tags']
            pilotNames = request.form.get('pilotNames', '')  # Get pilot names from the form
            pilotIDs = []
            for name in pilotNames.split(','):
                name = name.strip()  # Remove leading/trailing spaces
                if name:  # Only process non-empty names
                    pilot = conn.execute('SELECT characterID FROM characters WHERE characterName = ?', (name,)).fetchone()
                else:
                    flash(f"Pilot '{name}' not found!", 'error') # Notify user if pilot is not found
                if pilot:
                    pilotIDs.append(str(pilot['characterID']))  # Add the corresponding characterID to the list

            if pilotIDs:
                pilotID = ','.join(pilotIDs)  # Join IDs as a comma-separated string
            else:
                pilotID = None  # No pilots, set it to None or you can leave the field empty depending on your design
        
            conn.execute('INSERT INTO ships (shipName, shipImage, stars, level, tags, pilotID) VALUES (?, ?, ?, ?, ?, ?)',
                     (shipName, shipImage, stars, level, tags, pilotID))
            conn.commit()
            flash('Ship added successfully!', 'success') # Notify user of success
        except Exception as e: # Catch any potential database errors
            conn.rollback() # Rollback in case of error
            flash(f"Error adding ship: {str(e)}", 'error') # Show error message to user
        finally:
            conn.close()
        return redirect(url_for('ships'))
    
    return render_template('create_ship.html')

@app.route('/edit_character/<int:characterID>', methods=['GET', 'POST'])
def edit_character(characterID):
    conn = get_db_connection()
    character = conn.execute('SELECT * FROM characters WHERE characterID = ?', (characterID,)).fetchone()
    if request.method == 'POST':
        characterName = request.form['characterName']
        characterImage = request.form['characterImage']
        stars = request.form['stars']
        level = request.form['level']
        gear = request.form['gear']
        relic = request.form['relic']
        tags = request.form['tags']
        
        conn.execute('UPDATE characters SET characterName = ?, characterImage = ?, stars = ?, level = ?, gear = ?, relic = ?, tags = ? WHERE characterID = ?',
                     (characterName, characterImage, stars, level, gear, relic, tags, characterID))
        conn.commit()
        conn.close()
        flash('Character updated successfully!', 'success')
        return redirect(url_for('characters'))
    
    conn.close()
    return render_template('edit_character.html', character=character)

@app.route('/edit_ship/<int:shipID>', methods=['GET', 'POST'])
def edit_ship(shipID):
    conn = get_db_connection()
    ship = conn.execute('SELECT * FROM ships WHERE shipID = ?', (shipID,)).fetchone()
    if request.method == 'POST':
        shipName = request.form['shipName']
        shipImage = request.form['shipImage']
        stars = request.form['stars']
        level = request.form['level']
        tags = request.form['tags']
        pilotID = request.form['pilotID']
        
        conn.execute('UPDATE ships SET shipName = ?, shipImage = ?, stars = ?, level = ?, tags = ?, pilotID = ? WHERE shipID = ?',
                     (shipName, shipImage, stars, level, tags, pilotID, shipID))
        conn.commit()
        conn.close()
        flash('Ship updated successfully!', 'success')
        return redirect(url_for('ships'))
    
    conn.close()
    return render_template('edit_ship.html', ship=ship)

@app.route('/delete_character/<int:characterID>', methods=['POST'])
def delete_character(characterID):
    conn = get_db_connection()
    conn.execute('DELETE FROM characters WHERE characterID = ?', (characterID,))
    conn.commit()
    conn.close()
    flash('Character deleted successfully!', 'success')
    return redirect(url_for('characters'))

@app.route('/delete_ship/<int:shipID>', methods=['POST'])
def delete_ship(shipID):
    conn = get_db_connection()
    conn.execute('DELETE FROM ships WHERE shipID = ?', (shipID,))
    conn.commit()
    conn.close()
    flash('Ship deleted successfully!', 'success')
    return redirect(url_for('ships'))

@app.route('/update_characters', methods=['POST'])
def update_characters():
    url_to_scrape = 'https://swgoh.gg/p/'+str(ALLY_CODE)+'/characters/'
    driver = webdriver.Chrome()
    driver.get(url_to_scrape)
    character_data = []
    try:
        driver.implicitly_wait(10)
        wait = WebDriverWait(driver, 20)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        character_entries = soup.select('.js-unit-search__results .js-unit-search__result')
        character_data = []
        for character_entry in character_entries:
            character_name = character_entry['data-unit-name']
            image = character_entry.select_one("img")["src"]
            level_element = character_entry.select_one('.character-portrait__level text')
            if level_element:
                character_level = int(level_element.get_text(strip=True))
            relic_element = character_entry.select_one('.relic-badge')
            if relic_element:
                relic_level = int(relic_element.text.strip())
                gear_level = 13  # Characters with relics have a gear tier of 13
                character_level = 85
            else:
                relic_level = 0
                gear_element = character_entry.select_one('.character-portrait__gframe')
                if gear_element:
                    gear_class = gear_element.get('class')
                    gear_level = [int(cls.split('--tier-')[-1]) for cls in gear_class if '--tier-' in cls]
                    gear_level = gear_level[0] if gear_level else None
            active_stars = 7 - len(character_entry.select('.rarity-range__star--inactive'))
            tags = character_entry['data-unit-tags']
            character_data.append((character_name, image, active_stars, character_level, gear_level, relic_level, tags))

        conn = get_db_connection()
        cursor = conn.cursor()
        
        for character in character_data:
            # Check if the character already exists
            cursor.execute("SELECT * FROM characters WHERE characterName = ?", (character[0],))
            existing_character = cursor.fetchone()
            
            if existing_character:
                # Update existing character
                cursor.execute("""
                    UPDATE characters 
                    SET characterImage = ?, stars = ?, level = ?, gear = ?, relic = ?, tags = ?
                    WHERE characterName = ?
                """, (character[1], character[2], character[3], character[4], character[5], character[6], character[0]))
            else:
                # Insert new character
                cursor.execute("""
                    INSERT INTO characters (characterName, characterImage, stars, level, gear, relic, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, character)
        
        conn.commit()
        conn.close()
        driver.quit()
        flash('Characters updated successfully!', 'success')
        return redirect(url_for('characters'))

    except TimeoutException:
        print("Timeout: Unable to extract character data.")
        driver.quit()
        flash('Timeout occurred while updating characters.', 'error')
        return redirect(url_for('characters'))
    except Exception as e:
        print(f"An error occurred: {e}")
        driver.quit()
        flash(f'An error occurred while updating characters: {str(e)}', 'error')
        return redirect(url_for('characters'))
@app.route('/update_ships', methods=['POST'])
def update_ships():
    url_to_scrape = 'https://swgoh.gg/p/' + str(ALLY_CODE) + '/ships/'
    driver = webdriver.Chrome()
    ship_data = []

    try:
        # Open the URL and scrape the page
        driver.get(url_to_scrape)
        driver.implicitly_wait(10)
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find all ship entries
        ship_entries = soup.select('.js-unit-search__results .js-unit-search__result')

        # Extract data for each ship
        for ship_entry in ship_entries:
            ship_name = ship_entry['data-unit-name']  # Extract the name from the data-unit-name attribute
            ship_image = ship_entry.select_one("img")["src"]
            # Extract level
            level_element = ship_entry.select_one('.ship-portrait__level text')
            if level_element:
                ship_level = int(level_element.get_text(strip=True))
            else:
                ship_level = None

            # Extract stars
            total_stars = len(ship_entry.select('.rarity-range__star'))
            active_stars = total_stars - len(ship_entry.select('.rarity-range__star--inactive'))

            # Append the extracted data to the list
            ship_data.append([ship_name, ship_image, active_stars, ship_level])

        conn = get_db_connection()
        cursor = conn.cursor()

        for ship in ship_data:
            # Check if ship exists
            cursor.execute("SELECT * FROM ships WHERE shipName = ?", (ship[0],))
            existing_ship = cursor.fetchone()

            if existing_ship:
                # Update existing ship
                cursor.execute("""
                    UPDATE ships 
                    SET shipImage = ?, stars = ?, level = ?
                    WHERE shipName = ?
                """, (ship[1], ship[2], ship[3], ship[0]))
            else:
                # Insert new ship
                cursor.execute("""
                    INSERT INTO ships (shipName, shipImage, stars, level)
                    VALUES (?, ?, ?, ?)
                """, (ship[0], ship[1], ship[2], ship[3]))


        conn.commit()
        conn.close()

        # Flash success message and redirect to /ships page
        flash('Ships updated successfully!', 'success')
        return redirect(url_for('ships'))

    except Exception as e:
        # Handle any errors during scraping or database insertion
        print(f"An error occurred while updating ships: {e}")
        flash(f'An error occurred while updating ships: {str(e)}', 'error')
        return redirect(url_for('ships'))

    finally:
        # Ensure the driver is closed even if an error occurs
        driver.quit()
        
if __name__ == '__main__':
    app.run(debug=True)
