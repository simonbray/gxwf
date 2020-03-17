import click
import os
import yaml
import json

from bioblend import galaxy

from requests import ConnectionError as RequestsConnectionError
from bioblend import ConnectionError as BioblendConnectionError
from yaml import SafeLoader

from gxwf import utils


def invocations(id_):
    gi, cnfg, aliases = utils._login()
    if id_:
        id_ = aliases.get(id_, id_)  # if the user provided an alias, return the id; else assume they provided a raw id
        invocations = gi.workflows.get_invocations(id_)  # will be deprecated, use line below in future
        # invocations = gi.invocations.get_invocations(workflow_id=id_)

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
