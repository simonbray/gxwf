#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
.. currentmodule:: gxwf.cli
.. moduleauthor:: Simon Bray <sbray@informatik.uni-freiburg.de>

This is the entry point for the command-line interface (CLI) application.  It
can be used as a handy facility for running the task from a command line.

.. note::

    To learn more about Click visit the
    `project website <http://click.pocoo.org/5/>`_.  There is also a very
    helpful `tutorial video <https://www.youtube.com/watch?v=kNke39OZ2k0>`_.

    To learn more about running Luigi, visit the Luigi project's
    `Read-The-Docs <http://luigi.readthedocs.io/en/stable/>`_ page.
"""
import logging
import click
import os
import time
# from tqdm import tqdm
import yaml

from yaml import SafeLoader

from .__init__ import __version__

from bioblend import galaxy
from bioblend import ConnectionError as BioblendConnectionError

LOGGING_LEVELS = {
    0: logging.NOTSET,
    1: logging.ERROR,
    2: logging.WARN,
    3: logging.INFO,
    4: logging.DEBUG,
}  #: a mapping of `verbose` option counts to logging levels

CONFIG_PATH = os.path.expanduser("~/.gxwf")

def _login():
    try:
        with open(CONFIG_PATH) as f: 
            login_dict = yaml.safe_load(f)
        cnfg = login_dict['logins'][login_dict['active_login']]
        gi = galaxy.GalaxyInstance(cnfg['url'], cnfg['api_key'])
        gi.histories.get_histories()  # just to check the connection
        return gi, cnfg
    except FileNotFoundError:
        print("No login details provided - please run gxwf init.")
    except ConnectionError:
        print("Could not connect - check login details are correct.")


def _tabulate(values):
    """
    Print data as a table

    values is a list of lists, each list a column
    """
    col_widths = [len(max(col, key=len)) + 2 for col in values]

    if len(values[0]) <= 1:
        print("No results found.")
        return 0

    try:
        width = os.get_terminal_size(0)[0]  # get terminal width
    except OSError:
        width = 80  # default

    if sum(col_widths) > width:  # check if the columns are too wide for terminal
        wide_col = col_widths.index(max(col_widths))  # for simplicity we only edit the widest col
        col_widths[wide_col] -= sum(col_widths) - width
        for n in range(len(values[wide_col])):  # check elements of the widest col
            val = values[wide_col][n]
            if len(val) > col_widths[wide_col] - 5:  # insert ellipsis to shorten wide elements
                values[wide_col][n] = val[:int(col_widths[wide_col]/2-3)] + '...' + val[int(3-col_widths[wide_col]/2):]

    row_format = ''.join(["{{:<{}}}".format(n) for n in col_widths])

    click.echo(click.style(row_format.format(*[col[0] for col in values]), bold=True))  # print col headers
    for row in range(1, len(values[0])):
        click.echo(row_format.format(*[col[row] for col in values]))


class Info(object):
    """
    An information object to pass data between CLI functions.
    """

    def __init__(self):  # Note: This object must have an empty constructor.
        self.verbose: int = 0


class GxwfInvocation(object):
    def __init__(self, gi, invoc_id):
        self.invoc_id = invoc_id
        self.gi = gi
    
    def __iter__(self):
        self.summary = self.gi.invocations.get_invocation_summary(self.invoc_id)
        return self.summary['states'].get('ok', 0) / sum(self.summary['states'].values())

# pass_info is a decorator for functions that pass 'Info' objects.
#: pylint: disable=invalid-name
pass_info = click.make_pass_decorator(Info, ensure=True)


# Change the options to below to suit the actual options for your task (or
# tasks).
@click.group()
@click.option("--verbose", "-v", count=True, help="Enable verbose output.")
@pass_info
def cli(info: Info, verbose: int):
    """
    Run gxwf.
    """
    # Use the verbosity count to determine the logging level...
    if verbose > 0:
        logging.basicConfig(
            level=LOGGING_LEVELS[verbose]
            if verbose in LOGGING_LEVELS
            else logging.DEBUG
        )
        click.echo(
            click.style(
                f"Verbose logging is enabled. "
                f"(LEVEL={logging.getLogger().getEffectiveLevel()})",
                fg="yellow",
            )
        )
    info.verbose = verbose


# @cli.command()
# @pass_info
# def hello(_: Info):
#     """
#     Say 'hello' to the nice people.
#     """
#     click.echo(f"gxwf says 'hello'")


@cli.command()
def version():
    """
    Get the library version.
    """
    click.echo(click.style(f"{__version__}", bold=True))

@cli.command()
@click.option("--url", help="URL of Galaxy server")
@click.option("--api-key", help="API key")
@click.option("--name", help="Provide a handy name to refer to a login")
@click.option("--switch", default=False, help="Switch to a different login")
@click.option("--delete", default=False, help="Delete a login")
@click.option("--view", is_flag=True, help="View all logins")
def init(url, api_key, name, switch, delete, view):
    """
    Log into a Galaxy server.
    """

    try:
        with open(CONFIG_PATH, "r") as f:
            login_dict = yaml.load(f.read(), Loader=SafeLoader)
    except FileNotFoundError:
        login_dict = {'active_login': None, 'logins': {}}

    if view:
        login_name, login_url, login_api, login_hid = ['Login name'], ['URL'], ['API key'], ['History ID']

        for lgn in login_dict['logins']:
            login_name.append(lgn)
            login_url.append(login_dict['logins'][lgn]['url'])
            login_api.append(login_dict['logins'][lgn]['api_key'])
            login_hid.append(login_dict['logins'][lgn]['hid'])

        click.echo("You are currently using active login: " + click.style(login_dict['active_login'], bold=True))
        _tabulate([login_name, login_url, login_api, login_hid])

    elif switch:
        if switch in login_dict['logins']:
            login_dict['active_login'] = switch
        else:
            click.echo('Sorry, no login is recorded under the name {}.'.format(switch))
    elif delete:
        if login_dict['active_login'] == delete:
            click.echo('Sorry, {} is the active login and cannot be deleted. Please activate a different login first.'.format(delete))
        else:
            try:
                del login_dict['logins'][delete]
            except KeyError:
                click.echo('Sorry, no login is recorded under the name {}.'.format(delete))
    elif name in login_dict['logins']:
        click.echo('A login is already saved under the name {}; pick another.'.format(name))
    else:
        try:
            gi = galaxy.GalaxyInstance(url=url, key=api_key)
            hid = gi.histories.create_history(name='GXWF datasets')['id']
            gi.histories.create_history_tag(hid, 'gxwf')
        except ConnectionError as e:
            click.echo("Accessing server failed with '{}'".format(e))
        else:
            login_dict['logins'][name] = {'url': url, 'api_key': api_key, 'hid': hid}
            login_dict['active_login'] = name  # automatically switch to the new login
    
    with open(CONFIG_PATH, "w") as f:
        f.write(yaml.dump(login_dict, Dumper=yaml.SafeDumper))
    

@cli.command()
@click.option("--public/--private", default=False, help="List all public workflows or only user-created?.")
@click.option("--search", '-s', default=False, help="Filter workflows by a string.")
def list(public, search):
    gi, cnfg = _login()
    if search:
        workflows = [wf for wf in gi.workflows.get_workflows(published=public) if search in wf['name'] or search in wf['owner']] 
    else:
        workflows = gi.workflows.get_workflows(published=public)

    wf_name, wf_id, steps, owner = ['Workflow name'], ['ID'], ['Steps'], ['Owner']

    for wf in workflows:
        wf_name.append(wf['name'])
        wf_id.append(wf['id'])
        steps.append(str(wf['number_of_steps']))
        owner.append(wf['owner'])

    _tabulate([wf_name, wf_id, steps, owner])

    # click.echo(click.style("{:>100}{:>30}{:>10}{:>20}".format('Workflow name', 'ID', 'Steps', 'Owner'), bold=True))
    # for wf in workflows:
    #     click.echo("{:>100}{:>30}{:>10}{:>20}".format(wf['name'], wf['id'], wf['number_of_steps'], wf['owner']))


@cli.command()
@click.option("--id", help="Workflow ID to run")
@click.option("--history", default='gxwf_history', help="Name to give history in which workflow will be executed.")
@click.option("--save-yaml", default=False, help="Save inputs as YAML, or perform a dry-run.")
@click.option("--run-yaml", default=False, help="Run from inputs previously saved as YAML.")
def invoke(id, history, save_yaml, run_yaml):
    gi, cnfg = _login()
    wf = gi.workflows.show_workflow(id)

    click.echo(click.style("Workflow selected: ", bold=True) + wf['name'])
    click.echo(click.style("Input steps:\n\t{:>5}{:>50}".format('Number', 'Name'), bold=True))

    for inp in wf['inputs']:
        click.echo("\t{:>5}{:>50}".format(inp, wf['inputs'][inp]['label']))
    click.echo('_______________________________________________________________\n')
    # hist = gi.histories.create_history(history)

    # might be nice to show a list of available datasets
    # click.echo(click.style("Datasets available", bold=True))
    # datasets()

    if not run_yaml:
        inputs_dict = {'params': {}, 'inputs': {}}  # what is params actually used for? not clear from the docs
        click.echo(click.style("Enter inputs (dataset id):", bold=True))
        for inp in wf['inputs']:
            print(inp, wf['inputs'][inp]['label'])
            inp_val = click.prompt("Input {}: ".format(inp) + click.style("{}".format(wf['inputs'][inp]['label']), bold=True))
            try:
                gi.datasets.show_dataset(inp_val)  # test if inp_val is a valid dataset id
                inputs_dict['inputs'][inp] = {'src': gi.datasets.show_dataset(inp_val)['hda_ldda'], 'id': inp_val}
            except BioblendConnectionError:  # then we assume it is a param
                 inputs_dict['inputs'][inp] = inp_val

        if save_yaml:
            with open(save_yaml, 'w') as f:
                f.write(yaml.dump(inputs_dict)) 
            cont = click.prompt("Continue to run workflow? [y/n]")
            if cont not in ['y', 'Y']:
                return
    else:
        with open(run_yaml) as f:
            inputs_dict = yaml.load(f, Loader=SafeLoader)

    click.echo(click.style("Invoking workflow...", bold=True))
    # print(id, inputs_dict['inputs'], inputs_dict['params'], hist)
    hid = gi.histories.create_history(history)['id']
    gi.histories.create_history_tag(hid, 'gxwf')
    try:
        inv = gi.workflows.invoke_workflow(id, inputs=inputs_dict['inputs'], params=inputs_dict['params'], history_id=hid)
    except (ConnectionError, BioblendConnectionError):
        click.echo('Invocation failed due to a ConnectionError. Check dataset IDs were specified correctly.')
        gi.histories.delete_history(hid, purge=True)  # tidy up our mess


@cli.command()
@click.option("--id", default=False, help="Workflow ID invoked")
@click.option("--history", default='gxwf_history', help="Name to give history in which workflow will be executed.")
@click.option("--save-yaml", default=False, help="Save inputs as YAML, or perform a dry-run.")
@click.option("--run-yaml", default=False, help="Run from inputs previously saved as YAML.")
def running(id, history, save_yaml, run_yaml):
    gi, cnfg = _login()
    if id:
        invocations = gi.workflows.get_invocations(id)  # will be deprecated, use line below in future
        # invocations = gi.invocations.get_invocations(workflow_id=id)

    else:  # get all invocations - whether this is actually useful or not I don't know, but you get to see a lot of pretty colours
        invocations = gi.invocations.get_invocations()

    for n in range(len(invocations)):
        click.echo(click.style("Invocation {}".format(n+1), bold=True))
        invoc_id = invocations[n]['id']

        step_no = 1
        state_colors = {'ok': 'green', 'running': 'yellow', 'error': 'red', 'paused': 'cyan', 'deleted': 'magenta', 'deleted_new': 'magenta', 'new': 'cyan', 'queued': 'yellow'}
        for state in state_colors:
            for k in range(gi.invocations.get_invocation_summary(invoc_id)['states'].get(state, 0)):
                click.echo(click.style(u'\u2B24' + ' Job {} ({})'.format(k+step_no, state), fg=state_colors[state]))
                step_no += k + 1


@cli.command()
@click.option("--upload", default=False, help="Upload a new dataset")
@click.option("--search", '-s', default=False, help="Filter workflows by a string.")
@click.option("--all", '-a', is_flag=True, help="Get all datasets - not only those in the GXWF history. Warning - may take a REALLY long time.")
def datasets(upload, search, all):
    gi, cnfg = _login()
    # if search:
    #     workflows = [wf for wf in gi.workflows.get_workflows(published=public) if search in wf['name'] or search in wf['owner']] 
    # else:
    #     workflows = gi.workflows.get_workflows(published=public)

    if all:
        dataset_list = []
        for h in gi.histories.get_histories():
            h_name = gi.histories.show_history(h['id'])['name']
            history_list = gi.histories.show_history(h['id'], contents=True)
            print(h_name)
            for dataset in history_list:
                dataset['history_name'] = h_name
            dataset_list += history_list

    else:
        dataset_list = gi.histories.show_history(cnfg['hid'], contents=True)

    ds_name, ds_id, ds_ext, ds_hist = ['Dataset name'], ['ID'], ['Extension'], ['History']

    for ds in dataset_list:
        if ds.get('deleted') == False and ds.get('state') == 'ok':
            ds_name.append(ds.get('name', ''))
            ds_id.append(ds.get('id', ''))
            ds_ext.append(str(ds.get('extension', '')))
            ds_hist.append(ds.get('history_name', ''))  # could hide this option when --all is not set

        if None in [ds.get('name', ''), ds.get('id', ''), ds.get('extension', ''), ds.get('history_name', '')]:
            print(ds)

    _tabulate([ds_name, ds_ext, ds_id, ds_hist])