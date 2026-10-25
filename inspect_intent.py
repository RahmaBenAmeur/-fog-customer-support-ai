import joblib

MODEL_PATH = "Intent_Classification/intent_classifier.pkl"

model = joblib.load(MODEL_PATH)

texts = [
    "My order has not arrived",
    "I want to cancel my order",
    "I want to return this product",
    "Where is my package?",
    "I was charged twice",
    "I want a refund"
]

print("🤖 Intent Classification Test\n")

for text in texts:
    prediction = model.predict([text])[0]
    probabilities = model.predict_proba([text])[0]

    classes = model.classes_
    confidence = max(probabilities)

    print(f"Text: {text}")
    print(f"Intent: {prediction}")
    print(f"Confidence: {confidence:.2f}")

    # Show top 3 predictions
    top_indices = probabilities.argsort()[-3:][::-1]

    print("Top predictions:")
    for i in top_indices:
        print(f"  {classes[i]} → {probabilities[i]:.2f}")

    print("-" * 50)