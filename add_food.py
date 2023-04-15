import requests

# Add a new food item
url = "http://localhost:8000/food_items/"

data = {
    "food": "Milk",
    "expiration_date": "2023-04-22",
    "reminder_date": "2023-04-22",
    "suggested_expiration_date": "2123-04-21"
}

response = requests.post(url, json=data)

print(response.status_code)
response_data = response.json()
print(response_data)

# Get the QR code for the new food item
item_id = response_data["id"]
qr_code_url = f"http://localhost:8000/food_items/{item_id}/qrcode"

qr_code_response = requests.get(qr_code_url)

with open(f"{item_id}.png", "wb") as f:
    f.write(qr_code_response.content)

print(f"QR code saved as {item_id}.png")
