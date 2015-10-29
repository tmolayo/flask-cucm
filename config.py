import os
# grab the folder where this script lives
basedir = os.path.abspath(os.path.dirname(__file__))

DATABASE = 'cucm.db'

WTF_CSRF_ENABLED = True 
SECRET_KEY = 'whatever_150n2@C1'

# define the full path for the database
DATABASE_PATH = os.path.join(basedir, DATABASE)
