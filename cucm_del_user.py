#! /usr/bin/env python

from suds.client import Client
from suds.transport.https import HttpAuthenticated
import base64, logging, sys, suds, platform
import ssl, urllib
from suds.xsd.doctor import Import
from suds.xsd.doctor import ImportDoctor

def getAuthentication(system_type):
    
  #open config file to grab username and password
  #conf = open('/var/tmp/creds.conf', 'r')
  conf = open('creds.conf', 'r')
  config = conf.readlines()
  conf.close()

  for line in config:
    if 'USERNAME_'+system_type.lower() in line:
      usr_list = line.strip().split(' = ')
      username = str(usr_list[1]).lstrip("'").rstrip("'")

    elif 'PASSWORD_'+system_type.lower() in line:
      passwd_list = line.strip().split(' = ')
      password = base64.b64decode(str(passwd_list[1]).lstrip("'").rstrip("'"))

  auth = (username,password)
  return auth 


def removePhone(userid,ip_phone,User_file,client):
  try:
  # First we remove the physical phone
    result = client.service.removePhone(name=ip_phone)
  except:
    print 'There is probably no '+ip_phone+' device. The error message is '+str(sys.exc_info()[1])      
    User_file.write('There is probably no '+ip_phone+' device. The error message is '+str(sys.exc_info()[1])+'\n')
  
# Then we remove the other phones
  try:
    result = client.service.removePhone(name='CSF'+userid.upper())
  except:
    print 'There is probably no CSF'+userid.upper()+' device. The error message is '+str(sys.exc_info()[1])      
    User_file.write('There is probably no CSF'+userid.upper()+' device. The error message is '+str(sys.exc_info()[1])+'\n')

  try:
    result = client.service.removePhone(name='BOT'+userid.upper())
  except:
    print 'There is probably no BOT'+userid.upper()+' device. The error message is '+str(sys.exc_info()[1])      
    User_file.write('There is probably no BOT'+userid.upper()+' device. The error message is '+str(sys.exc_info()[1])+'\n')
  
  try:
    result = client.service.removePhone(name='TAB'+userid.upper())
  except:
    print 'There is probably no TAB'+userid.upper()+' device. The error message is '+str(sys.exc_info()[1])      
    User_file.write('There is probably no TAB'+userid.upper()+' device. The error message is '+str(sys.exc_info()[1])+'\n')
 
  try:
    result = client.service.removePhone(name='TCT'+userid.upper())
  except:
    print 'There is probably no TCT'+userid.upper()+' device. The error message is '+str(sys.exc_info()[1])      
    User_file.write('There is probably no TCT'+userid.upper()+' device. The error message is '+str(sys.exc_info()[1])+'\n')
  

def cucm_deprovisioning(filename):

  # First we connect to the AXL API
  # Logging for debugging
  logging.basicConfig(level=logging.INFO)
  #logging.getLogger('suds.client').setLevel(logging.DEBUG)
  logging.getLogger('suds.client').setLevel(logging.CRITICAL)
  #logging.getLogger('suds.transport').setLevel(logging.DEBUG)
  #logging.getLogger('suds.xsd.schema').setLevel(logging.CRITICAL)
  #logging.getLogger('suds.wsdl').setLevel(logging.CRITICAL)

 
  location = 'https://172.20.132.70:8443/axl/'
  if platform.uname()[0] == 'Darwin':
    # OSX path
    wsdl = 'file:///Users/fbobes/Documents/Python/CUCM/AXLAPI.wsdl'
  elif platform.uname()[0] == 'Linux':
    # Linux path
    wsdl = 'file:///home/fbobes/cucm/AXLAPI.wsdl'
  else: 
    # Some other OS
    wsdl = 'file:///home/fbobes/cucm/AXLAPI.wsdl'
  auth = getAuthentication("axl")  
  Username = auth[0]
  Password = auth[1]

  
  # Bypassing SSL self-cert check
  ssl._create_default_https_context = ssl._create_unverified_context

  # URL Detail
  client = Client(wsdl,location = location, transport = HttpAuthenticated(username = Username, password = Password))

  # Opening the file containing the users details 
  in_file = open(filename, 'r')
  config = in_file.readlines()
  in_file.close()

  #Generating a file that contains the provisioning results
  User_file = open('cucm_user_deprovisioning_results.txt', 'w') 
  
  for line in config[1:]:

    line=line.replace('\n','')
    fields = line.split(',')
    userid = fields[0]
    ip_phone = fields[1]
    # We remove the phones
    removePhone(userid,ip_phone,User_file,client)  
  
  
    # Verification  
    # Getting a user detail
    result = client.service.getUser(userid=userid)
    if result['return']['user']['associatedDevices'] == "":
      print 'The devices associated with '+userid+' have been removed'
      User_file.write('The devices associated with '+userid+' have been removed\n')
    else:
      print 'The phones have not been removed succesfuly for',userid  
      User_file.write('The phones have not been removed succesfuly for',userid+'\n')
      
  print 'Results were saved in cucm_user_deprovisioning_results.txt'

  

  
def main():
  # This is program reads data from CSV files
  # to create phones and associates user(s) with their phones  
  args = sys.argv[1:]
  if (len(args) <1):
    print 'usage: python cucm_user_deprovisoning.py cucm_users.csv'
    sys.exit(1)
  
  input_file = args[0]
 
  cucm_deprovisioning(input_file)

if __name__ == "__main__":
  main()  
