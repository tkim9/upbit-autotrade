import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 1. get upbit chart, 30days


import json
import pyupbit
import uuid
import jwt
import requests


access_key = os.getenv("UPBIT_OPEN_API_ACCESS_KEY")
secret_key = os.getenv("UPBIT_OPEN_API_SECRET_KEY")
# upbit = pyupbit.Upbit(access, secret)
# current_cash = upbit.get_balance("KRW")
# current_ada = upbit.get_balance("ADA")

# Generate the JWT as shown in Step 1
payload = {
    "access_key": access_key,
    "nonce": str(uuid.uuid4())
}
encoded_jwt = jwt.encode(payload, secret_key, algorithm="HS256")
authorization_header = f"Bearer {encoded_jwt}"

# Define the API endpoint and headers
url = "https://api.upbit.com/v1/accounts"
headers = {"Authorization": authorization_header}

# Send the GET request
response = requests.get(url, headers=headers)

# Check the response
if response.status_code == 200:
    portfolio = response.json()
    for item in portfolio:
        print(f"Currency: {item['currency']}, Balance: {item['balance']}, Locked: {item['locked']}")
else:
    print(f"Error: {response.status_code}, {response.text}")
