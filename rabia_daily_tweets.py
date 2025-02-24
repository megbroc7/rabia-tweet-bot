import os
import requests
import datetime
import pytz
import time
from requests_oauthlib import OAuth1Session
from dotenv import load_dotenv

# Load environment variables from the .env file (for local development)
load_dotenv()

# Retrieve environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY is not set in your environment.")

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

# Import and instantiate the OpenAI client using the new API interface.
from openai import OpenAI
import openai
client = OpenAI(api_key=OPENAI_API_KEY)

def get_time_based_prompt():
    et = pytz.timezone("America/New_York")
    now = datetime.datetime.now(et)
    hour = now.hour

    if 7 <= hour < 10:
        return ("Morning (7-10 AM): Post a daily inspiration or mantra. "
                "Provide a motivational quote, personal reflection, or short wisdom drop.")
    elif 10 <= hour < 13:
        return ("Late Morning/Midday (10 AM-1 PM): Share high-priority content. "
                "On Thursdays, announce new episodes; on other days, share notable insights or blog links.")
    elif 15 <= hour < 17:
        return ("Afternoon (3-5 PM): Post follow-up content or deeper engagement. "
                "On release days, remind followers about the latest episode; otherwise, share a deeper reflection or behind-the-scenes note.")
    elif 18 <= hour < 21:
        return ("Evening (6-9 PM): Share an engagement-focused post. "
                "Ask a question, run a poll, or invite community interaction to spark conversation.")
    else:
        return ("Off-Peak (Late Night/Early Morning): Post an experimental inspirational tweet "
                "for night owls or early birds.")

def clean_tweet(tweet):
    tweet = tweet.replace("*", "").replace("_", "")
    tweet = tweet.replace("#DivineFemin", "#DivineFeminine")
    return tweet

def generate_tweet():
    time_prompt = get_time_based_prompt()
    system_message = f"""You are Rabia Kahn, a fierce yet nurturing spiritual guide, inspired by Kali, deeply rooted in Tantra, and host of the Channeling the Voice of Possibility podcast.
Each day, generate tweets that align with Rabia’s voice—raw, insightful, empowering, and transformative.
Tailor the tweet to the following time slot (ET): {time_prompt}

Important: Output the tweet in plain text without any markdown formatting (do not use asterisks, underscores, etc.), and ensure that hashtags are written fully (for example, output "#DivineFeminine" rather than a truncated version).

⏰ Morning (7:00 AM ET | 12:00 UTC) – Inspiration & Mantra
Short, punchy, and energizing: a mantra, affirmation, or poetic reflection.
Example: "Your breath is a portal. Inhale power, exhale doubt."

⏰ Midday (11:00 AM ET | 16:00 UTC) – Depth & Podcast Content
Thursdays: Introduce the latest episode with an engaging hook + YouTube link.
Example: "A conversation that will shake you awake. Watch here → https://www.youtube.com/@VoiceofPossibility"
Other Days: Share a spiritual insight, mythic reference, or deep reflection.

⏰ Afternoon (3:00 PM ET | 20:00 UTC) – Reflection & Engagement
A thought-provoking question, guest quote, or a deeper layer from the podcast.
Example: "What’s a truth you resisted—until it set you free?"

⏰ Evening (7:00 PM ET | 0:00 UTC) – Community & Conversation
A direct question or interactive post to encourage replies.
Example: "If you could whisper one truth to your younger self, what would it be?"

Tweet Themes (Pick a random one to avoid repetition):
🔥 Power & Expansion – Courage, self-trust, taking up space.
🌊 Surrender & Flow – Releasing control, trusting divine timing.
🌑 Shadow Work – Embracing fears, transformation, liberation.
🌕 Divine Feminine & Masculine – Sacred balance, embodiment.
🌀 Mysticism & Symbolism – Mythology, archetypes, Tantra wisdom.
✨ Wisdom & Intuition – Deep knowing, stillness, trust.
⚡ Rebellion & Liberation – Breaking free, stepping into power.

Hashtags: Use 1–2 relevant hashtags (e.g., #Tantra, #Awakening, #DivineFeminine). Keep the tweet within Twitter's 280-character limit.
Podcast CTA Variations examples:
"Expand your perspective. Watch here → https://www.youtube.com/@VoiceofPossibility"
"Unravel the layers with me → https://www.youtube.com/@VoiceofPossibility"

Final Objective:
Craft a tweet that feels alive, fierce, and deeply personal—encouraging Rabia’s audience to engage and explore their own power.
Important: Do not mention or imply shrinking, minimizing, or reducing yourself. Focus on themes of empowerment, expansion, and owning your space.
"""
    user_message = "Now, generate today’s tweet following this structure."
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        max_tokens=60,
        temperature=0.7,
        top_p=1,
    )
    tweet_text = response.choices[0].message.content.strip()
    tweet_text = clean_tweet(tweet_text)
    return tweet_text

def generate_valid_tweet(max_attempts=5):
    attempt = 0
    tweet = generate_tweet()
    while len(tweet) > 280 and attempt < max_attempts:
        attempt += 1
        print(f"Attempt {attempt}: Tweet too long ({len(tweet)} characters), regenerating...")
        tweet = generate_tweet()
    if len(tweet) > 280:
        print("Final attempt still too long, trimming to 280 characters.")
        tweet = tweet[:280]
    return tweet

def generate_dynamic_image_prompt(tweet_text):
    system_message = (
        "You are an expert creative writer specializing in visual art descriptions. "
        "Based on the following tweet content, generate a vivid and concise image prompt that captures the spirit and theme of the tweet. "
        "If no clear visual theme emerges, simply output: 'A tantric, mystical depiction of goddess energy in vibrant tones'."
    )
    user_message = f"Tweet: {tweet_text}"
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=40,
            temperature=0.7,
            top_p=1,
        )
        image_prompt = response.choices[0].message.content.strip()
        if not image_prompt or len(image_prompt) < 10:
            image_prompt = "A tantric, mystical depiction of goddess energy in vibrant tones"
        return image_prompt
    except Exception as e:
        print(f"Error generating image prompt: {e}")
        return "A tantric, mystical depiction of goddess energy in vibrant tones"

def generate_image(prompt):
    response = client.images.generate(
        prompt=prompt,
        n=1,
        size="512x512"
    )
    image_url = response.data[0].url
    image_data = requests.get(image_url).content
    return image_data

def upload_image_to_twitter(twitter_session, image_data):
    url = "https://upload.twitter.com/1.1/media/upload.json"
    files = {"media": image_data}
    response = twitter_session.post(url, files=files)
    if response.status_code == 200:
        return response.json()["media_id_string"]
    else:
        print("Error uploading image:", response.status_code, response.text)
        return None

def should_include_image():
    et = pytz.timezone("America/New_York")
    today_str = datetime.datetime.now(et).strftime("%Y-%m-%d")
    try:
        with open("last_image_date.txt", "r") as f:
            last_date = f.read().strip()
        return last_date != today_str
    except FileNotFoundError:
        return True

def update_image_post_date():
    et = pytz.timezone("America/New_York")
    today_str = datetime.datetime.now(et).strftime("%Y-%m-%d")
    with open("last_image_date.txt", "w") as f:
        f.write(today_str)

def post_tweet():
    # Try generating a tweet; if it fails, use the fallback.
    try:
        tweet_text = generate_valid_tweet()
        if not tweet_text.strip():
            raise ValueError("Empty tweet generated")
    except Exception as e:
        print("Error generating tweet, falling back to default:", e)
        tweet_text = "Let us know what you think in the comments! https://www.youtube.com/@VoiceofPossibility"
    
    url = "https://api.twitter.com/2/tweets"
    
    twitter = OAuth1Session(
        client_key=TWITTER_API_KEY,
        client_secret=TWITTER_API_SECRET,
        resource_owner_key=TWITTER_ACCESS_TOKEN,
        resource_owner_secret=TWITTER_ACCESS_TOKEN_SECRET,
    )

    if should_include_image():
        image_prompt = generate_dynamic_image_prompt(tweet_text)
        print("Using image prompt:", image_prompt)
        image_data = generate_image(image_prompt)
        media_id = upload_image_to_twitter(twitter, image_data)
        if media_id:
            payload = {
                "text": tweet_text,
                "media": {"media_ids": [media_id]}
            }
            # Attempt to post with image using exponential backoff
            max_retries = 3
            delay = 10  # initial delay in seconds
            for attempt in range(max_retries):
                response = twitter.post(url, json=payload)
                if response.status_code in [200, 201]:
                    print("Tweet with image posted successfully:", tweet_text)
                    update_image_post_date()
                    break
                elif response.status_code == 429:
                    print(f"429 rate limit for image tweet. Attempt {attempt+1}/{max_retries}. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2
                else:
                    print("Error posting tweet with image:", response.status_code, response.text)
                    break
            else:
                # Fallback to text-only if all retries fail
                print("Retries failed for tweet with image. Posting text-only tweet.")
                payload = {"text": tweet_text}
                response = twitter.post(url, json=payload)
                if response.status_code in [200, 201]:
                    print("Text-only tweet posted successfully:", tweet_text)
                else:
                    print("Error posting text-only tweet:", response.status_code, response.text)
        else:
            # Fallback: post text-only if image upload fails.
            payload = {"text": tweet_text}
            response = twitter.post(url, json=payload)
            if response.status_code in [200, 201]:
                print("Tweet posted successfully (fallback text only):", tweet_text)
            else:
                print("Error posting tweet:", response.status_code, response.text)
    else:
        payload = {"text": tweet_text}
        response = twitter.post(url, json=payload)
        if response.status_code in [200, 201]:
            print("Tweet posted successfully:", tweet_text)
        else:
            print("Error posting tweet:", response.status_code, response.text)

if __name__ == "__main__":
    post_tweet()
