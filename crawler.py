import sys
import os
import re
import logging
import traceback
import csv
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

# Logging
logging.basicConfig(level=logging.INFO, filename=os.path.join(os.path.dirname(__file__),
                    'crawler.log'), format='%(asctime)s::%(levelname)s::%(message)s')

class EmailCrawler():

    MAX_SEARCH_RESULTS = 10

    EMAIL_DOMAINS_BLACKLIST = os.path.join(os.path.dirname(__file__), 'blacklisted_email_domains.txt')
    EMAILS_FILENAME = os.path.join(os.path.dirname(__file__), 'emails.csv')

    GOOGLE_URL_SELECTOR = "div.g div.rc > div > a"
    GOOGLE_TITLE_SELECTOR = "h3 > span"

    EMAIL_REGEX = re.compile('([A-Z0-9._%+-]+@[A-Z0-9.-]+\.(?!(png|gif|jpg|jpeg|mov|mpeg|mpg|mp4))[A-Z]{2,4})', 
        re.IGNORECASE)

    # Headers for requests
    HEADERS = ({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.67 Safari/537.36',
            "accept-language": "es-ES,es;q=0.9"})
    
    def __init__(self):
        self.emails_blacklist = []
        try:
            self.emails_blacklist = open(EmailCrawler.EMAIL_DOMAINS_BLACKLIST,'r').read().splitlines()
        except Exception as e:
            self.emails_blacklist = []

    def crawl(self, keywords):
        logging.info(f"Starting crawl for '{keywords}'")
        keywords = requests.utils.quote(keywords)
        with open(EmailCrawler.EMAILS_FILENAME, 'a') as email_file:
            logging.info(f"Emails will be stored in '{EmailCrawler.EMAILS_FILENAME}'")
            writer = csv.writer(email_file)
            for page_index in range(0, EmailCrawler.MAX_SEARCH_RESULTS, 10):
                # Crawl Google Page (each page 10 results)
                links = self._get_google_results(keywords, page_index)
                # For every result (link), go and get emails with depth 2 (homepage and its links (same domain))
                for link in links:
                    url = link.get('href')
                    logging.info(f"Crawling '{url}'")
                    writer.writerows([(x,urlparse(url).netloc) for x in self._go_and_crawl(url, 1)])
                
                
    def _get_google_results(self, keywords, page_index):
        logging.info(f"Googling '{keywords}', page {page_index}")
        html = requests.get(f'https://www.google.com/search?q={keywords}&start={page_index}'.encode('utf8'), 
            headers=EmailCrawler.HEADERS).text
        bs = BeautifulSoup(html, 'html.parser')
        return bs.select(EmailCrawler.GOOGLE_URL_SELECTOR)
            
    def _go_and_crawl(self, url, depth=0):
        logging.debug(f"Crawling '{url}' with depth {depth}")
        try:
            html = requests.get(url.encode('utf8'), headers=EmailCrawler.HEADERS).text
        except requests.RequestException:
            logging.error(f"   Skipping {url} due to an error")
            return None
        bs = BeautifulSoup(html, 'html.parser')
        emails = self._get_emails(html)
        if emails or depth <= 0:
            return emails
        netloc = urlparse(url).netloc
        # Go 1 in depth
        links = bs.select("a")
        logging.info(f"   {len(links)} links found")
        for link in bs.select("a"):
            suburl = link.get('href')
            # Visit if same domain (netloc)
            if netloc == urlparse(suburl).netloc:
                emails.update(self._go_and_crawl(suburl, depth-1))
            else:
                logging.debug(f"   Skipped '{suburl}' for {url}")
        logging.info(f"   Retrieved {len(emails)} emails for {url}")
        return emails

    def _get_emails(self, html):
        emails = set()
        for email in EmailCrawler.EMAIL_REGEX.findall(html):
            if type(email) == tuple:
                email = email[0]
            if email[email.index('@')+1:email.rfind('.')].lower() not in self.emails_blacklist:
                emails.add(email)
        logging.debug(f"   Emails found: {emails}")
        return emails

if __name__ == "__main__":    
    try:
        crawler = EmailCrawler()
        crawler.crawl(sys.argv[1])
    except KeyboardInterrupt:
        logging.error("Stopping (KeyboardInterrupt)")
        sys.exit()
    except Exception as e:
        logging.error("EXCEPTION: %s " % e)
        traceback.print_exc()
