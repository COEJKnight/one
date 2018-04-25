
# MAX Validation Process

### 1. Generate certificate from the MAX pfx file 

Unpack a `.pfx` (file that holds the certificate) file from MAX. We'll need to generate a `.pem` file. 

To generate a `.pem` file on a Mac/Linux:
```
openssl pkcs12 -in <pfx filepath>.pfx -out <pem filepath>.pem -nodes
```

On Windows:
```
cd C:\Program Files\OpenSSL-Win64\bin
openssl pkcs12 -in <pfx filepath>.pfx -out <pem filepath>.pem -nodes
```


### 2. Login to MAX using certificate  
We can use requests in order to get a ticket back from max to use in the max login endpoint for broker.

```
import requests
import re

# Attach certificate file to the request to MAX
req = requests.get('https://piv.max.gov/cas/login?service=https://broker.usaspending.gov/', 
				  cert=('/<filepath>/max_cert.pem'))

regex = re.compile('ticket=(?P<ticket>[a-zA-Z0-9.-]*)')

ticket_search = regex.search(max_req.url)
ticket = ticket_search.group('ticket')
```

**Terms**

- `service`: Tells MAX what site we want authenticated so that MAX can return return the appropriate login data. Specifying this service will give us the ticket information to determined if the user sucessfully logged in to max. 
- `ticket`: Represents the verifcation that a user sucessfully logged into max. The ticket comes from the url the Max login service sends. And example of the url is  `https://broker.usaspending.gov/?ticket=<ticket hash>-login.max.gov`.


### 3. Log into Broker
Now that we have the ticket we can access the `max/login` endpoint on broker. Both the service and ticket are required to verify the user's login through CAS.

Endpoint: `https://<broker api>.usaspending.gov/v1/max_login/`

Request Body:
```
{
    "ticket":"<ticket>",
    "service":"<service>"
}
```


Code:

```
req_body = {
    "ticket": ticket,
    "service": "https://broker.usaspending.gov/"
}

requests.post('https://broker-api.usaspending.gov/v1/max_login/', 
				json=req_body)
```

**Terms**

- `service`: Service matches the service specified in Step 2. In this case since our services is `https://broker.usaspending.gov/`.
- `https://broker-api.usaspending.gov/v1/max_login/`: The endpoint for MAX verification on broker. This endpoint will verify through CAS that the user successfully logged on to max and will return information about the user from MAX that broker will then add to the user's profile in the broker database. 

Data Broker stores the following information from MAX:

- Email address
- Group list (User Affiliations and/or website admin status)
- First name
- Middle name
- Last name

Using name information MAX sends, broker can link a MAX login with a user in the database. Broker will login the user and create a session for a user.

### 4. Access the API through a session token
If the request runs sucessfully, you should be able to access the API through a session token. To check you can make the following request to check whether you're in a session:

```
headers_session = {'x-session-id': '<session token>'}

session_req = requests.get('https://broker-api.usaspending.gov/v1/session/', headers=headers_session)

print(req.text)

# Returns {"status": "True"} means user is logged in

```

### Terms
- `session`: Data storage where a user's information is stored outside the database so that the application can identify which user is using the site.
- `session token`: A unique identifier that the application can verify that user sending the request is logged in. Matches the session token to a session on the server. 

# Areas for Improvement

1. The Max certificate I tested did not contain the any items under `maxAttribute:GroupList` and therefore threw an error when logging in. I believe this is an issue with the certificate I was given.
2. Currently, no endpoints return the session token. The frontend uses cookies to store this information and adds it to request headers. We will need to decide how we would like to return this value to the user and if we should create a separate endpoint. Using a separate endpoint can streamline the login process the API user. 



