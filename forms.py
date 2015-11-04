# project/forms.py
from flask_wtf import Form
from wtforms import StringField, DateField, IntegerField, \
  SelectField
from wtforms.validators import DataRequired, Length

class AddTaskForm(Form):
  task_id = IntegerField()
  username = StringField('User Name', validators=[DataRequired()])
  ip_phone = StringField('IP Phone', validators=[DataRequired(), Length(min=15, max=15)])
  
  ip_phone_type = SelectField( 
  	'IP Phone Type',
    validators=[DataRequired()], 
    choices=[
      ('7942', '7942'), ('7962', '7962')
    ] 
  )
  status = IntegerField('Status')