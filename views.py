# project/views.py
from functools import wraps
from flask import Flask, flash, redirect, render_template, \
  request, session, url_for
from forms import AddTaskForm 
from cucm_library import user_association, user_provisioning, \
  user_deprovisioning 
from flask.ext.sqlalchemy import SQLAlchemy   

# config
app = Flask(__name__) 
app.config.from_object('config')
db = SQLAlchemy(app)

from models import User

def flash_errors(form):
  for field, errors in form.errors.items():
    for error in errors:
      flash(u"Error in the %s field - %s" % (
        getattr(form, field).label.text, error), 'error')

@app.route('/logout/')
def logout(): 
  session.pop('logged_in', None) 
  flash('Goodbye!')
  return redirect(url_for('login'))

def login_required(test): 
  @wraps(test)
  def wrap(*args, **kwargs):
    if 'logged_in' in session:
      return test(*args, **kwargs) 
    else:
      flash('You need to login first.')
      return redirect(url_for('login')) 
  return wrap

@app.route('/db_reset')
def db_reset(): 
  db.session.query(User).delete()
  db.session.commit()
  flash('Records have been removed!')
  return redirect(url_for('tasks'))

# Add new query
@app.route('/add/', methods=['GET', 'POST'])
@login_required
def new_task():
  form = AddTaskForm(request.form)
  if request.method == 'POST':
    if form.validate_on_submit():
      new_user = User(
        form.username.data,
        form.ip_phone.data,
        form.ip_phone_type.data,
        '1'
      )
      db.session.add(new_user)
      db.session.commit()
      flash('New entry was successfully posted. Thanks.') 
  return redirect(url_for('tasks'))

# Add phones for a user 
@app.route('/complete/<int:task_id>/')
@login_required
def complete(task_id):
  new_id = task_id
  #db.session.query(User).filter_by(task_id=new_id).update({"status":"0"})
  check_user = User.query.filter_by(task_id=task_id).first()
  db.session.commit()
  username = check_user.username
  ip_phone = check_user.ip_phone
  ip_phone_type = check_user.ip_phone_type
  flash('The phones that have been associated with the user are:')
  associated_phones = user_provisioning(username, ip_phone, ip_phone_type)
  return render_template(
   'phones_provisioned.html', 
   associated_phones=associated_phones,
   username=username)  

# Check the user association with his line and phones
@app.route('/check_entry/<int:task_id>/')
@login_required
def check_entry(task_id):
  new_id = task_id
  check_user = User.query.filter_by(task_id=task_id).first()
  db.session.commit()
  username = check_user.username
  flash('The phones currently associated to the user are:')
  associated_phones = user_association(username)
  return render_template(
   'phones.html', 
   associated_phones=associated_phones,
   username=username)  

# Delete phones for a user
@app.route('/del/<int:task_id>/')
@login_required
def delete_entry(task_id):
  new_id = task_id
  check_user = User.query.filter_by(task_id=task_id).first()
  db.session.commit()
  username = check_user.username
  ip_phone = check_user.ip_phone
  flash('The phones that have been disassociated for the user are:')
  associated_phones = user_deprovisioning(username, ip_phone)
  return render_template(
   'phones_deprovisioned.html', 
   associated_phones=associated_phones,
   username=username) 


# Login page
@app.route('/', methods=['GET', 'POST']) 
def login():
  if request.method == 'POST':
    if request.form['username'] != app.config['USERNAME'] \
    or request.form['password'] != app.config['PASSWORD']:
      error = 'Invalid Credentials. Please try again.'
      return render_template('login.html', error=error) 
    else:
      session['logged_in'] = True 
      flash('Welcome!')
      return redirect(url_for('tasks'))
  return render_template('login.html')

# Page afer login from where queries, adds, deletes and updates can be done 
@app.route('/tasks/') 
@login_required
def tasks():
  open_tasks = db.session.query(User) \
    .filter_by(status='1').order_by(User.username.asc())
  closed_tasks = db.session.query(User) \
    .filter_by(status='0').order_by(User.username.asc())  
  return render_template(
   'tasks.html',
   form=AddTaskForm(request.form), 
   open_tasks=open_tasks, 
   closed_tasks=closed_tasks
  )   