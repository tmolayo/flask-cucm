# project/views.py
import sqlite3
from functools import wraps
from flask import Flask, flash, redirect, render_template, \
  request, session, url_for, g
from forms import AddTaskForm 
from cucm_library import user_association, user_provisioning, \
  user_deprovisioning 

# config
app = Flask(__name__) 
app.config.from_object('config')

# helper functions
def connect_db():
  return sqlite3.connect(app.config['DATABASE_PATH'])


# Add new tasks
@app.route('/add/', methods=['POST']) 
def new_task():
  g.db = connect_db()
  username = request.form['username']
  ip_phone = request.form['ip_phone'] 
  ip_phone_type = request.form['ip_phone_type']
  if not username or not ip_phone or not ip_phone_type:
    flash("All fields are required. Please try again.")
    return redirect(url_for('tasks')) 
  else:
    g.db.execute('insert into users (username, ip_phone, ip_phone_type, status) \
      values (?, ?, ?, 1)', [ 
        request.form['username'], 
        request.form['ip_phone'], 
        request.form['ip_phone_type']
      ] 
    )
    g.db.commit()
    g.db.close()
    flash('New entry was successfully posted. Thanks.') 
    return redirect(url_for('tasks'))
'''
# Add user 
@app.route('/complete/<int:task_id>/') 
def complete(task_id):
  g.db = connect_db() 
  g.db.execute(
    'update users set status = 0 where task_id='+str(task_id) )
  g.db.commit()   
  g.db.close()
  flash('The user was marked as complete.') 
  return redirect(url_for('tasks'))
'''

# Add user 
@app.route('/complete/<int:task_id>/') 
def complete(task_id):
  g.db = connect_db() 
  cur = g.db.execute(	
    'select username, ip_phone, ip_phone_type from users where task_id='+str(task_id)
    ) 
  check_user = [
    dict(username=row[0], ip_phone=row[1], ip_phone_type=row[2]) for row in cur.fetchall()
    ] 
  g.db.close()
  username = check_user[0]["username"]
  ip_phone = check_user[0]["ip_phone"]
  ip_phone_type = check_user[0]["ip_phone_type"]
  flash('The phones that have been associated with the user are:')
  associated_phones = user_provisioning(username, ip_phone, ip_phone_type)
  return render_template(
   'phones_provisioned.html', 
   associated_phones=associated_phones,
   username=username)  

# Check the user association 
@app.route('/check_entry/<int:task_id>/') 
def check_entry(task_id):
  g.db = connect_db() 
  cur = g.db.execute(	
    'select username, ip_phone, ip_phone_type from users where task_id='+str(task_id)
    ) 
  check_user = [
    dict(username=row[0], ip_phone=row[1], ip_phone_type=row[2]) for row in cur.fetchall()
    ] 
  g.db.close()
  username = check_user[0]["username"]
  flash('The phones currently associated to the user are:')
  associated_phones = user_association(username)
  return render_template(
   'phones.html', 
   associated_phones=associated_phones,
   username=username)  

'''
# Delete user
@app.route('/del/<int:task_id>/') 
def delete_entry(task_id):
  g.db = connect_db()
  g.db.execute(
    'delete from users where task_id='+str(task_id)) 
  g.db.commit()
  g.db.close()
  flash('The user has been deleted.')
  return redirect(url_for('tasks'))
'''
# Delete user
@app.route('/del/<int:task_id>/') 
def delete_entry(task_id):
  g.db = connect_db() 
  cur = g.db.execute(	
    'select username, ip_phone, ip_phone_type from users where task_id='+str(task_id)
    ) 
  check_user = [
    dict(username=row[0], ip_phone=row[1]) for row in cur.fetchall()
    ] 
  g.db.close()
  username = check_user[0]["username"]
  ip_phone = check_user[0]["ip_phone"]
  flash('The phones that have been disassociated for the user are:')
  associated_phones = user_deprovisioning(username, ip_phone)
  return render_template(
   'phones_deprovisioned.html', 
   associated_phones=associated_phones,
   username=username) 

@app.route('/')
@app.route('/tasks/') 
def tasks():
  g.db = connect_db() 
  cur = g.db.execute(
    'select username, ip_phone, ip_phone_type, task_id from users where status=1'
    )
  open_tasks = [
    dict(username=row[0], ip_phone=row[1], ip_phone_type=row[2], task_id=row[3]) for row in cur.fetchall()
    ]
  cur = g.db.execute(
    'select username, ip_phone, ip_phone_type, task_id from users where status=0'
    )
  closed_tasks = [
    dict(username=row[0], ip_phone=row[1], ip_phone_type=row[2], task_id=row[3]) for row in cur.fetchall()
    ]
  g.db.close()
  return render_template(
   'tasks.html',
   form=AddTaskForm(request.form), 
   open_tasks=open_tasks, 
   closed_tasks=closed_tasks
  )   