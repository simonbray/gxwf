import click
import os
import yaml
import json

from bioblend import galaxy

from requests import ConnectionError as RequestsConnectionError
from bioblend import ConnectionError as BioblendConnectionError
from yaml import SafeLoader

from gxwf import utils

def upload(path, public, file_type):
    gi, cnfg, aliases = utils._login()
    # id = aliases.get(id, id)  # if the user provided an alias, return the id; else assume they provided a raw id

    if path[-3:] == '.ga':  # decide based on ext whether to upload as wf or ds. is this sufficient?
        with open(path) as f:
            # quote from @bgruening: 'Only support the newer yaml based workflow files', don't know what this is though
            # wf_dict = yaml.safe_load(f)
            wf_dict = json.load(f)
        wf_dict['tags'].append('gxwf')
        gi.workflows.import_workflow_dict(wf_dict, publish=public)  # could use import_workflow_from_local_path, but then would need a second call to add the gxwf tag as below
        # gi.workflows.update_workflow(wf['id'], tags=wf['tags'] + ['gxwf'])

    else:
        ds_id = gi.tools.upload_file(path, cnfg['hid'], file_type=file_type)['outputs'][0]['id']
        gi.histories.update_dataset(cnfg['hid'], ds_id, tags=['gxwf'])