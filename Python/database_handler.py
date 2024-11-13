import sqlite3
import datetime
def big_bang(cur = cur, conn = conn):
    conn = sqlite3.connect("../Databases/lg4x-v2-univers.db")
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
    FOREIGN KEY (Data_id) REFERENCES DATA (DID),
    FOREIGN KEY (Fit_id) REFERENCES FITS (FID))''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS Project
    (ID INTEGER PRIMARY KEY,
    Name TEXT, 
    Comment TEXT, 
    Spec_id INT,
    FOREIGN KEY (Spec_id) REFERENCES SPECTRA (SID))''')

    conn.commit()
    except sqlite3.Error as error:
        print("Error while working with SQLite", error)
    finally:
        if conn:
            conn.close()
            print("sqlite connection is closed")
