import sqlite3

def initialize_database(db_name="database.db"):
    """Initialize the SQLite database with the characters and ships tables and insert sample data."""
    connection = sqlite3.connect(db_name)
    cursor = connection.cursor()
    
    # SQL commands to create tables
    create_characters_table = """
    DROP TABLE IF EXISTS characters;
    CREATE TABLE characters (
        characterID INTEGER PRIMARY KEY AUTOINCREMENT,
        characterName TEXT NOT NULL,
        characterImage TEXT NOT NULL,
        stars INTEGER NOT NULL,
        level INTEGER NOT NULL,
        gear INTEGER NOT NULL,
        relic INTEGER NOT NULL,
        tags TEXT
    );
    """
    
    create_ships_table = """
    DROP TABLE IF EXISTS ships;
    CREATE TABLE ships (
    shipID INTEGER PRIMARY KEY AUTOINCREMENT,
    shipName TEXT NOT NULL,
    shipImage TEXT NOT NULL,
    stars INTEGER NOT NULL,
    level INTEGER NOT NULL,
    tags TEXT,
    pilotID TEXT
);
    """
    
    # Sample data for characters
    insert_characters = """
    INSERT INTO characters (characterName, characterImage, stars, level, gear, relic, tags)
    VALUES 
    ('Luke Skywalker', 'luke.png', 7, 85, 13, 7, 'Rebel,Jedi'),
    ('Darth Vader', 'vader.png', 7, 85, 13, 5, 'Empire,Sith'),
    ('Han Solo', 'han.png', 7, 85, 12, 0, 'Rebel,Scoundrel');
    """

    # Sample data for ships
    insert_ships = """
    INSERT INTO ships (shipName, level, stars, shipImage, tags, pilotID)
    VALUES
    ('X-wing', 85, 7, 'xwing.png', 'Rebel', 1),
    ('TIE Advanced x1', 85, 7, 'tieadvanced.png', 'Empire', 2),
    ('Millennium Falcon', 85, 7, 'falcon.png', 'Rebel,Scoundrel', 3);
    """
    
    try:
        # Execute SQL commands
        cursor.executescript(create_characters_table)
        cursor.executescript(create_ships_table)
        cursor.executescript(insert_characters)
        cursor.executescript(insert_ships)
        print("Database initialized and sample data inserted successfully.")
    except sqlite3.Error as e:
        print(f"An error occurred while initializing the database: {e}")
    finally:
        # Close the connection
        connection.commit()
        connection.close()

if __name__ == "__main__":
    initialize_database()
