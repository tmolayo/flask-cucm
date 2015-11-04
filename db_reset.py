# INSERT Command
# import the sqlite3 library
import sqlite3
from config import DATABASE_PATH

# Creating the population table
with sqlite3.connect(DATABASE_PATH) as connection:
  c = connection.cursor()
  # If we want to create a new table, uncomment the next two lines
  c.execute("DROP TABLE IF EXISTS users")
  # Create the table
  c.execute("""CREATE TABLE users
			  (task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL, 
        ip_phone TEXT NOT NULL,
        ip_phone_type INTEGER NOT NULL,
        status INTEGER NOT NULL)
			  """)
