from playwright.sync_api import sync_playwright
from transformers import pipeline
from langdetect import detect
import csv
import time
import os
import random

# Change the search queries Keyword according to your own needs
SEARCH_QUERIES = [
    "Kedarnath experience", "CharDham Yatra", "Kedarnath crowd", "visited Kedarnath",
    "CharDham issues", "Kedarnath", "CharDhamYatra", "Badrinath experience",
    "Kedarnath Uttarakhand", "CharDham travel review", "Chardham review", "Kedarnath Travel review", "Badrinath Travel review", "GangotriDham", "GangotriVlog", "Kedarnath Vlog",
    "Badrinath Uttrakhand", "Travel Uttrakhand", "Kedarnath Pahad", "Tungnath Travel",
    "Kedarnath Registration", "Chardham Registration"
]

MAX_TWEETS_PER_QUERY = 200
MAX_SCROLLS = 100
OUTPUT_CSV = "tweets_with_sentiment_gender_age.csv"

import torch
from transformers import pipeline

device = 0 if torch.cuda.is_available() else -1  # ✅ Use GPU if available

    zero_shot_classifier = pipeline( 
    "zero-shot-classification",
    model="facebook/bart-large-mnli",
    device=device
)   

gender_labels = ["male", "female"]
age_labels = ["teenager", "in their 20s", "in their 30s", "in their 40s", "in their 50s", "senior"]
sentiment_labels = ["positive", "neutral", "negative"]

def detect_language(text):
    try:
        return detect(text)
    except:
        return "unknown"

def predict_all(text):
    try:
        sentiment = zero_shot_classifier(text, sentiment_labels)['labels'][0]
        gender = zero_shot_classifier(text, gender_labels)['labels'][0]
        age = zero_shot_classifier(text, age_labels)['labels'][0]
        return sentiment, gender, age
    except:
        return "unknown", "unknown", "unknown"

def scrape_query(browser, keyword, writer, fhandle):
    context = browser.new_context(storage_state="x_session.json")
    page = context.new_page()
    query_encoded = keyword.replace(" ", "%20")
    search_url = f"https://x.com/search?q={query_encoded}&src=typed_query&f=top"
    print(f"\n🔍 Searching for: {keyword}")

    try:
        page.goto(search_url, timeout=30000)
    except:
        print(f"⚠️ Timeout or load failure on query '{keyword}', skipping...")
        context.close()
        return

    page.wait_for_timeout(5000)

    tweet_texts = set()
    collected = 0
    scrolls = 0

    while collected < MAX_TWEETS_PER_QUERY and scrolls < MAX_SCROLLS:
        articles = page.locator("article")
        count = articles.count()
        if count == 0:
            scrolls += 1
            page.mouse.wheel(0, 3000)
            time.sleep(2)
            continue

        for i in range(count):
            try:
                article = articles.nth(i)
                tweet_text = article.locator("div[data-testid='tweetText']").inner_text()
                username = article.locator("div[dir='ltr'] span").first.inner_text()
                timestamp = article.locator("time").get_attribute("datetime")

                if tweet_text in tweet_texts:
                    continue

                language = detect_language(tweet_text)
                sentiment, gender, age = predict_all(tweet_text)

                tweet_texts.add(tweet_text)
                writer.writerow({
                    "keyword": keyword,
                    "tweet": tweet_text,
                    "timestamp": timestamp,
                    "username": username,
                    "gender": gender,
                    "age": age,
                    "sentiment": sentiment,
                    "language": language
                })
                fhandle.flush()  # ⬅️ immediately save to CSV
                collected += 1

                print(f"✅ {collected}: {tweet_text[:80]}...")

                if collected >= MAX_TWEETS_PER_QUERY:
                    break

            except Exception as e:
                continue

        scrolls += 1
        page.mouse.wheel(0, 3000)
        time.sleep(random.uniform(1.5, 2.5))

    context.close()

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        file_exists = os.path.isfile(OUTPUT_CSV)
        with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
            fieldnames = ["keyword", "tweet", "timestamp", "username", "gender", "age", "sentiment", "language"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()

            for keyword in SEARCH_QUERIES:
                scrape_query(browser, keyword, writer, f)
                print(f"📦 Finished collecting for '{keyword}'")
                time.sleep(2)

        browser.close()
        print(f"\n🎉 All tweets saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
