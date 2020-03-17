import click
import os
import yaml
import namesgenerator

from bioblend import galaxy

from requests import ConnectionError as RequestsConnectionError
from bioblend import ConnectionError as BioblendConnectionError
from yaml import SafeLoader

from gxwf import utils

def _update_aliases(aliases, configfile=utils.CONFIG_PATH):
    f = utils._read_configfile(configfile=configfile)
    f['aliases'] = aliases
    utils._write_to_file(f)

@click.command()
@click.option("--id", required=True, help="Workflow or dataset ID to be assigned an alias.")
@click.option("--alias", default=False, help="Alias to assign to a workflow, history or dataset ID. If not specified, one will be randomly generated.")
def add_single(id, alias):
    """
    Add an alias to a single ID.
    """
    gi, cnfg, aliases = utils._login()
    if not alias:
        alias = namesgenerator.get_random_name()
    click.echo("Alias assigned to ID {}: ".format(id) + click.style(alias, bold=True))
    aliases[alias] = id
    _update_aliases(aliases)

@click.command()
def add_all():
    """
    Add randomly generated aliases to all workflows and datasets which do not currently have one.
    """
    gi, cnfg, aliases = utils._login()
    workflow_ids = [wf['id'] for wf in gi.workflows.get_workflows()]
    dataset_ids = [ds['id'] for ds in gi.histories.show_history(cnfg['hid'], contents=True)]
    for id in workflow_ids + dataset_ids:
        if id not in aliases.values():  # we do not overwrite if an alias already exists
            while True:
                alias = namesgenerator.get_random_name()
                # we can allow one id to have multiple aliases but NOT the reverse
                if alias not in aliases:
                    break
            click.echo("Alias assigned to ID {}: ".format(id) + click.style(alias, bold=True))
            aliases[alias] = id
    _update_aliases(aliases)

@click.command(name="list")
def list_():
    """
    List all aliases currently assigned to IDs.
    """
    gi, cnfg, aliases = utils._login()
    alias, id = ['Alias'], ['ID']

    for a in aliases:
        alias.append(a)
        id.append(aliases[a])

    utils._tabulate([alias, id])

@click.command()
@click.option('--alias', default=False, help='Alias to remove.')
@click.option('--all', 'all_', is_flag=True, help='Remove all saved aliases.')
def delete(alias, all_):
    """
    Remove a single currently assigned alias with --alias, or all aliases with --all
    """
    if bool(alias) == bool(all_):
        click.echo(click.get_current_context().get_help())  # raise help, we need either option but not both or neither
        return

    gi, cnfg, aliases = utils._login()
    if all_:
        aliases = {}
    elif alias:
        aliases.pop(alias)
    else:
        return
    
    _update_aliases(aliases)
