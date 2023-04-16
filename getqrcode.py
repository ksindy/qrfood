import requests

# Replace the URL below with your Heroku app's URL
base_url = "https://qrfood.herokuapp.com"

item_id = "740237b3-c448-4dc6-9186-10843d548745"  # Replace with the actual item ID
qr_code_url = f"{base_url}/food_items/{item_id}/qrcode"

qr_code_response = requests.get(qr_code_url)

# Save the QR code image to a local file
with open(f"{item_id}.png", "wb") as f:
    f.write(qr_code_response.content)

print(f"QR code saved as {item_id}.png")
