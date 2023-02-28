import re, praw, requests, os, glob, sys, itertools, time, threading
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup

subreddits = [
	"dankmemes",
	"wallpapers",
	"anime_irl",
	]
MIN_SCORE = 100 # the default minimum score before it is downloaded
loop_wait = 0 #0 = disabled, 10 = 10 seconds
#loop_wait = 3600 # 0 = disabled, 10 = 10 seconds
max_threads = 100 # 1 thread per Mbit/s is a good rule of thumb

# Must be set to be able to scrape the Reddit API
reddit_api_client_id = 'MY_CLIENT_ID'
reddit_api_client_secret = 'MY_CLIENT_SECRET'
reddit_api_user_agent = 'RedditImageDownloader'

os.system('cls' if os.name == 'nt' else 'clear')
gen_downloaded = 0
gen_processed = 0
live_threads = 0
spinner = itertools.cycle(['-', '\\', '|', '/'])
imgurUrlPattern = re.compile(r'(http://i.imgur.com/(.*))(\?.*)?')
imgurUrlPatternSecure = re.compile(r'(https://i.imgur.com/(.*))(\?.*)?')

# Change script working path to current location. 
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

def checkFolder(subreddit):
    # Check to see if the downloads folder exists
    save_folder = os.path.normpath(os.path.dirname(os.path.realpath(__file__)) + os.path.sep + subreddit)
    if not os.path.isdir(save_folder):
        os.makedirs(save_folder)

def downloadImage(imageUrl, localFileName, subreddit):
    localFileName = localFileName.replace("/", "")
    localFileName = localFileName.replace("\\", "")
    if ".gifv" in imageUrl:
        # Gifv to Gif
        imageUrl = imageUrl.replace(".gifv", ".gif")
        localFileName = localFileName.replace(".gifv", ".gif")
    global gen_downloaded
    global spinner

    # Check if already downloaded
    if not os.path.isfile(subreddit + os.path.sep + localFileName):
        response = requests.get(imageUrl)
        if response.status_code == 200:
            gen_downloaded += 1
            #print("\r [",next(spinner),"] Downloading (",gen_downloaded,")                                         \r", end="")
            #print('Downloading %s...' % (localFileName))
            with open(subreddit + os.path.sep + localFileName, 'wb') as fo:
                for chunk in response.iter_content(4096):
                    fo.write(chunk)
            if os.path.getsize(subreddit + os.path.sep + localFileName) == 503:
                os.remove(subreddit + os.path.sep + localFileName)
                gen_downloaded -= 1

def process_submission(submission):
    while True:
        global spinner
        global MIN_SCORE
        global max_threads
        global gen_processed
        print("\r  [%s] [Threads: %s/%s] Processing [%s](%s)                \r" % (next(spinner), threading.active_count()-1, max_threads, subreddit, gen_processed), end="")
        #print("\r  [",next(spinner),"] [",threading.active_count()-1,"/",max_threads,"] Processing [",subreddit,"](",gen_processed,")                               \r", end="")
        #print("\n",submission.url)
        # Check for all the cases where we will skip a submission:

        supportedDomains = ["imgur.com","gfycat.com","redgifs.con","i.redd.it"]
        doProcess = 0
        for domain in supportedDomains:
            if domain not in submission.url:
                doProcess = doProcess + 1
                
        if doProcess < 1:
            break

        if submission.score < MIN_SCORE:
            break # skip submissions that haven't even reached 100 (thought this should be rare if we're collecting the "hot" submission)
        if len(glob.glob('reddit_%s_%s_*' % (subreddit, submission.id))) > 0:
            break # we've already downloaded files for this reddit submission

        if ('http://redgifs.com/watch/' in submission.url) | ('https://redgifs.com/watch/' in submission.url):
            htmlSource = requests.get(submission.url).text
            soup = BeautifulSoup(htmlSource, "html.parser")
            downloadURL = ""
            matches = soup.select(".video.media source")
            for match in matches:
                downloadURL = match['src'].replace("-mobile","")
                if '?' in downloadURL:
                    imageFile = downloadURL[downloadURL.rfind('/') + 1:downloadURL.rfind('?')]
                else:
                    imageFile = downloadURL[downloadURL.rfind('/') + 1:]
                localFileName = 'reddit_%s_%s_redgifs_%s' % (subreddit, submission.id, imageFile)
                downloadImage(downloadURL,localFileName,subreddit)

        elif ('http://i.redd.it/' in submission.url) | ('https://i.redd.it/' in submission.url):
            downloadURL = submission.url
            if '?' in downloadURL:
                imageFile = downloadURL[downloadURL.rfind('/') + 1:downloadURL.rfind('?')]
            else:
                imageFile = downloadURL[downloadURL.rfind('/') + 1:]
            localFileName = 'reddit_%s_%s_%s' % (subreddit, submission.id, imageFile)
            downloadImage(downloadURL,localFileName,subreddit)
            
        elif ('http://imgur.com/a/' in submission.url) | ('https://imgur.com/a/' in submission.url):
            #print('Album: ' + submission.url)
            # This is an album submission.
            if 'https' in submission.url:
                albumId = submission.url[len('http://imgur.com/a/'):]
            else:
                albumId = submission.url[len('https://imgur.com/a/'):]

            htmlSource = requests.get(submission.url).text
            #print("\n",submission.url, "                        ")

            soup = BeautifulSoup(htmlSource, "html.parser")
            imageUrl = ""
            #matches = soup.select('.album-view-image-link a')
            matches = soup.select('.zoom')
            for match in matches:
                imageUrl = match['href']
                if '?' in imageUrl:
                    imageFile = imageUrl[imageUrl.rfind('/') + 1:imageUrl.rfind('?')]
                else:
                    imageFile = imageUrl[imageUrl.rfind('/') + 1:]
                localFileName = 'reddit_%s_%s_album_%s_imgur_%s' % (subreddit, submission.id, albumId, imageFile)
                if 'https' in submission.url:
                    downloadImage('http:' + match['href'], localFileName, subreddit)
                else:
                    downloadImage('https:' + match['href'], localFileName, subreddit)

        elif ('http://i.imgur.com/' in submission.url) | ('https://i.imgur.com/' in submission.url):
            #print('Image: ' + submission.url)
            # The URL is a direct link to the image.
            if 'https' in submission.url:
                mo = imgurUrlPatternSecure.search(submission.url) # using regex here instead of BeautifulSoup because we are pasing a url, not html
            else:
                mo = imgurUrlPattern.search(submission.url)

            imgurFilename = mo.group(2)
            if '?' in imgurFilename:
                # The regex doesn't catch a "?" at the end of the filename, so we remove it here.
                imgurFilename = imgurFilename[:imgurFilename.find('?')]
                
            if '.gifv' in submission.url:
                htmlSource = requests.get(submission.url).text
                soup = BeautifulSoup(htmlSource, "html.parser")
                downloadUrl = ""
                matches = soup.select('meta[itemprop=contentURL]')
                for match in matches:
                    downloadUrl = match['content']
                    if '?' in downloadUrl:
                        imageFile = downloadUrl[downloadUrl.rfind('/') + 1:downloadUrl.rfind('?')]
                    else:
                        imageFile = downloadUrl[downloadUrl.rfind('/') + 1:]
                    localFileName = 'reddit_%s_%s_imgur_%s' % (subreddit, submission.id, imageFile)
                    downloadImage(downloadUrl,localFileName,subreddit)
            else:
                localFileName = 'reddit_%s_%s_album_None_imgur_%s' % (subreddit, submission.id, imgurFilename)
                downloadImage(submission.url, localFileName, subreddit)

        elif ('http://imgur.com/' in submission.url) | ('https://imgur.com/' in submission.url):
            #print('Page: ' + submission.url)
            # This is an Imgur page with a single image.
            htmlSource = requests.get(submission.url).text # download the image's page
            try:
                soup = BeautifulSoup(htmlSource, "html.parser")
            except:
                break
            imageUrl = ""
            try:
                # Image?
                imageUrl = soup.find('link', {'rel': 'image_src'})['href']
            except:
                # Gif?
                imageUrl = submission.url.replace(".gifv", "")
                imageUrl = str(imageUrl) + ".gif"

                if imageUrl.startswith('//'):
                    # if no schema is supplied in the url, prepend 'http:' to it
                    imageUrl = 'http:' + imageUrl

                response = requests.get(imageUrl)
                if response.status_code != 200:
                    if response.status_code == 404:
                        break
                    else:
                        print('Could not download [' + submission.url + '] (Not Image or Gif)')
                        break

            if imageUrl.startswith('//'):
                # if no schema is supplied in the url, prepend 'http:' to it
                imageUrl = 'http:' + imageUrl
            imageId = imageUrl[imageUrl.rfind('/') + 1:imageUrl.rfind('.')]

            if '?' in imageUrl:
                imageFile = imageUrl[imageUrl.rfind('/') + 1:imageUrl.rfind('?')]
            else:
                imageFile = imageUrl[imageUrl.rfind('/') + 1:]

            localFileName = 'reddit_%s_%s_album_None_imgur_%s' % (subreddit, submission.id, imageFile)
            downloadImage(imageUrl, localFileName, subreddit)

        elif ('http://gfycat.com/' in submission.url) | ('https://gfycat.com/' in submission.url):
            #print('Image: ' + submission.url)
            # The URL is a GIF from Gfycat
            urlid = submission.url.rsplit('/', 1)[-1]

            localFileName = 'reddit_%s_%s_gfycat_%s' % (subreddit, submission.id, urlid)
            try:
                downloadImage("https://giant.gfycat.com/" + urlid + ".webm", localFileName + ".webm", subreddit)
            except:
                try:
                    downloadImage("https://fat.gfycat.com/" + urlid + ".mp4", localFileName + ".mp4", subreddit)
                except:
                    try:
                        downloadImage("https://giant.gfycat.com/" + urlid + ".gif", localFileName + ".gif", subreddit)
                    except:
                        break
        gen_processed = gen_processed + 1
        break

# Connect to reddit and download the subreddit front page
#r = praw.Reddit(user_agent='PoxyDoxyRedditImageDownloader')
print("\rConnecting to API                                    \r", end="")
r = praw.Reddit(client_id=reddit_api_client_id, client_secret=reddit_api_client_secret, user_agent=reddit_api_user_agent)

while True:
    gen_downloaded = 0
    for subreddit in subreddits:
        checkFolder(subreddit)
        submissions = itertools.chain()
        print("\rFetching Submissions [" + subreddit + "] 1/7                          \r", end="")
        submissions = itertools.chain(submissions, r.subreddit(subreddit).hot(limit=500))
        print("\rFetching Submissions [" + subreddit + "] 2/7                          \r", end="")
        submissions = itertools.chain(submissions, r.subreddit(subreddit).top(limit=500))
        print("\rFetching Submissions [" + subreddit + "] 3/7                          \r", end="")
        submissions = itertools.chain(submissions, r.subreddit(subreddit).top(limit=200, time_filter='hour'))
        print("\rFetching Submissions [" + subreddit + "] 4/7                          \r", end="")
        submissions = itertools.chain(submissions, r.subreddit(subreddit).top(limit=200, time_filter='day'))
        print("\rFetching Submissions [" + subreddit + "] 5/7                          \r", end="")
        submissions = itertools.chain(submissions, r.subreddit(subreddit).top(limit=500, time_filter='week'))
        print("\rFetching Submissions [" + subreddit + "] 6/7                          \r", end="")
        submissions = itertools.chain(submissions, r.subreddit(subreddit).top(limit=500, time_filter='month'))
        print("\rFetching Submissions [" + subreddit + "] 7/7                          \r", end="")
        submissions = itertools.chain(submissions, r.subreddit(subreddit).top(limit=500, time_filter='year'))

        # Process all the submissions from the front page
        for todo_submission in submissions:
            while True:
                if threading.active_count() < (max_threads + 1):
                    threading.Thread(target=process_submission,args=(todo_submission,)).start()
                    break
                else:
                    time.sleep(0.3)

        while (threading.active_count()-3) > 0:
            print('  [%s] Finishing [%s] (%s threads remaining)                            \r' % (next(spinner), subreddit, (threading.active_count()-3)), end="")
            time.sleep(0.5)

    if gen_downloaded == 0:
        print('Nothing New                                            ')
    else:
        print('Download Complete (%s images)                           ' % gen_downloaded)

    if loop_wait == 0:
        break
    else:
        while (threading.active_count()-3) > 0:
            print('  [%s] Closing Remaining Threads (%s)                            \r' % (next(spinner), (threading.active_count()-1)), end="")
            time.sleep(0.5)
        time_remaining = loop_wait
        while time_remaining >= 1:
            print("\rStarting again in %s seconds.                       \r" % time_remaining, end="")
            time.sleep(1)
            time_remaining -= 1
os.system('cls' if os.name == 'nt' else 'clear')
