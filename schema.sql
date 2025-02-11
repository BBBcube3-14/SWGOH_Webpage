-- Drop the tables if they exist
DROP TABLE IF EXISTS characters;
DROP TABLE IF EXISTS ships;

-- Create the characters table
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

-- Create the ships table with a pilotID field
CREATE TABLE ships (
    shipID INTEGER PRIMARY KEY AUTOINCREMENT,
    shipName TEXT NOT NULL,
    shipImage TEXT NOT NULL,
    stars INTEGER NOT NULL,
    level INTEGER NOT NULL,
    tags TEXT,
    pilotID TEXT
);
