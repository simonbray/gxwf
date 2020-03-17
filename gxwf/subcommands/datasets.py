import click
import os
import yaml

from bioblend import galaxy

from requests import ConnectionError as RequestsConnectionError
from bioblend import ConnectionError as BioblendConnectionError
from yaml import SafeLoader

from gxwf import utils

def datasets(search, all):
    gi, cnfg, aliases = utils._login()
    aliases_inverted = {v: k for k, v in aliases.items()}  # need this below

    if all:
        # replace all this rubbish with gi.datasets.get_datasets() when the PR is merged
        dataset_list = gi.datasets._get('?limit=1000000000000')
        # for h in gi.histories.get_histories():
        #     h_name = gi.histories.show_history(h['id'])['name']
        #     history_list = gi.histories.show_history(h['id'], contents=True)
        #     for dataset in history_list:
        #         dataset['history_name'] = h_name
        #     dataset_list += history_list

    else:
        dataset_list = gi.histories.show_history(cnfg['hid'], contents=True)
        for dataset in dataset_list:
            if 'gxwf' not in dataset['tags']:
                gi.histories.update_dataset(cnfg['hid'], dataset['id'], tags=['gxwf'])

    ds_name, ds_id, ds_alias, ds_ext = ['Dataset name'], ['ID'], ['Alias'], ['Extension']#, ['History']

    for ds in dataset_list:
        if search:
            if search not in ds.get('name', ''):
                continue
        if ds.get('deleted') == False and ds.get('state') == 'ok':  # could show non-ok datasets too? 
            ds_name.append(ds.get('name', ''))
            ds_id.append(ds.get('id', ''))
            ds_alias.append(aliases_inverted.get(ds.get('id'), ''))
            ds_ext.append(str(ds.get('extension', '')))
            # ds_hist.append(ds.get('history_name', ''))  # could hide this option when --all is not set

    utils._tabulate([ds_name, ds_ext, ds_id, ds_alias,])  # ds_hist])