from transformers import pipeline

MODEL_PATH = "Sentiment_Classification/amazon_distilbert"

sentiment = pipeline(
    "sentiment-analysis",
    model=MODEL_PATH,
    tokenizer=MODEL_PATH
)

texts = [
    "I am very happy with my order!",
    "My order has not arrived for two weeks.",
    "The service was terrible."
]

for text in texts:
    result = sentiment(text)[0]

    print(f"\nText: {text}")
    print(f"Sentiment: {result['label']}")
    print(f"Confidence: {result['score']:.2f}")