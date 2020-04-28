import click
import os
import yaml
import json
import webbrowser

from bioblend import galaxy

from requests import ConnectionError as RequestsConnectionError
from bioblend import ConnectionError as BioblendConnectionError
from yaml import SafeLoader

from gxwf import utils

def edit(id_):
    cnfg = utils._read_configfile()
    server_url = cnfg['logins'][cnfg['active_login']]['url']
    id_ = cnfg['aliases'].get(id_, id_)
    webbrowser.open_new('{}workflow/editor?id={}'.format(server_url, id_))
