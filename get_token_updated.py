'''
Modified to work with the latest login function on MarketWatch.
'''


import requests
import json
 
postURL = 'https://id.marketwatch.com/auth/submitlogin.json'
cookies = {}
 
s = requests.Session()
username = 'foo@bar.com'
password = 'hunter2'
 
print "\nAttempting to log in... "
 
userdata = {
                "username": username,
                "password": password
            }
s.get('https://id.marketwatch.com/')
r = s.get('https://id.marketwatch.com/auth/submitlogin.json', params = userdata)
s.get(json.loads(r.text)['url'])
print s.cookies
 
if (s.get('http://www.marketwatch.com/user/login/status').url != \
"http://www.marketwatch.com/my"):
        print "You entered the wrong username / password. Try again!"
 
print "\nSuccessfully logged in!"
