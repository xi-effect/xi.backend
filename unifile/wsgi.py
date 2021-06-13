# This file contains the WSGI configuration required to serve up your
# web application at http://<your-username>.pythonanywhere.com/
# It works by setting the variable 'application' to a WSGI handler of some
# description.
#
# The below has been partly auto-generated for your Flask project

import sys

# add your project directory to the sys.path
project_home = "/home/qwert45hi/mysite"
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# import flask app but need to call it "application" for WSGI to work
# importing discord webhook functionality
from unifile_server import app as application  # noqa
from unifile_server import on_restart  # noqa
on_restart()  # works on restart
