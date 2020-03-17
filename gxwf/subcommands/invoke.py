import click
import os
import yaml
import json

from bioblend import galaxy

from requests import ConnectionError as RequestsConnectionError
from bioblend import ConnectionError as BioblendConnectionError
from yaml import SafeLoader

from gxwf import utils

def _invoke(gi, inputs_dict, history):
    click.echo(click.style("Invoking workflow...", bold=True))
    # print(id, inputs_dict['inputs'], inputs_dict['params'], hist)
    hid = gi.histories.create_history(history)['id']
    gi.histories.create_history_tag(hid, 'gxwf')
    try:
        inv = gi.workflows.invoke_workflow(inputs_dict['wf_id'], inputs=inputs_dict['inputs'], params=inputs_dict['params'], history_id=hid)
    except (ConnectionError, BioblendConnectionError):
        click.echo('Invocation failed due to a ConnectionError. Check dataset IDs were specified correctly.')
        gi.histories.delete_history(hid, purge=True)  # tidy up our mess


def _create_dict(gi, id_, wf, aliases, save_yaml=None):
    inputs_dict = {'params': {}, 'inputs': {}}  # what is params actually used for? not clear from the docs
    click.echo(click.style("Enter inputs (dataset id):", bold=True))
    for inp in wf['inputs']:
        print(inp, wf['inputs'][inp]['label'])
        inp_val = click.prompt("Input {}: ".format(inp) + click.style("{}".format(wf['inputs'][inp]['label']), bold=True))
        try:
            inp_val = aliases.get(inp_val, inp_val)
            gi.datasets.show_dataset(inp_val)  # test if inp_val is a valid dataset id
            inputs_dict['inputs'][inp] = {'src': gi.datasets.show_dataset(inp_val)['hda_ldda'], 'id': inp_val}
        except BioblendConnectionError:  # then we assume it is a param
             inputs_dict['inputs'][inp] = inp_val
    inputs_dict['wf_id'] = id_
    if save_yaml:
        utils._write_to_file(inputs_dict, save_yaml)
        with open(save_yaml, 'w') as f:
            f.write(yaml.dump(inputs_dict)) 
        cont = click.prompt("Continue to run workflow? [y/n]")
        if cont not in ['y', 'Y']:
            return None
    return inputs_dict

@click.command()
@click.argument('id_')
@click.option("--history", default='gxwf_history', help="Name to give history in which workflow will be executed (default: gxwf_history).")
@click.option("--save-yaml", default=False, help="Save inputs as YAML, or perform a dry-run.")
def from_params(id_, history, save_yaml):
    """
    Invoke a workflow using its ID (or alias) and select datasets and parameters interactively.

    When prompted to give a value for an input, provide a ID or alias for a dataset, and text in whatever format (e.g. integer, string) is required for a parameter.

    A new history will be created for the invocation; this can be named using --history.
    """
    gi, cnfg, aliases = utils._login()
    id_ = aliases.get(id_, id_)  # if the user provided an alias, return the id; else assume they provided a raw id
    wf = gi.workflows.show_workflow(id_)

    click.echo(click.style("Workflow selected: ", bold=True) + wf['name'])
    click.echo(click.style("Input steps:\n\t{:>5}{:>50}".format('Number', 'Name'), bold=True))

    for inp in wf['inputs']:
        click.echo("\t{:>5}{:>50}".format(inp, wf['inputs'][inp]['label']))
    click.echo('_______________________________________________________________\n')

    # might be nice to show a list of available datasets
    # click.echo(click.style("Datasets available", bold=True))
    # datasets()

    inputs_dict = _create_dict(gi, id_, wf, aliases, save_yaml)
    if not inputs_dict:
        return

    _invoke(gi, inputs_dict, history)


@click.command()
@click.argument("yaml_file")
@click.option("--history", default='gxwf_history', help="Name to give history in which workflow will be executed (default: gxwf_history).")
# @click.option("--yaml", required=True, help="YAML file containing parameters for workflow to be run")
def from_yaml(yaml_file, history):
    """
    Invoke a workflow from a YAML file containing all parameters (workflow ID, inputs, etc...). This YAML file can be generated using `gxwf invoke ... --save_yaml`.
    """
    gi, cnfg, aliases = utils._login()
    with open(yaml_file) as f:
        inputs_dict = yaml.load(f, Loader=SafeLoader)
    
    _invoke(gi, inputs_dict, history)