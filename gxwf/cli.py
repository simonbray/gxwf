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

from yaml import SafeLoader

from .__init__ import __version__

from bioblend import galaxy

LOGGING_LEVELS = {
    0: logging.NOTSET,
    1: logging.ERROR,
    2: logging.WARN,
    3: logging.INFO,
    4: logging.DEBUG,
}  #: a mapping of `verbose` option counts to logging levels

CONFIG_PATH = os.path.expanduser("~/.gxwf")

def _login():
    with open(CONFIG_PATH) as f: 
        cnfg = yaml.safe_load(f) 
        gi = galaxy.GalaxyInstance(cnfg['url'], cnfg['api_key'])
    return gi

class Info(object):
    """
    An information object to pass data between CLI functions.
    """

    def __init__(self):  # Note: This object must have an empty constructor.
        self.verbose: int = 0


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


@cli.command()
@pass_info
def hello(_: Info):
    """
    Say 'hello' to the nice people.
    """
    click.echo(f"gxwf says 'hello'")


@cli.command()
def version():
    """
    Get the library version.
    """
    click.echo(click.style(f"{__version__}", bold=True))

@cli.command()
@click.option("--url", help="URL of Galaxy server.")
@click.option("--api-key", help="API key")
def init(url, api_key):
    """
    Log into a Galaxy server.
    """
    if os.path.exists(CONFIG_PATH):
        overwrite = click.prompt("Your login credentials are already saved here: {}. Do you want to overwrite? [y/n]".format(CONFIG_PATH))
        if overwrite not in ['Y', 'y']:
            return 0
    try:
        gi = galaxy.GalaxyInstance(url, api_key)
    except Exception as e:
        click.echo("Accessing server failed with '{}'".format(e))
    else:
        with open(CONFIG_PATH, "w+") as f:
            f.write(
"""url: {}
api_key: {}""".format(url, api_key))
    # print(url, api_key)
    click.echo(click.style(f"{__version__}", bold=True))


@cli.command()
@click.option("--public/--private", default=False, help="List all public workflows or only user-created?.")
@click.option("--search", '-s', default=False, help="Filter workflows by a string.")
def list(public, search):
    gi = _login()
    if search:
        workflows = [wf for wf in gi.workflows.get_workflows(published=public) if search in wf['name'] or search in wf['owner']] 
    else:
        workflows = gi.workflows.get_workflows(published=public)
    click.echo(click.style("{:>100}{:>30}{:>10}{:>20}".format('Workflow name', 'ID', 'Steps', 'Owner'), bold=True))
    for wf in workflows:
        click.echo("{:>100}{:>30}{:>10}{:>20}".format(wf['name'], wf['id'], wf['number_of_steps'], wf['owner']))


@cli.command()
@click.option("--id", help="Workflow ID to run")
@click.option("--history", default='gxwf_history', help="Name to give history in which workflow will be executed.")
@click.option("--save-yaml", default=False, help="Save inputs as YAML, or perform a dry-run.")
@click.option("--run-yaml", default=False, help="Run from inputs previously saved as YAML.")

def invoke(id, history, save_yaml, run_yaml):
    gi = _login()
    wf = gi.workflows.show_workflow(id)
    click.echo(click.style("Workflow selected: ", bold=True) + wf['name'])
    # click.echo(click.style("Steps:\n\t", bold=True))
    # for step in wf['steps']:
    #     # tool_id = wf['steps'][step]['tool_id'].split('/')[4] if wf['steps'][step]['tool_id'] else 'None'
    #     # tool_version = 
    #     click.echo("\t{:>5}{:>100}".format(step, str(wf['steps'][step]['tool_id'])))
    click.echo(click.style("Input steps:\n\t{:>5}{:>50}".format('Number', 'Name'), bold=True))
    for inp in wf['inputs']:
        # tool_id = wf['steps'][step]['tool_id'].split('/')[4] if wf['steps'][step]['tool_id'] else 'None'
        # tool_version = 
        click.echo("\t{:>5}{:>50}".format(inp, wf['inputs'][inp]['label']))
    click.echo('_______________________________________________________________\n')
    hist = gi.histories.create_history(history)     
    if not run_yaml:
        hist = gi.histories.create_history(history) 
        inputs_dict = {'params': {}, 'inputs': {}}
        click.echo(click.style("Enter inputs:", bold=True))
        for inp in wf['inputs']:
            inp_val = click.prompt("Input {}: ".format(inp) + click.style("{}".format(wf['inputs'][inp]['label']), bold=True))
            if os.path.exists(inp_val):
                # use local files or datasets?
                dataset = gi.tools.upload_file(inp_val, hist['id'])
                inputs_dict['inputs'][inp] =  {'id': dataset['outputs'][0]['id'], 'src': dataset['outputs'][0]['hda_ldda']}
            else:
                # should do a check that params are getting correct inputs, e.g. int -> int, text -> text etc
                inputs_dict['params'][inp] = {'param': wf['inputs'][inp]['label'], 'value': inp_val}

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
    gi.workflows.invoke_workflow(id, inputs=inputs_dict['inputs'], params=inputs_dict['params'], history_id=hist)
    