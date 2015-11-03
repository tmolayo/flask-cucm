# INSERT Command
# import the sqlite3 library

from views import db
from models import User

# create the database and the db table
db.create_all()

# insert data into table
db.session.add(User("fbobes", "SEP01888867530E", 7942, 1))

# commit the changes
db.session.commit() 
