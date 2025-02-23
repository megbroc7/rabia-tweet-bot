import os
import csv
import datetime
import pytz
import random
from typing import List, Dict
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session
from openai import OpenAI
import logging
import time
from ratelimit import limits, sleep_and_retry

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
LOG_FILE = "engagement_log.csv"
TIMEZONE = pytz.timezone("America/New_York")
TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"
TWITTER_POST_URL = "https://api.twitter.com/2/tweets"
TWITTER_FAVORITE_URL = "https://api.twitter.com/1.1/favorites/create.json"
QUERY = (
    "#Spirituality OR #SelfLove OR #Healing OR #SpiritualAwakening OR #WomenEmpowerment OR "
    "#Inspiration OR #Consciousness OR #Mindfulness OR #EnergyHealing OR #Manifestation OR "
    "#DivineFeminine OR #ShadowWork OR #Mysticism OR #GoddessEnergy OR #SelfEmpowerment OR "
    "#InnerWork OR #SoulGrowth OR #TantraWisdom OR #Alchemy OR #FemininePower"
)

# Rate limit configurations
TWITTER_SEARCH_RATE = 180 / 900  # 180 requests per 15 min (900 seconds)
TWITTER_POST_RATE = 50 / 900    # 50 requests per 15 min
OPENAI_RATE = 3 / 60            # 3 requests per minute

@sleep_and_retry
@limits(calls=180, period=900)
def rate_limited_search(twitter_session, query: str, max_results: int) -> List[Dict]:
    params = {"query": query, "max_results": max_results, "tweet.fields": "id,text,author_id"}
    response = twitter_session.get(TWITTER_SEARCH_URL, params=params)
    response.raise_for_status()
    return response.json().get("data", [])

@sleep_and_retry
@limits(calls=50, period=900)
def rate_limited_post(twitter_session, payload: Dict):
    return twitter_session.post(TWITTER_POST_URL, json=payload)

@sleep_and_retry
@limits(calls=3, period=60)
def rate_limited_openai(client, messages: List[Dict]) -> str:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=80,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

class TwitterBot:
    def __init__(self):
        self._validate_env_vars()
        self.twitter = OAuth1Session(
            client_key=os.getenv("TWITTER_API_KEY"),
            client_secret=os.getenv("TWITTER_API_SECRET"),
            resource_owner_key=os.getenv("TWITTER_ACCESS_TOKEN"),
            resource_owner_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        )
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _validate_env_vars(self):
        required_vars = [
            "OPENAI_API_KEY", "TWITTER_API_KEY", "TWITTER_API_SECRET",
            "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_TOKEN_SECRET"
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    def _log_engagement(self, action: str, tweet_id: str, tweet_text: str, 
                       reply_text: str, status: str, message: str):
        try:
            file_exists = os.path.exists(LOG_FILE)
            timestamp = datetime.datetime.now(TIMEZONE).isoformat()
            with open(LOG_FILE, mode="a", newline='', encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                if not file_exists:
                    writer.writerow(["timestamp", "action", "tweet_id", "tweet_text", 
                                   "reply_text", "status", "message"])
                writer.writerow([timestamp, action, tweet_id, tweet_text, 
                               reply_text, status, message])
        except Exception as e:
            logger.error(f"Failed to log engagement: {e}")

    def search_tweets(self, query: str, max_results: int = 10) -> List[Dict]:
        try:
            return rate_limited_search(self.twitter, query, max_results)
        except Exception as e:
            logger.error(f"Error searching tweets: {e}")
            return []

    def generate_reply(self, tweet_text: str) -> str:
        try:
            messages = [
                {"role": "system", "content": (
                    "You are Rabia Kahn, a fearless spiritual warrior and poetic mystic known for "
                    "unflinching honesty and transformative insight. Craft clear, meaningful, and "
                    "actionable responses grounded in concrete experience, avoiding excessive abstraction."
                )},
                {"role": "user", "content": f"Tweet: {tweet_text}\n\nReply:"}
            ]
            return rate_limited_openai(self.openai_client, messages)
        except Exception as e:
            logger.error(f"Error generating reply: {e}")
            return "A moment of silence speaks louder than words."

    def post_reply(self, tweet_id: str, reply_text: str, tweet_text: str):
        payload = {"text": reply_text, "reply": {"in_reply_to_tweet_id": tweet_id}}
        try:
            response = rate_limited_post(self.twitter, payload)
            response.raise_for_status()
            logger.info(f"Replied to tweet {tweet_id}: {reply_text}")
            self._log_engagement("reply", tweet_id, tweet_text, reply_text, 
                               "success", "Reply posted")
        except Exception as e:
            logger.error(f"Error replying to tweet {tweet_id}: {e}")
            self._log_engagement("reply", tweet_id, tweet_text, reply_text, 
                               "error", str(e))

    def favorite_tweet(self, tweet_id: str, tweet_text: str):
        try:
            response = self.twitter.post(TWITTER_FAVORITE_URL, params={"id": tweet_id})
            response.raise_for_status()
            logger.info(f"Favorited tweet {tweet_id}")
            self._log_engagement("favorite", tweet_id, tweet_text, "", 
                               "success", "Tweet favorited")
        except Exception as e:
            logger.error(f"Error favoriting tweet {tweet_id}: {e}")
            self._log_engagement("favorite", tweet_id, tweet_text, "", 
                               "error", str(e))

    def run(self):
        tweets = self.search_tweets(QUERY, max_results=10)
        if not tweets:
            logger.info("No tweets found to engage with.")
            return
        
        random.shuffle(tweets)
        logger.info(f"Found {len(tweets)} tweets to engage with.")
        
        for tweet in tweets:
            tweet_id = tweet["id"]
            tweet_text = tweet["text"]
            reply_text = self.generate_reply(tweet_text)
            self.post_reply(tweet_id, reply_text, tweet_text)
            self.favorite_tweet(tweet_id, tweet_text)
            time.sleep(5)  # Add delay between actions to spread load

if __name__ == "__main__":
    try:
        bot = TwitterBot()
        bot.run()
    except Exception as e:
        logger.error(f"Bot failed to run: {e}")