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

def sasl_connect(username):
  """Connects to LDAP to retrieve the user phone number and 
  extension 
  """  
  connect = ldap.initialize('ldap://172.20.130.254')
  print "Connecting to LDAP to extract the user extension"
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
    print "Username or password is incorrect."
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

 
def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

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



def cucm_provisioning(filename):
  """Connects to CUCM, builds the config including 
  lines, phones and user association
  """ 

  # First we connect to the AXL API
  # Logging for debugging
  logging.basicConfig(level=logging.INFO)
  #logging.getLogger('suds.client').setLevel(logging.DEBUG)
  logging.getLogger('suds.client').setLevel(logging.CRITICAL)
  #logging.getLogger('suds.transport').setLevel(logging.DEBUG)
  #logging.getLogger('suds.xsd.schema').setLevel(logging.CRITICAL)
  #logging.getLogger('suds.wsdl').setLevel(logging.CRITICAL)
  print "Connecting to myphone.central1.com to add the line and phones for the user"
 
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

  # Opening the file containing the users details 
  in_file = open(filename, 'r')
  config = in_file.readlines()
  in_file.close()

  #Generating a file that contains the provisioning results
  User_file = open('cucm_user_provisioning_results.txt', 'w')
  
  
  for line in config[1:]:
    # We go through the list of the associated phones and add the ones missing
    line=line.replace('\n','')
    fields = line.split(',')
    userid = fields[0]
    ip_phone = fields[1]
    ip_phone_type = fields[2]
    # First we want to check that the user is in AD and that he is an extension
    result = sasl_connect(userid)

    if not result:
      print 'This user',userid,'has not been found in AD'
      continue
    elif len(result[0][1]) != 4:
      print 'This user',userid,'is missing some info in LDAP, probably his extension (ipPhone) is not set in AD'
      continue

    
    directory_number = ''.join(result[0][1]['ipPhone'])
    e164mask = (''.join(result[0][1]['telephoneNumber'])).replace('-','')
    full_name = ''.join(result[0][1]['name']) 
    if directory_number == '':  
      print 'This user',userid,'has no extension set in the ipPhone field in AD'
    elif directory_number != '' and e164mask == '':
      print 'This user',userid,'has no extension set in the telephoneNumber field in AD'
  
    # Do we need to create the line?
    #answer = query_yes_no('The user '+userid+' is set with the extension '+directory_number+'. Is this a new extension in CUCM?')

    #We add the line and if it exists already, it will error out and move on to the next step:
    addLine(userid,full_name,directory_number,User_file,client)
    # We create the phones
    addPhone(userid,full_name,directory_number,ip_phone,ip_phone_type,e164mask,User_file,client) 
    # We finally associate the user with his phones
    result = client.service.updateUser(__inject={'msg':updateUser(userid,ip_phone)})
    if result[0] == 200:
      print 'All the phones were associated with user: '+userid
      User_file.write('All the phones were associated with user: '+userid+'\n')
    elif result[0] == 500:
      print 'Error message when associating the phones for '+userid+': '+result[1].faultstring 
      User_file.write('Error message when associating the phones for '+userid+': '+result[1].faultstring +'\n')

    
  
  # Verification  
  in_file = open(filename, 'r')
  config = in_file.readlines()
  in_file.close()

  print 'Results:'
  print '='*122+'\b'
  print ("{0:24}{1:24}{2:24}{3:24}{4:24}".format('|| USER ID','|| CONTROLLED PROFILE 1 ||',' CONTROLLED PROFILE 2 ||',' CONTROLLED PROFILE 3 ||',' CONTROLLED PROFILE 4 ||'))
  print '='*122+'\b' 
  User_file.write('Results:\n')
  User_file.write('='*122+'\n')
  User_file.write("{0:24}{1:24}{2:24}{3:24}{4:24}".format('|| USER ID','|| CONTROLLED PROFILE 1 ||',' CONTROLLED PROFILE 2 ||',' CONTROLLED PROFILE 3 ||',' CONTROLLED PROFILE 4 ||')+'\n')
  User_file.write('='*122+'\n') 

  for line in config[1:]:
    try:
      # Getting a user detail
      line=line.replace('\n','')
      fields = line.split(',')      
      userid = fields[0]    
      result = client.service.getUser(userid=userid)
      print ("{0:24}{1:24}{2:24}{3:24}{4:24}{5:2}".format('|| '+result[1]['return']['user']['associatedDevices']['device'][0],'|| ' \
        +result[1]['return']['user']['associatedDevices']['device'][1],'|| '\
        +result[1]['return']['user']['associatedDevices']['device'][2],'|| '\
        +result[1]['return']['user']['associatedDevices']['device'][3],'|| '\
        +result[1]['return']['user']['associatedDevices']['device'][4],'||'))
      User_file.write("{0:24}{1:24}{2:24}{3:24}{4:24}{5:2}".format('|| '+result[1]['return']['user']['associatedDevices']['device'][0],'|| ' \
        +result[1]['return']['user']['associatedDevices']['device'][1],'|| '\
        +result[1]['return']['user']['associatedDevices']['device'][2],'|| '\
        +result[1]['return']['user']['associatedDevices']['device'][3],'|| '\
        +result[1]['return']['user']['associatedDevices']['device'][4],'||')+'\n')

     
      #print 'The devices associated with '+userid+' are:'
      #for device in result[1]['return']['user']['associatedDevices']['device']:
      #  print device
    except:
      print 'There is probably no associated devices for '+userid+'. The error message is '+str(sys.exc_info()[0])      
      User_file.write('There is probably no associated devices for '+userid+'. The error message is '+str(sys.exc_info()[0])+'\n')
  print '='*122+'\b'
  User_file.write('='*122+'\n') 
  print 'Results were saved in cucm_user_provisioning_results.txt'

def addLine(userid,full_name,directory_number,User_file,client):

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
    print 'The extension '+directory_number+' has been added'
    User_file.write('The extension '+directory_number+' has been added\n')
  elif result[0] == 500:
    print 'Error message when adding Line '+directory_number+': '+result[1].faultstring
    User_file.write('Error message when adding Line '+directory_number+': '+result[1].faultstring+'\n')
 
    
  
def addPhone(userid,full_name,directory_number,ip_phone,ip_phone_type,e164mask,User_file,client):

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
    print 'The phone '+ip_phone+' has been added'
    User_file.write('The phone '+ip_phone+' has been added\n')    
  elif result[0] == 500:
    print 'Error message when adding '+ip_phone+': '+result[1].faultstring 
    User_file.write('Error message when adding '+ip_phone+': '+result[1].faultstring+'\n')


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
    print 'The phone CSF'+userid.upper()+' has been added'
    User_file.write('The phone CSF'+userid.upper()+' has been added\n')    
  elif result[0] == 500:
    print 'Error message when adding CSF'+userid.upper()+': '+result[1].faultstring 
    User_file.write('Error message when adding CSF'+userid.upper()+': '+result[1].faultstring+'\n')
  
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
    print 'The phone BOT'+userid.upper()+' has been added'
    User_file.write('The phone BOT'+userid.upper()+' has been added\n')    
  elif result[0] == 500:
    print 'Error message when adding BOT'+userid.upper()+': '+result[1].faultstring 
    User_file.write('Error message when adding BOT'+userid.upper()+': '+result[1].faultstring+'\n')
 
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
    print 'The phone TCT'+userid.upper()+' has been added'
    User_file.write('The phone TCT'+userid.upper()+' has been added\n')
  elif result[0] == 500:
    print 'Error message when adding TCT'+userid.upper()+': '+result[1].faultstring 
    User_file.write('Error message when adding TCT'+userid.upper()+': '+result[1].faultstring+'\n')
      
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
    print 'The phone TAB'+userid.upper()+' has been added'
    User_file.write('The phone TAB'+userid.upper()+' has been added\n')
  elif result[0] == 500:
    print 'Error message when adding TAB'+userid.upper()+': '+result[1].faultstring 
    User_file.write('Error message when adding TAB'+userid.upper()+': '+result[1].faultstring+'\n')
 

  
def main():
  # This is program reads data from CSV files
  # to create phones and associates user(s) with their phones  
  args = sys.argv[1:]
  if (len(args) <1):
    print 'usage: python cucm_add_user.py somefilename.csv'
    print 'The csv content should look like this (one user per line):'
    print 'user,physical phone,type of phone'
    print 'fbobes,SEP01888867530E,7942'
    print 'claw,SEP01888867530F,7962'
    sys.exit(1)
  
  input_file = args[0]
  
 
  cucm_provisioning(input_file)

if __name__ == "__main__":
  main()  
