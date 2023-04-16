import requests

# Replace the URL below with your Heroku app's URL
base_url = "https://qrfood.herokuapp.com"

item_id = "fd63405e-d6f8-4135-ac81-627c915a4a36"  # Replace with the actual item ID
qr_code_url = f"{base_url}/food_items/{item_id}/qrcode"

qr_code_response = requests.get(qr_code_url)

# Save the QR code image to a local file
with open(f"{item_id}.png", "wb") as f:
    f.write(qr_code_response.content)

print(f"QR code saved as {item_id}.png")
