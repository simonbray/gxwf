import click
import os

from .__init__ import __version__
from .subcommands import manage as manage_commands
from .subcommands import invoke as invoke_commands
from .subcommands import list_workflows as list_commands
from .subcommands import datasets as dataset_commands
from .subcommands import alias as alias_commands
from .subcommands import invocations as invocation_commands
from .subcommands import upload as upload_commands

from gxwf import utils


class Info(object):
    """
    An information object to pass data between CLI functions.
    """

    def __init__(self):  # Note: This object must have an empty constructor.
        self.verbose: int = 0


# class GxwfInvocation(object):
#     def __init__(self, gi, invoc_id):
#         self.invoc_id = invoc_id
#         self.gi = gi
    
#     def __iter__(self):
#         self.summary = self.gi.invocations.get_invocation_summary(self.invoc_id)
#         return self.summary['states'].get('ok', 0) / sum(self.summary['states'].values())

# pass_info is a decorator for functions that pass 'Info' objects.
#: pylint: disable=invalid-name
pass_info = click.make_pass_decorator(Info, ensure=True)

@click.group()
@click.option("--verbose", "-v", count=True, help="Enable verbose output.")
@pass_info
def cli(info: Info, verbose: int):
    """
    Run gxwf, a tool for executing and managing scientific workflows on Galaxy.

    To get started for the first time, run `gxwf manage add-login --help` to add login details.
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

@cli.group()
def manage():
    """
    Add, modify or remove login details for a Galaxy server.

    Multiple user accounts can be managed concurrently using gxwf.
    """
    pass

manage.add_command(manage_commands.add_login)
manage.add_command(manage_commands.switch)
manage.add_command(manage_commands.delete)
manage.add_command(manage_commands.view)

@cli.command(name="list")
@click.option("--public/--private", default=False, help="List all public workflows or only user-created?")
@click.option("--search", '-s', default=False, help="Filter workflows by a string.")
def list_(public, search):
    """
    Obtain a list of workflows - either those created/imported by the user, or alternatively all publicly available on the server.

    Results can also be filtered using --search.
    """
    return list_commands.list_workflows(public, search)


@cli.group()
# @click.argument('id')  #"--id", help="Workflow ID to run")
def invoke():
    """
    Invoke a command using its ID or assigned alias.
    """
    pass
    # return invoke_commands.invoke_from_params(id_, history, save_yaml)

invoke.add_command(invoke_commands.from_yaml)
invoke.add_command(invoke_commands.from_params)

@cli.command()
@click.option("--search", '-s', default=False, help="Filter workflows by a string.")
@click.option("--all", '-a', is_flag=True, help="Get all datasets - not only those in the GXWF history. Warning - may take a REALLY long time.")
def datasets(search, all):
    """
    Get a list of datasets in the `GXWF datasets` history which is accessed by gxwf.

    To access all of a user's datasets, use the --all flag. Note this can take quite a long time to complete.

    Results can also be filtered using --search.
    """
    return dataset_commands.datasets(search, all)


@cli.command()
@click.argument("path")  #, help="Path to file to be uploaded.")
@click.option("--file-type", default='auto', help="File type, if a dataset is uploaded. If not set, Galaxy will attempt to identify the correct datatype automatically.")
@click.option("--public/--private", default=False, help="Upload as public or private? (only valid for workflows)")
def upload(path, public, file_type=None):  # could also call it import
    """
    Upload a file or workflow to Galaxy.

    Currently, gxwf attempts to upload any file with a .ga extension as a workflow, and all others as datasets.
    """
    return upload_commands.upload(path, public, file_type)


@cli.group()
def alias():
    """
    Assign aliases to workflows or datasets. These can then be used in place of IDs for any gxwf subcommand.
    """
    pass

alias.add_command(alias_commands.add_single)
alias.add_command(alias_commands.add_all)
alias.add_command(alias_commands.list_)
alias.add_command(alias_commands.delete)



@cli.command()
@click.option("--id", 'id_', default=False, help="Workflow ID invoked; if not specified, all invocations will be returned")
def invocations(id_):
    """
    List workflow invocations. If --id is specified, limits list to a specific workflow; else, shows all invocations.
    """
    return invocation_commands.invocations(id_)

