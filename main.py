import time
import re
import pandas as pd
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import random
import json
import os

# near init_driver()
def init_driver():
    options = uc.ChromeOptions()
    if os.getenv("HEADLESS", "1") == "1":
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = uc.Chrome(options=options)
    return driver

def save_cookies(driver, filename="cookies.json"):
    """Save cookies to a file"""
    try:
        cookies = driver.get_cookies()
        if cookies:
            with open(filename, 'w') as f:
                json.dump(cookies, f, indent=2)
            print(f"✅ Cookies saved to {filename}")
        else:
            print("❌ No cookies to save")
    except Exception as e:
        print(f"❌ Error saving cookies: {e}")

def load_cookies(driver, filename="cookies.json"):
    """Load cookies from a file"""
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                cookies = json.load(f)
            
            # Check if cookies list is empty
            if not cookies:
                print("❌ Cookies file is empty")
                return False
            
            # Navigate to X.com first
            driver.get("https://x.com")
            time.sleep(2)
            
            # Add each cookie
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    print(f"Could not add cookie: {e}")
            
            # Refresh to apply cookies
            driver.refresh()
            time.sleep(3)
            print("✅ Cookies loaded successfully")
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid cookies file format: {e}")
            # Delete corrupted cookies file
            os.remove(filename)
            print(f"Deleted corrupted cookies file: {filename}")
            return False
        except Exception as e:
            print(f"❌ Error loading cookies: {e}")
            return False
    return False

def check_login_status(driver):
    """Check if user is already logged in"""
    try:
        driver.get("https://x.com/home")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "nav[aria-label='Primary']"))
        )
        print("✅ Already logged in!")
        return True
    except TimeoutException:
        print("❌ Not logged in")
        return False

def login_to_x(driver, email, username, password, cookies_file="cookies.json"):
    try:
        # First try to load existing cookies
        if load_cookies(driver, cookies_file):
            if check_login_status(driver):
                return True
        
        # If cookies didn't work, perform fresh login
        print("Performing fresh login...")
        driver.get("https://x.com/login")

        # Wait for the first input (email)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.NAME, "text"))
        )
        email_field = driver.find_element(By.NAME, "text")
        email_field.send_keys(email)
        time.sleep(random.uniform(2, 4))

        # Click Next button
        next_button = driver.find_element(By.XPATH, "//span[text()='Next']")
        next_button.click()
        time.sleep(random.uniform(2, 4))

        # Check if username is required (sometimes Twitter asks for it)
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.NAME, "text"))
            )
            # If we're still on a text input, it might be asking for username
            current_input = driver.find_element(By.NAME, "text")
            if current_input.is_displayed():
                current_input.send_keys(username)
                time.sleep(random.uniform(1.5, 3))
                next_button = driver.find_element(By.XPATH, "//span[text()='Next']")
                next_button.click()
                time.sleep(random.uniform(2, 4))
        except TimeoutException:
            pass  # Username not required

        # Wait for the password field
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.NAME, "password"))
        )
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys(password)
        time.sleep(random.uniform(2, 4))

        # Click Log in button
        login_button = driver.find_element(By.XPATH, "//span[text()='Log in']")
        login_button.click()
        time.sleep(random.uniform(3, 5))

        time.sleep(30)

        # Wait for home page element to confirm login
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "nav[aria-label='Primary']"))
        )
        
        # Save cookies after successful login
        save_cookies(driver, cookies_file)
        print("✅ Successfully logged in to X.com")
        return True

    except TimeoutException:
        print("❌ Timeout during login process")
        return False
    except NoSuchElementException as e:
        print(f"❌ Element not found during login: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during login: {e}")
        return False

# Extract emojis from text
def extract_emojis(text):
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F700-\U0001F77F"
        u"\U0001F780-\U0001F7FF"
        u"\U0001F800-\U0001F8FF"
        u"\U0001F900-\U0001F9FF"
        u"\U0001FA00-\U0001FA6F"
        u"\U0001FA70-\U0001FAFF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    return ''.join(emoji_pattern.findall(text))

# Append data to CSV
def append_to_csv(data, filename):
    if not data:
        return
    df = pd.DataFrame(data)
    mode = 'a' if os.path.exists(filename) else 'w'
    header = not os.path.exists(filename)
    df.to_csv(filename, mode=mode, header=header, index=False)
    print(f"Appended {len(data)} posts to {filename}")

# Scrape tweets after login
def scrape_tweets(url, filename, email, username, password):
    driver = init_driver()
    try:
        # Perform login with cookie management
        if not login_to_x(driver, email, username, password):
            print("Login failed. Cannot proceed with scraping.")
            return []

        # Navigate to the target page
        driver.get(url)

        # Wait for initial page load
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article[role='article']"))
            )
        except TimeoutException:
            print("Timeout waiting for posts.")
            return []

        tweets_data = []
        seen_tweet_ids = set()
        scroll_count = 0
        max_scrolls = 80
        scroll_pause_time = 8
        last_height = driver.execute_script("return window.pageYOffset")

        while scroll_count < max_scrolls:
            # Use Selenium to find articles for dynamic content
            articles = driver.find_elements(By.CSS_SELECTOR, "article[role='article']")
            print(f"Found {len(articles)} posts on scroll {scroll_count}")
            new_tweets_data = []

            for article in articles:
                try:
                    # Parse article HTML with BeautifulSoup
                    soup = BeautifulSoup(article.get_attribute('outerHTML'), 'html.parser')
                    tweet = soup.find("article", attrs={"role": "article"})

                    # Extract tweet ID (URL of tweet)
                    permalink = tweet.find("a", href=lambda href: href and "/status/" in href)
                    tweet_id = permalink['href'] if permalink else None
                    if not tweet_id:
                        time_elem = tweet.find("time")
                        text_div = tweet.find("div", attrs={"data-testid": "tweetText"})
                        tweet_id = f"{time_elem['datetime']}_{text_div.text[:20]}" if time_elem and text_div else None
                    if not tweet_id or tweet_id in seen_tweet_ids:
                        continue
                    seen_tweet_ids.add(tweet_id)

                    # Extract user name
                    user_name_elem = tweet.find("div", attrs={"data-testid": "User-Name"})
                    user_name = user_name_elem.text.strip() if user_name_elem else ""

                    # Extract timestamp
                    time_elem = tweet.find("time")
                    timestamp = time_elem['datetime'] if time_elem else ""

                    # Extract tweet text
                    text_div = tweet.find("div", attrs={"data-testid": "tweetText"})
                    text = text_div.text.strip() if text_div else ""

                    # Extract emojis from text
                    emojis = extract_emojis(text)

                    # Initialize metrics
                    comments = likes = reposts = 0

                    # Extract image link (if any)
                    image_link = ""
                    image_tag = tweet.find("img", attrs={"alt": "Image"})
                    if image_tag:
                        image_link = image_tag["src"]

                    # Construct tweet URL
                    tweet_url = f"https://x.com{tweet_id}" if tweet_id and "/status/" in tweet_id else ""

                    # Save data to dictionary
                    post_data = {
                        "user_name": user_name,
                        "timestamp": timestamp,
                        "text": text,
                        "emojis": emojis,
                        "comments": comments,
                        "reposts": reposts,
                        "likes": likes,
                        "image_link": image_link,
                        "tweet_url": tweet_url
                    }
                    new_tweets_data.append(post_data)

                except Exception as e:
                    print(f"Error parsing tweet: {e}")
                    continue

            if new_tweets_data:
                append_to_csv(new_tweets_data, filename)
                tweets_data.extend(new_tweets_data)

            # Scroll slightly
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(scroll_pause_time)

            new_height = driver.execute_script("return window.pageYOffset")
            if new_height == last_height:
                print("No new content loaded. Ending scroll.")
                break
            last_height = new_height
            scroll_count += 1

        print(f"Scraped {len(tweets_data)} total posts.")
        return tweets_data

    except Exception as e:
        print(f"Error during scraping: {e}")
        return []

    finally:
        try:
            driver.quit()
        except Exception as e:
            print(f"Error closing driver: {e}")
            pass

if __name__ == "__main__":
    url = "https://x.com/TheRealPCB"
    filename = "x_dva.csv"
    email = "nothing4816@gmail.com"
    password = "nothing123@"
    username = "Nothing023189"
    tweets = scrape_tweets(url, filename, email, username, password)
