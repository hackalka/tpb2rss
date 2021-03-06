#!/bin/env python2

# Imports
from bs4 import BeautifulSoup
import sys
import re
import datetime
import urllib2

# Project info
__author__  = "Ian Brunelli"
__email__   = "ian@brunelli.me"
__version__ = "1.2"
__docs__    = "https://github.com/camporez/tpb2rss/"
__license__ = "Apache License 2.0"

# Don't change these lines, unless you are absolutely sure about what you're doing
__tpburl__  = "https://thepiratebay.se"
__agent__   = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36"

def url_parser(search_string, force_most_recent, tpburl):
	# Splits the string (transforms it into a list and removes the empty items)
	url = filter(None, search_string.split("/"))
	# Checks if the URL starts with "search", "user" or "browse"
	if (( url[0] == "search" ) or ( url[0] == "user" ) or ( url[0] == "browse" )) and ( len(url) > 1 ):
		# Checks if the URL has pagination and ordination information and
		# no filter is specified, than adds "0" as filter
		if url[-1].isdigit() and url[-2].isdigit() and not url[-3].isdigit():
			url.append("0")
		try:
			# Checks if the URL has pagination, ordination and filters information
			if url[-2].isdigit() and url[-3].isdigit() and re.match(r"^[0-9]+(,[0-9])*$", url[-1]):
				filters = url[-1]
				link = " ".join(url[1:-3])
			# If no, sets "0" as filter
			else:
				filters = "0"
				link = " ".join(url[1:])
		# If any error, it sets the filters to "0"
		except:
			filters = "0"
		# If pagination and ordination info is being preserved...
		if not force_most_recent:
			# it tries to get these info from the URL
			try:
				pag = int(url[-3])
				order = int(url[-2])
			# If the URL don't have these information, than we tell the program
			# to ignore it and set "0" as filter
			except:
				force_most_recent = True
				filters = "0"
				link = " ".join(url[1:])
		# If pagination and ordination info isn't being preserved (or the URL don't
		# specifies it) it sets "0" to pagination and "3" to ordination
		if force_most_recent:
			pag = 0
			order = 3
		return [url[0], link.decode("iso-8859-1").encode("utf8"), "/" + str(pag) + "/" + str(order) + "/" + filters + "/"]
	# Checks if the user is trying to get feed from /recent
	elif url[0] == "recent":
		return [url[0], ""]
	# Checks if the string isn't an URL
	elif ( len(url) >= 1 ) and ( not re.match(r"^http(s)?://", search_string, flags=re.I) ) and ( not search_string.startswith("/") ):
		# Replaces all slashes by spaces
		search_string = search_string.replace("/", " ")
		return ["search", search_string.decode("iso-8859-1").encode("utf8"), "/0/3/0/"]
	return None

def open_url(input_string, force_most_recent, tpburl, agent):
	global soup, info, link, status
	# Removes the domain from the input string (if a domain is specified)
	search_string = re.sub(r">|<|#|&", "", re.sub(r"^(http(s)?://)?(www.)?" + re.sub(r"^http(s)?://", "", re.sub(r".[a-z]*(:[0-9]*)?$", "", tpburl)) + r".[a-z]*(:[0-9]*)?", "", input_string, flags=re.I))
	# Parses the string and returns a valid URL
	# (e.g. "/search/Suits/0/3/200")
	info = url_parser(search_string.strip(), force_most_recent, tpburl)
	if info:
		# Returns a full link for the page
		link = tpburl + "/" + info[0] + "/" + info[1].decode("utf8").encode("iso-8859-1") + info[-1]
		# Tries to open the link
		try:
			request = urllib2.Request(link, headers={'User-Agent' : agent})
			page = urllib2.urlopen(request)
			status = "200 OK"
		# If not successful, returns the error code
		except urllib2.HTTPError, err:
			if not exceptions:
				print >> sys.stderr, err
			status = str(err.code) + " " + err.reason
		# Parses the page content on Beautiful Soup
		try:
			soup = BeautifulSoup(page.read())
		except:
			soup = None
	else:
		if exceptions:
			raise Exception("The given URL is invalid: " + input_string)
		else:
			print >> sys.stderr, "The given URL is invalid:", input_string
			exit(1)

def open_file(input_file, force_most_recent, tpburl):
	global soup, info, link
	# Opens the file and parses it on Beautiful Soup
	file = open(input_file)
	soup = BeautifulSoup(file.read())
	# Tries to extract information from the file content
	try:
		# Gets the canonical link of the page
		link = str((soup.findAll("link", rel="canonical")[0])).split("\"")[1]
		# Extracts the mirror used on the page
		tpburl = re.search(r"^http(s)?://[\w|\.]+\.[\w|\.]+(:[0-9]+)?/", link).group(0)[:-1]
		# Extracts the string of the search
		search_string = re.sub(r">|<|#|&", "", re.sub(r"^(http(s)?://)?(www.)?" + re.sub(r"^http(s)?://", "", re.sub(r".[a-z]*(:[0-9]*)?$", "", tpburl)) + r".[a-z]*", "", link, flags=re.I))
		# Parses the string and returns a valid URL
		# (e.g. "/search/Manhattan/0/3/0")
		info = url_parser(search_string.strip(), force_most_recent, tpburl)
		# Returns a full link for the page
		link = tpburl + "/" + info[0] + "/" + info[1].decode("utf8").encode("iso-8859-1") + info[-1]
	# If not successful, raises an exception or prints an error and then exits with status 1
	except Exception, err:
		if exceptions:
			raise Exception(err)
		else:
			print >> sys.stderr, "The given file is invalid:", input_file
			exit(1)
	file.close()

def write_file(output_file, content):
	# Tries to write the XML on a file
	try:
		file = open(output_file, "w")
		file.write(content)
		file.close()
	# If not successful, prints an error and then exits with status 1
	except Exception, err:
		print >> sys.stderr, "Couldn't write file:", str(err)
		exit(1)

# This function converts the human-readable date (e.g. "7 mins ago",
# "Today", "Y-day"...) into a RSS 2.0-valid date string.
# Fri, 31 Dec 1999 12:59:59 GMT
def datetime_parser(raw_datetime):
	# Parses date on the format "1 min ago" and "59 mins ago"
	if "min" in raw_datetime:
		raw_datetime = (datetime.datetime.utcnow() - datetime.timedelta(minutes=int(re.sub("[^0-9]", "", raw_datetime)))).strftime("%a, %d %b %Y %H:%M")
		return raw_datetime + ":00"
	# Parses date on the format "Today 23:59"
	elif "Today" in raw_datetime:
		raw_datetime = str(raw_datetime).replace("Today", datetime.datetime.utcnow().strftime("%a, %d %b %Y"))
		raw_datetime = (datetime.datetime.strptime(raw_datetime, "%a, %d %b %Y\xc2\xa0%H:%M") - datetime.timedelta(hours=2)).strftime("%a, %d %b %Y %H:%M")
		return raw_datetime + ":00"
	# Parses date on the format "Y-day 23:59"
	elif "Y-day" in raw_datetime:
		raw_datetime = str(raw_datetime).replace("Y-day", (datetime.datetime.utcnow() - datetime.timedelta(days=1)).strftime("%a, %d %b %Y"))
		raw_datetime = (datetime.datetime.strptime(raw_datetime, "%a, %d %b %Y\xc2\xa0%H:%M") - datetime.timedelta(hours=2)).strftime("%a, %d %b %Y %H:%M")
		return raw_datetime + ":00"
	# Parses date on the format "12-31 23:59"
	elif ":" in raw_datetime:
		months={"01":"Jan", "02":"Feb", "03":"Mar", "04":"Apr", "05":"May", "06":"Jun", "07":"Jul", "08":"Aug", "09":"Sep", "10":"Oct", "11":"Nov", "12":"Dec"}
		raw_datetime = raw_datetime.split("\xc2\xa0")
		raw_datetime = raw_datetime[0].split("-")[1] + " " + months[raw_datetime[0].split("-")[0]] + " " + datetime.datetime.utcnow().strftime("%Y") + " " + str(raw_datetime[1])
		raw_datetime = (datetime.datetime.strptime(raw_datetime, "%d %b %Y %H:%M") - datetime.timedelta(hours=2)).strftime("%a, %d %b %Y %H:%M")
		return raw_datetime + ":00"
	# Parses date on the format "12-31 1999"
	else:
		weekdays=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
		months={"01":"Jan", "02":"Feb", "03":"Mar", "04":"Apr", "05":"May", "06":"Jun", "07":"Jul", "08":"Aug", "09":"Sep", "10":"Oct", "11":"Nov", "12":"Dec"}
		raw_datetime = raw_datetime.split("\xc2\xa0")
		weekday = datetime.date(int(raw_datetime[1]),int(raw_datetime[0].split("-")[0]),int(raw_datetime[0].split("-")[1])).weekday()
		raw_datetime = raw_datetime[0].split("-")[1] + " " + months[raw_datetime[0].split("-")[0]] + " " + str(raw_datetime[1])
		return weekdays[weekday] + ", " + raw_datetime + " 00:00:00"

# Tries to find the given string on the given list and
# returns the position of the last occurrence (or "None")
def find_string(raw_list, word):
	for i, s in enumerate(raw_list):
		if word in s:
			position = i
	try:
		return position
	except:
		return None

def item_constructor(item, seeders, leechers, category, tpburl):
	# The below line is very cute! :3 (it just removes the title from the URL, to get a canonical link)
	link = "/".join(((item[5]).split("/"))[:3])
	# Gets the info hash of the torrent
	info_hash = (item[9].split(":")[3]).split("&")[0]
	# Opens a new item
	item_xml = "\n\t\t<item>\n\t\t\t"
	# Title of the torrent
	item_xml += "<title>" + str(item[8]).split("</a>")[0][1:] + "</title>"
	# Link of the torrent
	item_xml += "\n\t\t\t<link><![CDATA[" + item[9] + "]]></link>"
	# Gets the date and size of the torrent
	uploaded = item[find_string(item, "Uploaded")]
	# Parses the date to use the RSS 2.0 especification, and adds the parsed date to the item
	item_xml += "\n\t\t\t<pubDate>" + datetime_parser(uploaded.split(" ")[1][:-1]) + " GMT</pubDate>"
	# Opens the description of the torrent
	item_xml += "\n\t\t\t<description><![CDATA["
	# Adds the link to the description
	item_xml += "Link: " + tpburl + link + "/"
	# If a torrent file is available, adds it to the description
	try:
		item_xml += "<br>Torrent: " + re.sub(r"^//", "https://", str(item[find_string(item, "piratebaytorrents")]))
	except:
		pass
	# If the uploader's name is available, adds it to the description
	try:
		item_xml += "<br>Uploader: " + str(item[find_string(item, "Browse ")]).replace("Browse ", "")
	except:
		pass
	# Adds the category to the description
	item_xml += "<br>Category: " + category
	# Adds the size to the description
	item_xml += "<br>Size: " + uploaded.split(" ")[3][:-1]
	# Adds the number of seeders to the description
	item_xml += "<br>Seeders: " + seeders
	# Adds the number of leechers to the description
	item_xml += "<br>Leechers: " + leechers
	# Closes the description of the torrent
	item_xml += "]]></description>"
	# Guid of the torrent (canonical link)
	item_xml += "\n\t\t\t<guid>" + tpburl + link + "/</guid>"
	# Torrent header
	item_xml += "\n\t\t\t<torrent xmlns=\"http://xmlns.ezrss.it/0.1/\">"
	# Adds the info hash information
	item_xml += "\n\t\t\t\t<infoHash>" + info_hash + "</infoHash>"
	# Adds the magnet of the torrent
	item_xml += "\n\t\t\t\t<magnetURI><![CDATA[" + item[9] + "]]></magnetURI>"
	# Torrent footer
	item_xml += "\n\t\t\t</torrent>"
	# Closes the item
	item_xml += "\n\t\t</item>"
	return item_xml

def xml_constructor(soup, tpburl):
	# Gets the page type to set a title
	page_type = info[0]
	if page_type == "search":
		title = info[1].replace("%20", " ")
	elif ( page_type == "browse" ):
		title = str(" ".join((soup.span.contents[0].split(" "))[1:]))
	elif ( page_type == "user" ):
		title = info[1]
	elif ( page_type == "recent" ):
		title = "Recent Torrents"
	# Reencodes the title to avoid unacknowledged characters
	title = title.decode("utf8").encode("iso-8859-1")
	# RSS header
	xml = "<rss version=\"2.0\">\n\t" + "<channel>\n\t\t"
	# Title of the feed
	xml += "<title>TPB2RSS: " + title + "</title>\n\t\t"
	# Canonical link of the page
	xml += "<link>" + link + "</link>\n\t\t"
	# Description of the feed
	xml += "<description>The Pirate Bay " + page_type + " feed for \"" + title + "\"</description>\n\t\t"
	# Time of access on the page
	xml += "<lastBuildDate>" + str(datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S")) + " GMT</lastBuildDate>\n\t\t"
	# Language
	xml += "<language>en-us</language>\n\t\t"
	# Generator's title and version
	xml += "<generator>TPB2RSS " + __version__ + "</generator>\n\t\t"
	# Link to our GitHub page
	xml += "<docs>" + __docs__ + "</docs>\n\t\t"
	# Author email
	xml += "<webMaster>" + __email__ + "</webMaster>"
	# Extracts the tables from the HTML
	tables = soup("td")
	# Generates an entry for each item of the page
	position = 0
	for i in range(len(tables) / 4):
		# Gets all the code for an item
		item = str(tables[position + 1]).split("\"")
		# Gets the number of seeders
		seeders = str(str(tables[position + 2]).split(">")[1]).split("<")[0]
		# Gets the number of leechers
		leechers = str(str(tables[position + 3]).split(">")[1]).split("<")[0]
		# Extracts the category of the item
		category = ((re.sub(r"(\n|\t)", "", ("".join( BeautifulSoup(str(tables[position])).findAll( text = True ) )))).replace("(", " (")).decode("iso-8859-1").encode("utf8")
		# Calls the item constructor to create the XML for the entry
		xml += item_constructor(item, seeders, leechers, category, tpburl)
		position += 4
	# RSS footer
	xml += "\n\t</channel>" + "\n</rss>"
	return xml

def xml_from_file(filename, force_most_recent=False, tpburl=__tpburl__):
	# Opens the file, extracts the URL and other things
	open_file(filename, force_most_recent, tpburl)
	# Calls the constructor to create the whole XML
	xml = xml_constructor(soup, tpburl)
	return xml

def xml_from_url(input_string, force_most_recent=True, tpburl=__tpburl__, agent=__agent__):
	# Checks if the string is an URL so we can extract the domain and use it as a mirror
	try:
		tpburl = re.search(r"^http(s)?://[\w|\.]+\.[\w|\.]+(:[0-9]+)?/", input_string).group(0)[:-1]
	except:
		pass
	# Downloads the page and extracts information
	open_url(input_string, force_most_recent, tpburl, agent)
	# Calls the constructor to create the whole XML
	if soup:
		xml = xml_constructor(soup, tpburl)
	else:
		xml = None
	return [status, xml]

def main(parameters):
	# Tests if the program is being called with 1 or 2 parameters
	if (len(parameters) == 2) or (len(parameters) == 3):
		# Tries to use the first parameter as a file
		try:
			xml = xml_from_file(parameters[1])
		# If isn't a file, use it as an URL or string
		except IOError:
			xml = xml_from_url(parameters[1])[1]
		# Tries to write the XML on a file (2nd parameter)
		try:
			write_file(parameters[2], xml)
		# If no 2nd parameter, the XML is printed to the standart output
		except IndexError:
			if xml:
				print xml

# If the program is being called from the user, disables exceptions and calls the main function
if __name__ == "__main__":
	exceptions = False
	main(sys.argv)
else:
	exceptions = True
