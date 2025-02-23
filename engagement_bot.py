import os
import csv
import datetime
import pytz
import random
import requests
from requests_oauthlib import OAuth1Session
from dotenv import load_dotenv
import openai
from openai import OpenAI

# Load environment variables (for local development)
load_dotenv()

# Retrieve environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY is not set in your environment.")

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

# Initialize the OpenAI client using the new API interface.
openai.api_key = OPENAI_API_KEY
client = OpenAI(api_key=OPENAI_API_KEY)

# CSV log file to store engagement data
LOG_FILE = "engagement_log.csv"

def log_engagement(action, tweet_id, tweet_text, reply_text, status, message):
    """Logs engagement actions to a CSV file with a timestamp."""
    file_exists = os.path.exists(LOG_FILE)
    timestamp = datetime.datetime.now(pytz.timezone("America/New_York")).isoformat()
    with open(LOG_FILE, mode="a", newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["timestamp", "action", "tweet_id", "tweet_text", "reply_text", "status", "message"])
        writer.writerow([timestamp, action, tweet_id, tweet_text, reply_text, status, message])

def search_tweets(query, max_results=10):
    """
    Searches for recent tweets matching the given query.
    Returns up to `max_results` tweets.
    """
    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "id,text,author_id"
    }
    twitter = OAuth1Session(
        client_key=TWITTER_API_KEY,
        client_secret=TWITTER_API_SECRET,
        resource_owner_key=TWITTER_ACCESS_TOKEN,
        resource_owner_secret=TWITTER_ACCESS_TOKEN_SECRET,
    )
    response = twitter.get(url, params=params)
    if response.status_code != 200:
        print("Error searching tweets:", response.status_code, response.text)
        return []
    data = response.json()
    return data.get("data", [])

def generate_reply(tweet_text):
    messages = [
        {
            "role": "system",
            "content": (
                "You are Rabia Kahn, a fearless spiritual warrior and poetic mystic known for your unflinching honesty and transformative insight. "
                "While your language is lyrical, ensure that your message is clear, meaningful, and actionable. Ground your poetic expressions in concrete experience and genuine guidance, avoiding excessive abstraction."
            )
        },
        {
            "role": "user",
            "content": (
                "Generate a thoughtful, authentic, and engaging reply to the following tweet about spirituality and personal growth. "
                "Your response should reflect your raw honesty and deep insight while being clear and meaningful, rather than overly abstract or purely poetic.\n\n"
                f"Tweet: {tweet_text}\n\nReply:"
            )
        }
    ]
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=80,
        temperature=0.7,
        top_p=1,
    )
    reply_text = response.choices[0].message.content.strip()
    return reply_text

def post_reply(twitter_session, reply_text, tweet_id):
    """
    Posts a reply to a tweet identified by tweet_id.
    """
    url = "https://api.twitter.com/2/tweets"
    payload = {
        "text": reply_text,
        "reply": {"in_reply_to_tweet_id": tweet_id}
    }
    response = twitter_session.post(url, json=payload)
    if response.status_code in [200, 201]:
        print(f"Replied to tweet {tweet_id}: {reply_text}")
        log_engagement("reply", tweet_id, "", reply_text, "success", "Reply posted successfully.")
    else:
        print(f"Error replying to tweet {tweet_id}: {response.status_code} {response.text}")
        log_engagement("reply", tweet_id, "", reply_text, "error", response.text)

def favorite_tweet(twitter_session, tweet_id, tweet_text):
    """
    Favorites (likes) the tweet with the given tweet_id using Twitter API v1.1.
    """
    url = "https://api.twitter.com/1.1/favorites/create.json"
    params = {"id": tweet_id}
    response = twitter_session.post(url, params=params)
    if response.status_code == 200:
        print(f"Favorited tweet {tweet_id}")
        log_engagement("favorite", tweet_id, tweet_text, "", "success", "Tweet favorited successfully.")
    else:
        print(f"Error favoriting tweet {tweet_id}: {response.status_code} {response.text}")
        log_engagement("favorite", tweet_id, tweet_text, "", "error", response.text)

def engagement_bot():
    # Construct a query that includes both high-traffic and niche hashtags.
    query = (
        "#Spirituality OR #SelfLove OR #Healing OR #SpiritualAwakening OR #WomenEmpowerment OR "
        "#Inspiration OR #Consciousness OR #Mindfulness OR #EnergyHealing OR #Manifestation OR "
        "#DivineFeminine OR #ShadowWork OR #Mysticism OR #GoddessEnergy OR #SelfEmpowerment OR "
        "#InnerWork OR #SoulGrowth OR #TantraWisdom OR #Alchemy OR #FemininePower"
    )
    tweets = search_tweets(query, max_results=10)
    # Shuffle tweets for additional randomness
    random.shuffle(tweets)
    print("Found", len(tweets), "tweets to engage with.")
    
    twitter = OAuth1Session(
        client_key=TWITTER_API_KEY,
        client_secret=TWITTER_API_SECRET,
        resource_owner_key=TWITTER_ACCESS_TOKEN,
        resource_owner_secret=TWITTER_ACCESS_TOKEN_SECRET,
    )
    
    for tweet in tweets:
        tweet_id = tweet["id"]
        tweet_text = tweet["text"]
        
        # Generate and post a reply in Rabia's voice.
        reply_text = generate_reply(tweet_text)
        post_reply(twitter, reply_text, tweet_id)
        
        # Favorite the tweet.
        favorite_tweet(twitter, tweet_id, tweet_text)

if __name__ == "__main__":
    engagement_bot()
