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

  # insert data into table
  c.execute(
    'INSERT INTO users (username, ip_phone, ip_phone_type, status)'
    'VALUES("fbobes", "SEP01888867530E", 7942, 1)'
  )

  c.execute("SELECT task_id, username, ip_phone, ip_phone_type, status from users")

  # fetchall() retrieves all records from the query
  rows = c.fetchall()
  # output the rows to the screen, row by row
  for r in rows:
    print r[0], r[1], r[2], r[3], r[4] 
