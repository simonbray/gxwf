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
import yaml
import json

import namesgenerator  # for now install via pip
import gxformat2

from yaml import SafeLoader

from .__init__ import __version__

from bioblend import galaxy
from bioblend import ConnectionError as BioblendConnectionError

from requests import ConnectionError as RequestsConnectionError

from .init_group import commands as init_group


LOGGING_LEVELS = {
    0: logging.NOTSET,
    1: logging.ERROR,
    2: logging.WARN,
    3: logging.INFO,
    4: logging.DEBUG,
}  #: a mapping of `verbose` option counts to logging levels

CONFIG_PATH = os.path.expanduser("~/.gxwf")

def _read_configfile(configfile=CONFIG_PATH):
    try:
        with open(configfile) as f:
            cnfg = yaml.safe_load(f)
        return cnfg
    except FileNotFoundError:
        print("No login details provided - please run gxwf init.")
    except ConnectionError:
        print("Could not connect - check login details are correct.")

def _write_to_file(yml, file_dest=CONFIG_PATH):
    with open(file_dest, "w") as f:
        f.write(yaml.dump(yml, Dumper=yaml.SafeDumper))

def _login():
    login_dict = _read_configfile()
    cnfg = login_dict['logins'][login_dict['active_login']]
    aliases = login_dict['aliases']
    gi = galaxy.GalaxyInstance(cnfg['url'], cnfg['api_key'])
    gi.histories.get_histories()  # just to check the connection
    return gi, cnfg, aliases

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


@click.group()
def entry_point():
    pass

entry_point.add_command(init_group.clikc_test)
# entry_point.add_command(group2.version)


@cli.command()
@click.option("--public/--private", default=False, help="List all public workflows or only user-created?.")
@click.option("--search", '-s', default=False, help="Filter workflows by a string.")
def list(public, search):
    gi, cnfg, aliases = _login()
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

    _tabulate([wf_name, wf_id, wf_alias, steps, owner])


@cli.command()
@click.option("--id", help="Workflow ID to run")
@click.option("--history", default='gxwf_history', help="Name to give history in which workflow will be executed.")
@click.option("--save-yaml", default=False, help="Save inputs as YAML, or perform a dry-run.")
@click.option("--run-yaml", default=False, help="Run from inputs previously saved as YAML.")
def invoke(id, history, save_yaml, run_yaml):
    gi, cnfg, aliases = _login()
    id = aliases.get(id, id)  # if the user provided an alias, return the id; else assume they provided a raw id
    wf = gi.workflows.show_workflow(id)

    click.echo(click.style("Workflow selected: ", bold=True) + wf['name'])
    click.echo(click.style("Input steps:\n\t{:>5}{:>50}".format('Number', 'Name'), bold=True))

    for inp in wf['inputs']:
        click.echo("\t{:>5}{:>50}".format(inp, wf['inputs'][inp]['label']))
    click.echo('_______________________________________________________________\n')

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
            _write_to_file(inputs_dict, save_yaml)
            # with open(save_yaml, 'w') as f:
            #     f.write(yaml.dump(inputs_dict)) 
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
def running(id, history, save_yaml, run_yaml):  # should perhaps rename this invocations, it also shows completed invs
    gi, cnfg, aliases = _login()
    id = aliases.get(id, id)  # if the user provided an alias, return the id; else assume they provided a raw id
    if id:
        invocations = gi.workflows.get_invocations(id)  # will be deprecated, use line below in future
        # invocations = gi.invocations.get_invocations(workflow_id=id)

    else:  # get all invocations - whether this is actually useful or not I don't know, but you get to see a lot of pretty colours
        invocations = gi.invocations.get_invocations()

    for n in range(len(invocations)):
        click.echo(click.style("\nInvocation {}".format(n+1), bold=True))
        invoc_id = invocations[n]['id']

        step_no = 1
        state_colors = {'ok': 'green', 'running': 'yellow', 'error': 'red', 'paused': 'cyan', 'deleted': 'magenta', 'deleted_new': 'magenta', 'new': 'cyan', 'queued': 'yellow'}
        for state in state_colors:
            for k in range(gi.invocations.get_invocation_summary(invoc_id)['states'].get(state, 0)):
                click.echo(click.style(u'\u2B24' + ' Job {} ({})'.format(k+step_no, state), fg=state_colors[state]))
                step_no += k + 1


@cli.command()
# @click.option("--upload", default=False, help="Upload a new dataset")
@click.option("--search", '-s', default=False, help="Filter workflows by a string.")
@click.option("--all", '-a', is_flag=True, help="Get all datasets - not only those in the GXWF history. Warning - may take a REALLY long time.")
def datasets(upload, search, all):
    gi, cnfg, aliases = _login()
    aliases_inverted = {v: k for k, v in aliases.items()}  # need this below

    if all:
        # replace all this rubbish with gi.datasets.get_datasets() when the PR is merged
        dataset_list = []
        for h in gi.histories.get_histories():
            h_name = gi.histories.show_history(h['id'])['name']
            history_list = gi.histories.show_history(h['id'], contents=True)
            for dataset in history_list:
                dataset['history_name'] = h_name
            dataset_list += history_list

    else:
        dataset_list = gi.histories.show_history(cnfg['hid'], contents=True)
        for dataset in dataset_list:
            if 'gxwf' not in dataset['tags']:
                gi.histories.update_dataset(cnfg['hid'], dataset['id'], tags=['gxwf'])

    ds_name, ds_id, ds_alias, ds_ext, ds_hist = ['Dataset name'], ['ID'], ['Alias'], ['Extension'], ['History']

    for ds in dataset_list:
        if search:
            if search not in ds.get('name', ''):
                continue
        if ds.get('deleted') == False and ds.get('state') == 'ok':
            ds_name.append(ds.get('name', ''))
            ds_id.append(ds.get('id', ''))
            ds_alias.append(aliases_inverted.get(ds.get('id'), ''))
            ds_ext.append(str(ds.get('extension', '')))
            ds_hist.append(ds.get('history_name', ''))  # could hide this option when --all is not set

    _tabulate([ds_name, ds_ext, ds_id, ds_alias, ds_hist])


@cli.command()
@click.option("--alias", default=False, help="New alias to add")
@click.option("--id", default=False, help="ID linked to the new alias")
@click.option("--all", '-a', is_flag=True, help="Generate aliases for all (user-owned) workflows and all datasets in the GXWF history.")
def alias(alias, id, all):
    gi, cnfg, aliases = _login()
    # print(aliases)
    if all:
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
    else:
        if not alias:
            alias = namesgenerator.get_random_name()
        click.echo("Alias assigned to ID {}: ".format(id) + click.style(alias, bold=True))
        aliases[alias] = id

    f = _read_configfile()
    f['aliases'] = aliases

    _write_to_file(f)

@cli.command()
def lint():
    from gxformat2.lint import lint_ga
    # have a look at gxformat2
    return

@cli.command()
@click.option("--path", default=False, help="Path to file to be uploaded.")
@click.option("--public/--private", default=False, help="Upload as public or private? (only valid for workflows)")
def upload(path, public):  # could call it import but doubt python will like that ...
    gi, cnfg, aliases = _login()
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
        ds_id = gi.tools.upload_file(path, cnfg['hid'])['outputs'][0]['id']
        gi.histories.update_dataset(cnfg['hid'], ds_id, tags=['gxwf'])


@cli.command()
@click.option("--id", default=False, help="Workflow ID.")
@click.option("--number", '-n', default=False, type=int, help="Number (index) of the invocation.")  # Should this be done using an invocation ID / alias instead?
@click.option("--output", '-o', default=False, help="Output for markdown report.")  # Should this be done using an invocation ID / alias instead?
def report(id, number, output):
    gi, cnfg, aliases = _login()
    id = aliases.get(id, id)  # if the user provided an alias, return the id; else assume they provided a raw id
    inv_id = gi.workflows.get_invocations(id)[number]['id']  # will be deprecated, use line below in future
    # invocation = gi.invocations.get_invocations(workflow_id=id)[number]

    md = gi.invocations.get_invocation_report(inv_id)['markdown']
    with open(output, 'w') as f:
        f.write(md)

    # Another idea: add --report as an option to invoke subcommand?
