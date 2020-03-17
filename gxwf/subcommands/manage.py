import click
import os
import yaml

from bioblend import galaxy

from requests import ConnectionError as RequestsConnectionError
from yaml import SafeLoader

from gxwf import utils


def _open_cnfg():
    try:
        with open(utils.CONFIG_PATH, "r") as f:
            return yaml.load(f.read(), Loader=SafeLoader)

    except FileNotFoundError:
        return {'active_login': None, 'logins': {}, 'aliases': {}}


@click.command()
@click.option("--url", required=True, help="URL of Galaxy server")
@click.option("--api-key", required=True, help="API key")
@click.option("--name", required=True, help="Provide a handy name to refer to a login")
def add_login(url, api_key, name):
    """
    Add a new login to the gxwf config file, specifying URL of the Galaxy server you want to log in to, the API key for your account, and a handy name to refer to the login with.
    
    When a new login is added, a new history with the name `GXWF datasets` is also created to store datasets used or created by GXWF.
    """
    login_dict = _open_cnfg()

    try:
        gi = galaxy.GalaxyInstance(url=url, key=api_key)
        hid = gi.histories.create_history(name='GXWF datasets')['id']
        gi.histories.create_history_tag(hid, 'gxwf')
    except (ConnectionError, RequestsConnectionError) as e:
        click.echo("Accessing server failed with '{}'".format(e))
    else:
        if name in login_dict['logins']:
            click.echo('A login already exists with the name: {}. Please choose another, or first delete the existing login using `gxwf manage delete`.'.format(name))
            return
        login_dict['logins'][name] = {'url': url, 'api_key': api_key, 'hid': hid}
        login_dict['active_login'] = name  # automatically switch to the new login
        click.echo("New login {} created.".format(name))
    utils._write_to_file(login_dict)

@click.command()
def view():
    """
    View all login details referenced in the gxwf config file.
    """
    login_dict = _open_cnfg()
    login_name, login_url, login_api, login_hid = ['Login name'], ['URL'], ['API key'], ['History ID']
    for lgn in login_dict['logins']:
        login_name.append(lgn)
        login_url.append(login_dict['logins'][lgn]['url'])
        login_api.append(login_dict['logins'][lgn]['api_key'])
        login_hid.append(login_dict['logins'][lgn]['hid'])
    click.echo("You are currently using active login: " + click.style(login_dict['active_login'], bold=True))
    utils._tabulate([login_name, login_url, login_api, login_hid])

@click.command()
@click.argument('name') #, required=True, help="Switch to a different login, referencing its name.")
def switch(name):
    """
    Switch to a different login, referencing its name.
    """
    login_dict = _open_cnfg()
    if login_dict['active_login'] == name:
        click.echo("Login with name {} is already activated.".format(name))
    elif name in login_dict['logins']:
        login_dict['active_login'] = name
        click.echo("Login with name {} activated.".format(name))
    else:
        click.echo('Sorry, no login is recorded under the name {}.'.format(name))
    utils._write_to_file(login_dict)

@click.command()
@click.argument('name') #, required=True, help="Switch to a different login, referencing its name.")
def delete(name):
    """
    Delete a login which is no longer needed, by referencing its name.
    """
    login_dict = _open_cnfg()
    if login_dict['active_login'] == name:
        click.echo('Sorry, {} is the active login and cannot be deleted. Please activate a different login first.'.format(name))
    else:
        try:
            del login_dict['logins'][name]
        except KeyError:
            click.echo('Sorry, no login is recorded under the name {}.'.format(name))
    utils._write_to_file(login_dict)
