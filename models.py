from views import db
import datetime
#import logging
#logging.basicConfig()
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

class User(db.Model):

  __tablename__ = "users"

  task_id = db.Column(db.Integer, primary_key = True)
  username = db.Column(db.String, unique=True, nullable = False)
  ip_phone = db.Column(db.String, nullable = False)
  ip_phone_type = db.Column(db.Integer, nullable = False)
  status = db.Column(db.Integer)


  def __init__(self, username, ip_phone, ip_phone_type, status):
  	self.username = username
  	self.ip_phone = ip_phone
  	self.ip_phone_type = ip_phone_type
  	self.status = status

  def __repr__(self):
  	return '<name {0}>'.format(self.username)