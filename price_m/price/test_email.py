import sys
import os

# Set up path to ensure correct module imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.core.notifier import send_price_drop_email

def test():
    print("Testing sending a simulated email...")
    send_price_drop_email(
        product_name="Test Product 123",
        url="https://example.com/test-product",
        old_price=1000.0,
        new_price=800.0,
        receiver_email="test_user@example.com"
    )

if __name__ == "__main__":
    test()
