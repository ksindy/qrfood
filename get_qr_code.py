import requests
import os

# Replace this with the URL of your FastAPI app
base_url = "https://qrfood.herokuapp.com/"

# Send a GET request to the /create_qr_code/ endpoint
response = requests.get(f"{base_url}/create_qr_code/")

# Check if the response is successful
if response.status_code == 200:
    # Save the QR code image to a file
    with open("qr_code.png", "wb") as f:
        f.write(response.content)
    print("QR code saved as qr_code.png")
else:
    print(f"Error: {response.status_code}, {response.text}")
