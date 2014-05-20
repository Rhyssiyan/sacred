#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import ast
import re
import textwrap
from docopt import docopt
import sys
from commands import help_for_command

from sacred.observers import MongoDBReporter


__all__ = ['parse_args', 'get_config_updates', 'get_observers']


USAGE_TEMPLATE = """Usage:
  {program_name} [run] [(with UPDATE...)] [-m DB]
  {program_name} help [COMMAND]
  {program_name} (-h | --help)
  {program_name} COMMAND [(with UPDATE...)]

{description}

Options:
  -h --help             Print this help message and exit
  -m DB --mongo_db=DB   Add a MongoDB Observer to the experiment

Arguments:
  DB        Database specification. Can be [host:port:]db_name
  UPDATE    Configuration assignments of the form foo.bar=17
  COMMAND   Custom command to run
"""


DB_NAME_PATTERN = r"[_A-Za-z][0-9A-Za-z!#%&'()+\-;=@\[\]^_{}]{0,63}"
HOSTNAME_PATTERN = \
    r"(?=.{1,255}$)"\
         r"[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?"\
    r"(?:\.[0-9A-Za-z](?:(?:[0-9A-Za-z]|-){0,61}[0-9A-Za-z])?)*"\
    r"\.?"
URL_PATTERN = "(?:" + HOSTNAME_PATTERN + ")" + ":" + "(?:[0-9]{1,5})"

DB_NAME = re.compile("^" + DB_NAME_PATTERN + "$")
URL = re.compile("^" + URL_PATTERN + "$")
URL_DB_NAME = re.compile("^(?P<url>" + URL_PATTERN + ")" + ":" +
                         "(?P<db_name>" + DB_NAME_PATTERN + ")$")


def parse_args(argv, description="", commands=None, print_help=True):
    usage = _format_usage(argv[0], description, commands)
    args = docopt(usage, [str(a) for a in argv[1:]], help=help)
    if not args['help'] or not print_help:
        return args

    if args['COMMAND'] is None:
        print(usage)
        sys.exit()
    else:
        print(help_for_command(commands[args['COMMAND']]))
        sys.exit()


def get_config_updates(updates):
    config_updates = {}
    if not updates:
        return config_updates
    for upd in updates:
        if upd == '':
            continue
        path, sep, value = upd.partition('=')
        assert sep == '=', "Missing '=' in update '%s'" % upd
        current_option = config_updates
        split_path = path.split('.')
        for p in split_path[:-1]:
            if p not in current_option:
                current_option[p] = dict()
            current_option = current_option[p]
        current_option[split_path[-1]] = _convert_value(value)
    return config_updates


def get_observers(args):
    observers = []
    if args['--mongo_db']:
        url, db_name = _parse_mongo_db_arg(args['--mongo_db'])
        mongo = MongoDBReporter(db_name=db_name, url=url)
        observers.append(mongo)

    return observers


def _format_usage(program_name, description, commands=None):
    usage = USAGE_TEMPLATE.format(
        program_name=program_name,
        description=description.strip())

    if commands:
        usage += "\nCommands:\n"
        cmd_len = max([len(c) for c in commands] + [8])
        command_doc = {k: _get_first_line_of_docstring(v)
                       for k, v in commands.items()}
        for k, v in command_doc.items():
            usage += ("  {:%d}  {}\n" % cmd_len).format(k, v)
    return usage


def _get_first_line_of_docstring(f):
    return textwrap.dedent(f.__doc__ or "").strip().split('\n')[0]


def _convert_value(value):
    try:
        return ast.literal_eval(value)
    except ValueError:
        # use as string if nothing else worked
        return value


def _parse_mongo_db_arg(mongo_db):
    if DB_NAME.match(mongo_db):
        return 'localhost:27017', mongo_db
    elif URL.match(mongo_db):
        return mongo_db, 'sacred'
    elif URL_DB_NAME.match(mongo_db):
        m = URL_DB_NAME.match(mongo_db)
        return m.group('url'), m.group('db_name')
    else:
        raise ValueError('mongo_db argument must have the form "db_name" or '
                         '"host:port[:db_name]" but was %s' % mongo_db)