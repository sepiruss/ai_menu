import requests
import json

# Test cart endpoint
session_token = "dXv9Wq2bvh87vpC1zmAqrZ8LHa4EK9InO9z_F-mouAk"
base_url = "http://localhost:8000/api/v1/public"

headers = {
    "X-Session-Token": session_token,
    "Content-Type": "application/json"
}

# Add item to cart
print("Testing add to cart...")
response = requests.post(
    f"{base_url}/cart/items",
    headers=headers,
    json={"menu_item_id": 14, "quantity": 2, "selected_options": []}
)
print(f"Add to cart: {response.status_code} - {response.text}")

# Get cart
print("\nTesting get cart...")
response = requests.get(f"{base_url}/cart", headers=headers)
print(f"Get cart: {response.status_code} - {response.text}")

# Create order
print("\nTesting create order...")
response = requests.post(
    f"{base_url}/orders",
    headers=headers,
    json={"idempotency_key": "test-123", "customer_note": "Test order"}
)
print(f"Create order: {response.status_code} - {response.text}")

# Get orders
print("\nTesting get orders...")
response = requests.get(f"{base_url}/orders", headers=headers)
print(f"Get orders: {response.status_code} - {response.text}")