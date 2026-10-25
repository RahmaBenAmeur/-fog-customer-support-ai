from database.extractor import extract_order_id

texts = [
    "Where is my order ORD001?",
    "I want to cancel ORD002",
    "What happened to order ORD003?",
    "My order has not arrived"
]

for text in texts:
    order_id = extract_order_id(text)

    print(f"Text: {text}")
    print(f"Order ID: {order_id}")
    print("-" * 40)