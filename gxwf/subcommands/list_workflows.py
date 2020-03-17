import click
import os
import yaml

from bioblend import galaxy

from requests import ConnectionError as RequestsConnectionError
from bioblend import ConnectionError as BioblendConnectionError
from yaml import SafeLoader

from gxwf import utils

def list_workflows(public, search):
    gi, cnfg, aliases = utils._login()
    aliases_inverted = {v: k for k, v in aliases.items()}  # need this below
    if search:
        workflows = [wf for wf in gi.workflows.get_workflows(published=public) if search in wf['name'] or search in wf['owner']] 
    else:
        workflows = gi.workflows.get_workflows(published=public)

    wf_name, wf_id, wf_alias, steps, owner = ['Workflow name'], ['ID'], ['Alias'], ['Steps'], ['Owner']
    # do we need separate id / alias columns? if we make sure everything can be done via alias

    for wf in workflows:
        wf_name.append(wf['name'])
        wf_id.append(wf['id'])
        wf_alias.append(aliases_inverted.get(wf['id'], ''))
        steps.append(str(wf['number_of_steps']))
        owner.append(wf['owner'])

    utils._tabulate([wf_name, wf_id, wf_alias, steps, owner])