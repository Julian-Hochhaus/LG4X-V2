import sqlite3
import datetime
def big_bang():
    try:
        conn = sqlite3.connect("../Databases/lg4x-v2-univers.db")
        conn.execute("PRAGMA foreign_keys = ON")
        cur = conn.cursor()
        print("Connected to SQLite")
        
        cur.execute('''CREATE TABLE IF NOT EXISTS Fits
        (FID INTEGER PRIMARY KEY,
        comment TEXT,
        FilePath TEXT)''')
        
        cur.execute('''CREATE TABLE IF NOT EXISTS Data
        (DID INTEGER PRIMARY KEY,
        comment TEXT,
        FilePath TEXT)''')
    
        cur.execute('''CREATE TABLE IF NOT EXISTS Spectra
        (SID INTEGER PRIMARY KEY,
        creationDate timestamp,
        lastChange timestamp,
        name TEXT,
        comment TEXT,
        Data_id INT,
        Fit_id INT,
        FOREIGN KEY (Data_id) REFERENCES DATA (DID) ON DELETE CASCADE,
        FOREIGN KEY (Fit_id) REFERENCES FITS (FID) ON DELETE CASCADE)''')
        
        cur.execute('''CREATE TABLE IF NOT EXISTS Project
        (ID INTEGER PRIMARY KEY,
        Name TEXT, 
        Comment TEXT, 
        Spec_id INT,
        FOREIGN KEY (Spec_id) REFERENCES SPECTRA (SID) ON DELETE CASCADE)''')
        
        conn.commit()
    except sqlite3.Error as error:
        print("Error while working with SQLite", error)
    finally:
        if conn:
            conn.close()
            print("sqlite connection is closed")


big_bang()
