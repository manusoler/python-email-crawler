from settings import LOGGING
import logging
import logging.config
import urllib
import urllib2
import re
import urlparse
import traceback
import os
from database import CrawlerDb

# Debugging
# import pdb;pdb.set_trace()

# Logging
logging.config.dictConfig(LOGGING)
logger = logging.getLogger("crawler_logger")

google_adurl_regex = re.compile('adurl=(.*?)"')
google_url_regex = re.compile('url\?q=(.*?)&amp;sa=')
email_regex = re.compile(
    '([A-Z0-9._%+-]+@[A-Z0-9.-]+\.(?!(png|gif|jpg|jpeg|mov|mpeg|mpg|mp4))[A-Z]{2,4})', re.IGNORECASE)
url_regex = re.compile('<a\s.*?href=[\'"](.*?)[\'"].*?>')
# Below url_regex will run into 'Castrophic Backtracking'!
# http://stackoverflow.com/questions/8010005/python-re-infinite-execution
# url_regex = re.compile('<a\s(?:.*?\s)*?href=[\'"](.*?)[\'"].*?>')

# Maximum number of search results to start the crawl
MAX_SEARCH_RESULTS = 150

EMAILS_FILENAME = 'data/emails.csv'
DOMAINS_FILENAME = 'data/domains.csv'
EMAIL_DOMAINS_BLACKLIST = 'blacklisted_email_domains.txt'

emails_blacklist = []
# Read blacklist email domains
try:
    emails_blacklist = open(EMAIL_DOMAINS_BLACKLIST,
                            'r').read().splitlines()
except Exception, e:
    logger.error("Couldn't read blackslited email domains")

# Set up the database
db = CrawlerDb()
db.connect()


def crawl(keywords):
    """
    This method will

    1) Google the keywords, and extract MAX_SEARCH_RESULTS
    2) For every result (aka website), crawl the website 2 levels deep.
            That is the homepage (level 1) and all it's links (level 2).
            But if level 1 has the email, then skip going to level 2.
    3) Store the html in /data/html/ and update the database of the crawled emails

    crawl(keywords):
            Extract Google search results and put all in database
            Process each search result, the webpage:
                    Crawl webpage level 1, the homepage
                    Crawl webpage level 2, a link away from the homepage
                    Update all crawled page in database, with has_crawled = True immediately
                    Store the HTML
    """
    logger.info("-"*40)
    logger.info("Keywords to Google for: %s" % keywords.decode('utf-8'))
    logger.info("-"*40)

    # Step 1: Crawl Google Page
    # eg http://www.google.com/search?q=singapore+web+development&start=0
    # Next page: https://www.google.com/search?q=singapore+web+development&start=10
    # Google search results are paged with 10 urls each. There are also adurls
    for page_index in range(0, MAX_SEARCH_RESULTS, 10):
        query = {'q': keywords}
        url = 'https://www.google.com/search?' + \
            urllib.urlencode(query) + '&start=' + str(page_index)
        data = retrieve_html(url)
        # 	print("data: \n%s" % data)
        if data:
            for url in google_url_regex.findall(data):
                db.enqueue(unicode(url))
            for url in google_adurl_regex.findall(data):
                db.enqueue(unicode(url))

    # Step 2: Crawl each of the search result
    # We search till level 2 deep
    while (True):
        # Dequeue an uncrawled webpage from db
        uncrawled = db.dequeue()
        if (uncrawled == False):
            logger.info('No more webpages to crawl')
            save_emails()
            break
        email_set = find_emails_2_level_deep(uncrawled.url)
        if (len(email_set) > 0):
            db.crawled(uncrawled, ",".join(list(email_set)))
        else:
            db.crawled(uncrawled, None)


def save_emails():
    logger.info("="*40)
    logger.info("Processing...")
    emails = db.get_all_emails()
    logger.info("There are %d emails" % len(emails))

    email_filename = get_new_file(EMAILS_FILENAME)
    file = open(email_filename, "w+")
    file.writelines("\n".join(emails))
    file.close()
    logger.info("All emails saved to ./data/emails.csv")
    logger.info("="*40)


def save_domains():
    logger.info("="*40)
    logger.info("Processing...")
    domains = db.get_all_domains()
    logger.info("There are %d domains" % len(domains))
    domains_filename = get_new_file(DOMAINS_FILENAME)
    file = open(domains_filename, "w+")
    file.writelines("\n".join(domains))
    file.close()
    logger.info("All domains saved to ./data/domains.csv")
    logger.info("="*40)


def get_new_file(filename):
    new_filename = filename
    counter = 1
    while os.path.isfile(new_filename):
        new_filename = "{}_{}.csv".format(
            new_filename[:(-4 if '_' not in new_filename else new_filename.index('_'))], counter)
        counter += 1
    return new_filename


def retrieve_html(url):
    """
    Crawl a website, and returns the whole html as an ascii string.

    On any error, return.
    """
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Just-Crawling 0.1')
    request = None
    status = 0
    try:
        logger.info("Crawling %s" % url)
        request = urllib2.urlopen(req)
    except urllib2.HTTPError, e:
        status = e.code
    except urllib2.URLError, e:
        logger.error("Exception at url: %s\n%s" % (url, e))
    except Exception, e:
        return
    if status == 0:
        status = 200

    try:
        data = request.read()
    except Exception, e:
        return

    return str(data)


def find_emails_2_level_deep(url):
    """
    Find the email at level 1.
    If there is an email, good. Return that email
    Else, find in level 2. Store all results in database directly, and return None
    """
    html = retrieve_html(url)
    email_set = find_emails_in_html(html)

    if (len(email_set) > 0):
        # If there is a email, we stop at level 1.
        return email_set

    else:
        # No email at level 1. Crawl level 2
        logger.info('No email at level 1.. proceeding to crawl level 2')

        link_set = find_links_in_html_with_same_hostname(url, html)
        for link in link_set:
            # Crawl them right away!
            # Enqueue them too
            html = retrieve_html(link)
            if (html == None):
                continue
            email_set = find_emails_in_html(html)
            db.enqueue(link, list(email_set))

        # We return an empty set
        return set()


def find_emails_in_html(html):
    if (html == None):
        return set()
    email_set = set()
    for email in email_regex.findall(html):
        if type(email) == tuple:
            logger.info(str(email) + ' --> ' + email[0])
            email = email[0]
        if email[email.index('@')+1:email.rfind('.')].lower() not in emails_blacklist:
            email_set.add(email)
    return email_set


def find_links_in_html_with_same_hostname(url, html):
    """
    Find all the links with same hostname as url
    """
    if (html == None):
        return set()
    url = urlparse.urlparse(url)
    links = url_regex.findall(html)
    link_set = set()
    for link in links:
        if link == None:
            continue
        try:
            link = str(link)
            if link.startswith("/"):
                link_set.add('http://'+url.netloc+link)
            elif link.startswith("http") or link.startswith("https"):
                if (link.find(url.netloc)):
                    link_set.add(link)
            elif link.startswith("#"):
                continue
            else:
                link_set.add(urlparse.urljoin(url.geturl(), link))
        except Exception, e:
            pass

    return link_set


if __name__ == "__main__":
    import sys
    try:
        arg = sys.argv[1].lower()
        if (arg == '--emails') or (arg == '-e'):
            # Get all the emails and save in a CSV
            save_emails()
        elif (arg == '--domains') or (arg == '-d'):
            # Get all the domains and save in a CSV
            save_domains()
        else:
            # Crawl the supplied keywords!
            crawl(arg)

    except KeyboardInterrupt:
        logger.error("Stopping (KeyboardInterrupt)")
        save_emails()
        sys.exit()
    except Exception, e:
        logger.error("EXCEPTION: %s " % e)
        traceback.print_exc()
