
# RedditWatch

Give it a list of Subreddits, and your own reddit api key, and you're off to the races.

#### What does it do?
  - Searches Each Subreddit for Images/Gifs/MP4s/Webms.
  - Downloads all Images/Gifs/MP4s/Webms from the Threads found that are above the given score (100).
  - Loops around every X seconds (0 = disable loop)

#### Works on Windows & Linux.

#### Requirements:
- Python 3 and above (Developed using 3.6.2)
- PRAW
- BeautifulSoup4

#### How to run it:
1. Edit the file and adjust the Subreddits/API Key/Minimum Score.
Make sure to change these values to your own valid API Key. 
```
reddit_api_client_id = 'MY_CLIENT_ID'
reddit_api_client_secret = 'MY_CLIENT_SECRET'
```
Don't have one? This guide should help. 
https://github.com/reddit-archive/reddit/wiki/OAuth2 

2. Run it on Linux or Windows
```sh
$ python3 redditwatch.py
```

#### Notes on Looping:
  - you can either loop by setting `loop_wait = #seconds` inside the script.
  - or by calling the script every hour using cron. 
