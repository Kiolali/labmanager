# -*-*- encoding: utf-8 -*-*-
# 
# lms4labs is free software: you can redistribute it and/or modify
# it under the terms of the BSD 2-Clause License
# lms4labs is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

"""
  :copyright: 2012 Pablo Orduña, Elio San Cristobal, Alberto Pesquera Martín
  :license: BSD, see LICENSE for more details
"""

#
# Python imports
import json
import urlparse
import codecs
import os
import traceback
import StringIO
import zipfile
from functools import wraps
import urllib2

# 
# Flask imports
# 
from flask import Response, render_template, request, redirect, url_for, flash

# 
# LabManager imports
# 

from labmanager.application import app
from labmanager.database import db_session

def get_json():
    if request.json is not None:
        return request.json
    else:
        try:
            if request.data:
                data = request.data
            else:
                keys = request.form.keys() or ['']
                data = keys[0]
            return json.loads(data)
        except:
            print "Invalid JSON found"
            print "Suggested JSON: %r" % data
            traceback.print_exc()
            return None

def deletes_elements(table):
    def real_wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if request.method == 'POST' and request.form.get('action','') == 'delete':
                for current_id in request.form:
                    element = db_session.query(table).filter_by(id = current_id).first()
                    if element is not None:
                        db_session.delete(element)
                db_session.commit()

            return f(*args, **kwargs)
        return decorated
    return real_wrapper

###############################################################################
# 
# 
# 
#                L M S    I N T E R A C T I O N 
# 
# 
#

def retrieve_courses(url, user, password):
    req = urllib2.Request(url, '')
    req.add_header('Content-type','application/json')

    password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, url, user, password)
    password_handler = urllib2.HTTPBasicAuthHandler(password_mgr)
    opener = urllib2.build_opener(password_handler)

    try:
        json_results= opener.open(req).read()
    except:
        traceback.print_exc()
        return "Error opening provided URL"

    try:
        return json.loads(json_results)
    except:
        print "Invalid JSON", json_results
        return "Invalid JSON"

###############################################################################
# 
# 
# 
#                S C O R M     M A N A G E M E N T
# 
# 
# 

def get_scorm_object(authenticate = True, laboratory_identifier = '', lms_path = '/', lms_extension = '/', html_body = '''<div id="lms4labs_root" />\n'''):
    import labmanager
    # TODO: better way
    base_dir = os.path.dirname(labmanager.__file__)
    base_scorm_dir = os.path.join(base_dir, 'data', 'scorm')
    if not os.path.exists(base_scorm_dir):
        flash("Error: %s does not exist" % base_scorm_dir)
        return render_template("lms_admin/scorm_errors.html")

    sio = StringIO.StringIO('')
    zf = zipfile.ZipFile(sio, 'w')
    for root, dir, files in os.walk(base_scorm_dir):
        for f in files:
            file_name = os.path.join(root, f)
            arc_name  = os.path.join(root[len(base_scorm_dir)+1:], f)
            content = codecs.open(file_name, 'rb', encoding='utf-8').read()
            if f == 'lab.html' and root == base_scorm_dir:
                content = content % { 
                            u'EXPERIMENT_COMMENT'    : '//' if authenticate else '',
                            u'AUTHENTICATE_COMMENT'  : '//' if not authenticate else '',
                            u'EXPERIMENT_IDENTIFIER' : unicode(laboratory_identifier),
                            u'LMS_URL'               : unicode(lms_path),
                            u'LMS_EXTENSION'         : unicode(lms_extension),
                            u'HTML_CONTENT'          : unicode(html_body),
                        }
            zf.writestr(arc_name, content.encode('utf-8'))

    zf.close()
    return sio.getvalue()

def get_authentication_scorm(lms_url):
    lms_path = urlparse.urlparse(lms_url).path or '/'
    extension = '/'
    if 'lms4labs/' in lms_path:
        extension = lms_path[lms_path.rfind('lms4labs/lms/list') + len('lms4labs/lms/list'):]
        lms_path  = lms_path[:lms_path.rfind('lms4labs/')]

    content = get_scorm_object(True, lms_path=lms_path, lms_extension=extension)
    return Response(content, headers = {'Content-Type' : 'application/zip', 'Content-Disposition' : 'attachment; filename=authenticate_scorm.zip'})

###############################################################################
# 
# 
# 
#                G E N E R A L     V I E W
# 
# 
# 

@app.errorhandler(404)
def not_found(e):
    return "404 not found", 404

@app.errorhandler(403)
def forbidden(e):
    return "403 forbidden", 403

@app.errorhandler(412)
def precondition_failed(e):
    return "412 precondition failed", 412

def load():
    import labmanager.views.lms
    assert labmanager.views.lms != None

    import labmanager.views.lms_admin
    assert labmanager.views.lms_admin != None

    import labmanager.views.admin
    assert labmanager.views.admin != None
