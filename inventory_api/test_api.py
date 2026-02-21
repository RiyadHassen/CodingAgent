import requests
import time

BASE_URL = "http://localhost:8000"

def test_api():
    print("Waiting for API to start...")
    time.sleep(5)  # Give the server some time to start

    # Test root endpoint
    try:
        response = requests.get(f"{BASE_URL}/")
        response.raise_for_status()
        print(f"Root endpoint response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to root endpoint: {e}")
        return

    # Test creating an item
    print("\nCreating an item...")
    item_data = {"name": "Laptop", "description": "Powerful laptop", "price": 1200.0, "quantity": 10}
    response = requests.post(f"{BASE_URL}/items/", json=item_data)
    print(f"Create item response: {response.json()}")
    item_id = response.json().get("id")
    assert response.status_code == 200
    assert item_id is not None

    # Test listing items
    print("\nListing items...")
    response = requests.get(f"{BASE_URL}/items/")
    print(f"List items response: {response.json()}")
    assert response.status_code == 200
    assert len(response.json()) > 0

    # Test reading a specific item
    print(f"\nReading item with ID: {item_id}...")
    response = requests.get(f"{BASE_URL}/items/{item_id}")
    print(f"Read item response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["name"] == "Laptop"

    # Test updating an item
    print(f"\nUpdating item with ID: {item_id}...")
    updated_item_data = {"name": "Gaming Laptop", "description": "Ultra-powerful gaming laptop", "price": 1500.0, "quantity": 8}
    response = requests.put(f"{BASE_URL}/items/{item_id}", json=updated_item_data)
    print(f"Update item response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["name"] == "Gaming Laptop"

    # Test deleting an item
    print(f"\nDeleting item with ID: {item_id}...")
    response = requests.delete(f"{BASE_URL}/items/{item_id}")
    print(f"Delete item response status code: {response.status_code}")
    assert response.status_code == 204

    # Verify item is deleted
    print(f"\nVerifying item with ID: {item_id} is deleted...")
    response = requests.get(f"{BASE_URL}/items/{item_id}")
    print(f"Verify delete response status code: {response.status_code}")
    assert response.status_code == 404

    print("\nAll API tests passed!")

if __name__ == "__main__":
    test_api()
