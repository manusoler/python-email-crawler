Python Email Crawler
====================

This python script search/google certain keywords, crawls the webpages from the results, and return all emails found.

Requirements
------------

- sqlalchemy
- urllib2

If you don't have, simply `sudo pip install sqlalchemy`. 


Usage
-------

Start the search with a keyword. We use "iphone developers" as an example.

	python email_crawler.py "iphone developers"

The search and crawling process will take quite a while, as it retrieve up to 500 search results (from Google), and crawl up to 2 level deep. It should crawl around 10,000 webpages :)

After the process finished or is canceled (Ctrl + C) emails will be saved in ./data/emails.csv.

It is possible to blacklist some domains in order to exclude them from the email results. Add them to the `blacklisted_email_domains` file (one on each line), for example 

```
gmail
hotmail
outlook
```
