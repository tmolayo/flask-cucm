#! /usr/bin/env python

from suds.client import Client
from suds.transport.https import HttpAuthenticated
# to install suds, use:
# sudo pip install suds-jurko
import base64, logging, sys, suds, platform
import ssl, urllib
import ldap
# to install python-ldap in Mavericks/Yosemite:
# sudo pip install python-ldap --global-option=build_ext --global-option="-I$(xcrun --show-sdk-path)/usr/include/sasl"
from binascii import hexlify
from flask import flash

def getAuthentication(system_type):
  """Grabs the credentials to connect
  to LDAP and CUCM
  """ 
    
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

def connect_AXL():

  # First we connect to the AXL API
  # Logging for debugging
  logging.basicConfig(level=logging.INFO)
  #logging.getLogger('suds.client').setLevel(logging.DEBUG)
  logging.getLogger('suds.client').setLevel(logging.CRITICAL)
  #logging.getLogger('suds.transport').setLevel(logging.DEBUG)
  #logging.getLogger('suds.xsd.schema').setLevel(logging.CRITICAL)
  #logging.getLogger('suds.wsdl').setLevel(logging.CRITICAL)
  
  #"Connecting to myphone.central1.com to add the line and phones for the user"
  location = 'https://172.20.133.71:8443/axl/'
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
  client = Client(wsdl,location = location, transport = HttpAuthenticated(username = Username, password = Password),faults=False)

  return client

def user_association(userid):
  """Connects to CUCM, builds the config including 
  lines, phones and user association
  """ 
  client = connect_AXL()
 
  res = [] 
  res1 = []

  try:  
    result = client.service.getUser(userid=userid)
    res.append('The phones associated with '+userid+':')
    res.append(result[1]['return']['user']['associatedDevices']['device'])
  except:
    res.append('There is probably no associated devices for '+userid+'. The error message is '+str(sys.exc_info()[0]))   
  
  result = sasl_connect(userid)

  ldap_failed = 'False'
  if not result:
    res.append('This user '+userid+' has not been found in AD')
    res.append('No phone has been associated or created')
    ldap_failed = 'True'   
  elif len(result[0][1]) != 4:
    res.append('This user '+userid+' is missing some info in LDAP, probably his extension (ipPhone) is not set in AD')
    res.append('No phone has been associated or created')
    ldap_failed = 'True'

 
  if ldap_failed == 'False':    
    directory_number = ''.join(result[0][1]['ipPhone'])
    try:
      if directory_number.startswith("8"):
        routePartitionName = 'PT_TOMS_DN'
      else:
        routePartitionName = 'PT_VACS_DN'  
       
      result = client.service.getLine(pattern=directory_number,routePartitionName=routePartitionName)
      res1.append('The phones associated with '+directory_number+':')
      res1.append(result[1]['return']['line']['associatedDevices']['device'])
      res.extend(res1)
    except:
      res.append('There is probably no associated devices for '+directory_number+'. The error message is '+str(sys.exc_info()[0]))  
  #return (", ".join(result))
  return res


def sasl_connect(username):
  """Connects to LDAP to retrieve the user phone number and 
  extension 
  """  
  connect = ldap.initialize('ldap://172.20.130.254')
  # "Connecting to LDAP to extract the user extension"
  try:
    
    auth = getAuthentication("ldap")
    userid = auth[0]
    pw = auth[1] 
    auth_tokens = ldap.sasl.digest_md5( userid, pw )
    connect.sasl_interactive_bind_s( "", auth_tokens )

    base_dn = 'OU=SWS,OU=Corp,DC=cs,DC=ad,DC=central1,DC=com'
    search_filter = 'sAMAccountName='+username
    attrs = ['sAMAccountName','TelephoneNumber','ipPhone','name']
    result = connect.search_s(base_dn, ldap.SCOPE_SUBTREE, search_filter, attrs )
    #print result
    #for k,v in result[0][1].items():
    # print k,v
  except ldap.INVALID_CREDENTIALS:
    # "Username or password is incorrect."
    sys.exit()    
  except ldap.LDAPError, e:
    sys.stderr.write("Fatal Error.n")
    if type(e.message) == dict:
      for (k, v) in e.message.iteritems():
        sys.stderr.write("%s: %sn" % (k, v))
    else: 
      sys.stderr.write("Error: %sn" % e.message);
    sys.exit()
  finally:
    try:
      #print "Doing unbind."
      connect.unbind()
    except ldap.LDAPError, e:
      pass
  return result              




def updateUser(userid,ip_phone):
  SOAP = '<SOAP-ENV:Envelope xmlns:ns0="http://www.cisco.com/AXL/API/10.5" xmlns:ns1="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">'
  SOAP += '<SOAP-ENV:Header/>'
  SOAP += '<ns1:Body>'
  SOAP += '<ns0:updateUser>'
  SOAP += '<name>' + userid + '</name>'
  SOAP += '<userid>' + userid + '</userid>'  
  SOAP += '         <enableCti>true</enableCti>'
  SOAP += '<associatedDevices><device>'+ip_phone+'</device><device>CSF'+userid.upper()+\
  '</device><device>BOT'+userid.upper()+'</device><device>TCT'+userid.upper()+\
  '</device><device>TAB'+userid.upper()+'</device></associatedDevices>'
  SOAP += '</ns0:updateUser>'
  SOAP += '</ns1:Body>'
  SOAP += '</SOAP-ENV:Envelope>'
  return SOAP

def user_provisioning(userid, ip_phone, ip_phone_type):
  """Connects to CUCM, builds the config including 
  lines, phones and user association
  """ 

  client = connect_AXL()
  
  res = [] 
  res1 = []
  res2 = []
  
  # First we want to check that the user is in AD and that he is an extension
  result = sasl_connect(userid)

  ldap_failed = 'False'
  if not result:
    res.append('This user '+userid+' has not been found in AD')
    res.append('No phone has been associated or created')
    ldap_failed = 'True'   
  elif len(result[0][1]) != 4:
    res.append('This user '+userid+' is missing some info in LDAP, probably his extension (ipPhone) is not set in AD')
    res.append('No phone has been associated or created')
    ldap_failed = 'True'

 
  if ldap_failed == 'False':    
    directory_number = ''.join(result[0][1]['ipPhone'])
    e164mask = (''.join(result[0][1]['telephoneNumber'])).replace('-','')
    full_name = ''.join(result[0][1]['name']) 
    if directory_number == '':  
      res.append('This user',userid,'has no extension set in the ipPhone field in AD')
    elif directory_number != '' and e164mask == '':
      res.append('This user',userid,'has no extension set in the telephoneNumber field in AD')
    
    #We add the line and if it exists already, it will error out and move on to the next step:
    res1 = addLine(userid,full_name,directory_number,client)
    res.extend(res1)
    # We create the phones
    res2 = addPhone(userid,full_name,directory_number,ip_phone,str(ip_phone_type),e164mask,client) 
    res.extend(res2)
    #We finally associate the user with his phones
    #result = client.service.updateUser(__inject={'msg':updateUser(userid,ip_phone)})
    #result = updateAUser(userid,ip_phone,client)
    
    #if result[0] == 200:
    #  print 'All the phones were associated with user: '+userid
    #elif result[0] == 500:
    #  print 'Error message when associating the phones for '+userid+': '+result[1].faultstring 
  
  return res

def user_deprovisioning(userid, ip_phone):
  """Connects to CUCM, removes the phones for a user
  but not the extension since it can be shared
  """ 

  client = connect_AXL()

  res = [] 
  res1 = []
  res2 = []
 
  
  # First we check that the user exists 
  user_failed = 'False'
  try:
    result = client.service.getUser(userid=userid)
    if result[0] == 500:
      user_failed = 'True'
      res.append('Error message when looking for '+userid.upper()+' information.')
  except:
    res.append('Error message when looking for '+userid.upper()+' information: '+str(sys.exc_info()[1])+'\n')
    user_failed = 'True'
  

  # We remove the phones
  res1 = removePhone(userid,ip_phone,client)  
  res.extend(res1)
  # Verification  
  # Getting a user detail
  if user_failed == 'False':
    try:
      result = client.service.getUser(userid=userid)
    except:
      res.append('Error message when looking for '+userid.upper()+' information: '+str(sys.exc_info()[1])+'\n')
    if result[1]['return']['user']['associatedDevices'] == "":
      res.append('The devices associated with '+userid+' have been removed')
    else:
      res.append('The phones have not been removed succesfuly for',userid)  
      
  #print 'Results were saved in cucm_user_deprovisioning_results.txt'
  return res



def addLine(userid,full_name,directory_number,client):

  res =[]
  # Setting some variables   
  if directory_number.startswith("8"):
    location = 'TOMS'
  else:
    location = 'VACS' 
  
  result = client.service.addLine({
    'pattern':directory_number,
    'routePartitionName':'PT_'+location+'_DN',
    'description':full_name+' '+directory_number,
    'alertingName':full_name,
    'asciiAlertingName':full_name,
    'voiceMailProfileName':'Default',
    'shareLineAppearanceCssName':'CSS-'+location+'-INT-Line',
    'callForwardAll':{'callingSearchSpaceName':'CSS-'+location+'-INT-Line',
    'secondaryCallingSearchSpaceName':'CSS-'+location+'-Phone'},}) 
  if result[0] == 200:
    res.append('The extension '+directory_number+' has been added')
  elif result[0] == 500:
    res.append('Error message when adding Line '+directory_number+': '+result[1].faultstring)

  return res  
   
def updateAUser(userid,ip_phone,client):

  res =[]
  result = client.service.updateUser({
    'uuid':'4AF0471F-4752-47FA-B3CD-FD025732FF02'
    })

  if result[0] == 200:
    print 'All the phones were associated with user: '+userid
    res.append('All the phones were associated with user: '+userid)
  elif result[0] == 500:
    print 'Error message when associating the phones for '+userid+': '+result[1].faultstring
    res.append('Error message when associating the phones for '+userid+': '+result[1].faultstring)
  
  return res
  
def addPhone(userid,full_name,directory_number,ip_phone,ip_phone_type,e164mask,client):

  res =[]
  # Setting some variables   
  if directory_number.startswith("8"):
    location = 'TOMS'
  else:
    location = 'VACS'  
    
  if ip_phone_type == '7942':
    template =  'SCCP - 2 Line'
  elif ip_phone_type == '7962':
    template =  'SCCP - 4 Line'  

  # First we add the physical phone
  result = client.service.addPhone({
    'name':ip_phone,
    'class':'Phone',
    'description':full_name+' '+directory_number,    
    'product':'Cisco '+ip_phone_type,
    'protocol':'SCCP',
    'protocolSide':'User',
    'callingSearchSpaceName':'CSS-'+location+'-INT-Line',
    'devicePoolName':'DP-'+location+'-'+ip_phone_type,    
    'commonPhoneConfigName':'Standard Common Phone Profile',
    'commonDeviceConfigName':location+'-COMMON-DEVICE',
    'mediaResourceListName':'MGL-'+location,    
    'locationName':location+'-Location',
    'ownerUserName':userid,  
    'lines': {'line': [{
      'display':full_name,
      'displayAscii':full_name,
      'e164Mask':e164mask,
      'callInfoDisplay':{'callerNumber':'true','redirectedNumber':'true'},
      'maxNumCalls':'4',
      'busyTrigger':'2',
      'associatedEndusers':{'enduser':[{'userId':userid}]},
      'dirn':{'pattern':directory_number,'routePartitionName':'PT_'+location+'_DN'},'index':'1'}]},      
    'securityProfileName':'Cisco '+ip_phone_type+' - Standard SCCP Non-Secure Profile',
    'subscribeCallingSearchSpaceName':'CSS-'+location+'-Phone',
    'useTrustedRelayPoint':'Default','presenceGroupName':'Standard Presence Group',
    'phoneTemplateName':'Standard '+ip_phone_type+' '+template,
    'softkeyTemplateName':'C1-Standard Feature',})
  if result[0] == 200:
    res.append('The phone '+ip_phone+' has been added') 
  elif result[0] == 500:
    res.append('Error message when adding '+ip_phone+': '+result[1].faultstring)

# Then we add a CSF 
  result = client.service.addPhone({
    'name':'CSF'+userid.upper(),
    'class':'Phone',
    'description':'CSF Device for '+userid,
    'product':'Cisco Unified Client Services Framework',
    'protocol':'SIP',
    'protocolSide':'User',
    'callingSearchSpaceName':'CSS-'+location+'-INT-Line',
    'devicePoolName':'DP-'+location,
    'commonPhoneConfigName':'Standard Common Phone Profile',
    'commonDeviceConfigName':location+'-COMMON-DEVICE',
    'mediaResourceListName':'MGL-'+location,
    'locationName':location+'-Location',
    'ownerUserName':userid,
    'primaryPhoneName':ip_phone,
    'lines': {'line': [{
      'display':full_name,
      'displayAscii':full_name,
      'e164Mask':e164mask,
      'callInfoDisplay':{'callerNumber':'true','redirectedNumber':'true'}, 
      'associatedEndusers':{'enduser':[{'userId':userid}]},
      'dirn':{'pattern':directory_number,'routePartitionName':'PT_'+location+'_DN'},'index':'1'}]},
    'securityProfileName':'Cisco Unified Client Services Framework - Standard SIP Non-Secure Profile',
    'sipProfileName':'Standard SIP Profile',
    'useTrustedRelayPoint':'Default','presenceGroupName':'Standard Presence group',
    'phoneTemplateName':'Standard Client Services Framework',})
  if result[0] == 200:
    res.append('The phone CSF'+userid.upper()+' has been added')  
  elif result[0] == 500:
    res.append('Error message when adding CSF'+userid.upper()+': '+result[1].faultstring+'\n')

  
  # Then we add a BOT (for Android) 
  result = client.service.addPhone({
    'name':'BOT'+userid.upper(),
    'class':'Phone',
    'description':'BOT Device for '+userid,
    'product':'Cisco Dual Mode for Android',
    'protocol':'SIP',
    'protocolSide':'User',
    'callingSearchSpaceName':'CSS-'+location+'-INT-Line',
    'devicePoolName':'DP-'+location,
    'commonPhoneConfigName':'Standard Common Phone Profile',
    'commonDeviceConfigName':location+'-COMMON-DEVICE',
    'mediaResourceListName':'MGL-'+location,
    'locationName':location+'-Location',
    'ownerUserName':userid,
    'primaryPhoneName':ip_phone,
    'lines': {'line': [{
      'display':full_name,
      'displayAscii':full_name,
      'e164Mask':e164mask,
      'callInfoDisplay':{'callerNumber':'true','redirectedNumber':'true'},
      'associatedEndusers':{'enduser':[{'userId':userid}]},
      'dirn':{'pattern':directory_number,'routePartitionName':'PT_'+location+'_DN'},'index':'1'}]},
    'securityProfileName':'Cisco Dual Mode for Android - Standard SIP Non-Secure Profile',
    'sipProfileName':'Standard SIP Profile',
    'useTrustedRelayPoint':'Default','presenceGroupName':'Standard Presence group',
    'phoneTemplateName':'Standard Dual Mode for Android',})
  if result[0] == 200:
    res.append('The phone BOT'+userid.upper()+' has been added')
  elif result[0] == 500:
    res.append('Error message when adding BOT'+userid.upper()+': '+result[1].faultstring)
 
  # Then we add a TCT (for iPhone) 
  result = client.service.addPhone({
    'name':'TCT'+userid.upper(),
    'class':'Phone',
    'description':'TCT Device for '+userid,
    'product':'Cisco Dual Mode for iPhone',
    'protocol':'SIP',
    'protocolSide':'User',
    'callingSearchSpaceName':'CSS-'+location+'-INT-Line',
    'devicePoolName':'DP-'+location,
    'commonPhoneConfigName':'Standard Common Phone Profile',
    'commonDeviceConfigName':location+'-COMMON-DEVICE',
    'mediaResourceListName':'MGL-'+location,
    'locationName':location+'-Location',
    'ownerUserName':userid,
    'primaryPhoneName':ip_phone,
    'lines': {'line': [{
      'display':full_name,
      'displayAscii':full_name,
      'e164Mask':e164mask,
      'callInfoDisplay':{'callerNumber':'true','redirectedNumber':'true'},
      'associatedEndusers':{'enduser':[{'userId':userid}]},
      'dirn':{'pattern':directory_number,'routePartitionName':'PT_'+location+'_DN'},'index':'1'}]},
    'securityProfileName':'Cisco Dual Mode for iPhone - Standard SIP Non-Secure Profile',
    'sipProfileName':'Standard SIP Profile',
    'useTrustedRelayPoint':'Default','presenceGroupName':'Standard Presence group',
    'phoneTemplateName':'Standard Dual Mode for iPhone',})
  if result[0] == 200:
    res.append('The phone TCT'+userid.upper()+' has been added')
  elif result[0] == 500:
    res.append('Error message when adding TCT'+userid.upper()+': '+result[1].faultstring)
      
  # And finally we add a TAB (for iPad) 
  result = client.service.addPhone({
    'name':'TAB'+userid.upper(),
    'class':'Phone',
    'description':'TAB Device for '+userid,
    'product':'Cisco Jabber for Tablet',
    'protocol':'SIP',
    'protocolSide':'User',
    'callingSearchSpaceName':'CSS-'+location+'-INT-Line',
    'devicePoolName':'DP-'+location,
    'commonPhoneConfigName':'Standard Common Phone Profile',
    'commonDeviceConfigName':location+'-COMMON-DEVICE',
    'mediaResourceListName':'MGL-'+location,
    'locationName':location+'-Location',
    'ownerUserName':userid,
    'primaryPhoneName':ip_phone,
    'lines': {'line': [{
      'display':full_name,
      'displayAscii':full_name,
      'e164Mask':e164mask,
      'callInfoDisplay':{'callerNumber':'true','redirectedNumber':'true'},
      'associatedEndusers':{'enduser':[{'userId':userid}]},
      'dirn':{'pattern':directory_number,'routePartitionName':'PT_'+location+'_DN'},'index':'1'}]},
    'securityProfileName':'Cisco Jabber for Tablet - Standard SIP Non-Secure Profile',
    'sipProfileName':'Standard SIP Profile',
    'useTrustedRelayPoint':'Default','presenceGroupName':'Standard Presence group',
    'phoneTemplateName':'Standard Jabber for Tablet',})
  if result[0] == 200:
    res.append('The phone TAB'+userid.upper()+' has been added')
  elif result[0] == 500:
    res.append('Error message when adding TAB'+userid.upper()+': '+result[1].faultstring)

  return res
  
def removePhone(userid,ip_phone,client):
  
  res =[]

  try:
  # First we remove the physical phone
    result = client.service.removePhone(name=ip_phone)
    if result[0] == 200:
      res.append('The phone '+ip_phone+' has been removed')
    elif result[0] == 500: 
      res.append('There is probably no '+ip_phone+' device.') 
  except:
    res.append('There was an issue removing '+ip_phone+'. The error message is '+str(sys.exc_info()[1]))     
  
  # Then we remove the other phones
  try:
    result = client.service.removePhone(name='CSF'+userid.upper())
    if result[0] == 200:
      res.append('The phone CSF'+userid.upper()+' has been removed')
    elif result[0] == 500:
      res.append('There is probably no CSF'+userid.upper()+' device.')
  except:
    res.append('There was an issue removing CSF'+userid.upper()+'. The error message is '+str(sys.exc_info()[1]))       

  try:
    result = client.service.removePhone(name='BOT'+userid.upper())
    if result[0] == 200:
      res.append('The phone BOT'+userid.upper()+' has been removed')
    elif result[0] == 500:
      res.append('There is probably no BOT'+userid.upper()+' device.')   
  except:
    res.append('There was an issue removing BOT'+userid.upper()+'. The error message is '+str(sys.exc_info()[1]))

  try:
    result = client.service.removePhone(name='TAB'+userid.upper())
    if result[0] == 200:
      res.append('The phone TAB'+userid.upper()+' has been removed')
    elif result[0] == 500:
      res.append('There is probably no TAB'+userid.upper()+' device.') 
  except:
    res.append('There was an issue removing TAB'+userid.upper()+'. The error message is '+str(sys.exc_info()[1]))

  try:
    result = client.service.removePhone(name='TCT'+userid.upper())
    if result[0] == 200:
      res.append('The phone TCT'+userid.upper()+' has been removed')
    elif result[0] == 500:
      res.append('There is probably no TCT'+userid.upper()+' device.')
  except:
    res.append('There was an issue removing TCT'+userid.upper()+'. The error message is '+str(sys.exc_info()[1]))

  return res


if __name__ == "__main__":
  main()  
