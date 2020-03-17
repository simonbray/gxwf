import yaml
from bioblend import galaxy
import os
import click

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
