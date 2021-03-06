# This file is a part of TPB2RSS (https://github.com/camporez/tpb2rss/)

import os
import tpb2rss
import page

def feed_generator(path_info):
	global error
	try:
		result = tpb2rss.xml_from_url(path_info)
		return result
	except Exception, err:
		error = str(err)
		return None

def application(environ, start_response):
	global error
	status = "200 OK"
	error = ""

	if (( environ["PATH_INFO"] == "") or ( environ["PATH_INFO"] == "/" )):
		xml = False
	else:
		result = feed_generator(environ["PATH_INFO"])
		try:
			status = result[0]
			xml = result[1]
		except:
			status = "404 Not Found"
			xml = None
	if xml:
		ctype = "text/xml"
		response_body = xml
	else:
		ctype = "text/html"
		response_body = page.build(xml, error, status)

	response_headers = [("Content-Type", ctype), ("Content-Length", str(len(response_body)))]

	start_response(status, response_headers)
	return [response_body]
