#!/usr/bin/env python
import hashlib
import urllib
import urllib2
import json

try:
    import poster
    poster_loaded = True
except ImportError:
    poster_loaded = False


class TorApi(object):
    api_key = ""
    api_token = ""
    api_version = "1"
    server_url = ""
    project_domain = ""

    def __init__(self, api_key, project_domain):
        self.api_key = api_key
        self.project_domain = project_domain
        self.server_url = "http://api.ticketonrails.com"
        md5_key = hashlib.md5(api_key).hexdigest()
        self.api_token = hashlib.md5(project_domain + md5_key).hexdigest()

    def request(self, url, method="GET", parameters=None):
        request_url = self.server_url + "/v" + self.api_version + url
        req_file = None
        parameters["token"] = self.api_token
        if method == "GET":
            opener = urllib2.build_opener()
            req_file = opener.open(request_url + "?" + urllib.urlencode(parameters))
        else:
            # check if there is an attachment
            if "attachment" in parameters and poster_loaded:
                opener = poster.streaminghttp.register_openers()
                datagen, headers = poster.encode.multipart_encode(parameters)
                req = urllib2.Request(request_url, datagen, headers)
            else:
                req = urllib2.Request(request_url, urllib.urlencode(parameters))
            req_file = urllib2.urlopen(req)

        #parse response
        try:
            json_response = str(req_file.read())
            response = json.loads(json_response)
            if req_file.code >= 400:
                raise TorApiException(response["error"])
        finally:
            req_file.close()

        #return
        return response

    def new_ticket(self, values=None):
        params = {}
        ticket = {}
        if values:
            # sending only what is necessary
            ticket_params = ["email", "from_name", "subject", "body", "html", "date", "labels"]
            for param in ticket_params:
                if param in values:
                    ticket[param] = values[param]
            if "attachment" in values and poster_loaded:
                params["attachment"] = open(values["attachment"], "rb")
        params["ticket"] = json.dumps(ticket)
        response = self.request("/tickets", "POST", params)
        return response

    def get_tickets(self, page, limit):
        params = {}
        params["page"] = page
        params["limit"] = limit
        response = self.request("/tickets", "GET", params)
        return response

    def get_ticket(self, ticket_id):
        response = self.request("/tickets/%s" % ticket_id, "GET", {})
        return response


class TorApiException(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
