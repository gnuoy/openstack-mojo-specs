#!/usr/bin/python

import subprocess
import yaml
import os
import mojo
import logging


def get_juju_status(service=None):
    cmd = ['juju', 'status']
    if service:
        cmd.append(service)
    status_file = subprocess.Popen(cmd, stdout=subprocess.PIPE).stdout
    return yaml.load(status_file)


def get_juju_units(juju_status=None):
    if not juju_status:
        juju_status = get_juju_status()
    units = []
    for service in juju_status['services']:
        if 'units' in juju_status['services'][service]:
            for unit in juju_status['services'][service]['units']:
                units.append(unit)
    return units


def remote_run(unit):
    cmd = ['juju', 'run', '--unit', unit, 'uname -a']
    FNULL = open(os.devnull, 'w')
    return not subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)


def juju_set(service, option):
    subprocess.check_call(['juju', 'set', service, option])


def get_undercload_auth():
    juju_env = subprocess.check_output(['juju', 'switch']).strip('\n')
    juju_env_file = open(os.environ['HOME'] + "/.juju/environments.yaml", 'r')
    juju_env_contents = yaml.load(juju_env_file)
    novarc_settings = juju_env_contents['environments'][juju_env]
    auth_settings = {
        'OS_AUTH_URL': novarc_settings['auth-url'],
        'OS_TENANT_NAME': novarc_settings['tenant-name'],
        'OS_USERNAME': novarc_settings['username'],
        'OS_PASSWORD': novarc_settings['password'],
        'OS_REGION_NAME': novarc_settings['region'],
    }
    return auth_settings


def get_overcloud_auth(juju_status=None):
    if not juju_status:
        juju_status = get_juju_status()
    # xxx Need to account for https
    transport = 'http'
    unit = juju_status['services']['keystone']['units'].itervalues().next()
    address = unit['public-address']
    auth_settings = {
        'OS_AUTH_URL': '%s://%s:5000/v2.0' % (transport, address),
        'OS_TENANT_NAME': 'admin',
        'OS_USERNAME': 'admin',
        'OS_PASSWORD': 'openstack',
        'OS_REGION_NAME': 'RegionOne',
    }
    return auth_settings


def get_mojo_config(filename):
    spec = mojo.Spec(os.environ['MOJO_SPEC_DIR'])
    config_file = spec.get_config(filename, stage=os.environ['MOJO_STAGE'])
    logging.info('Using config %s' % (config_file))
    return yaml.load(file(config_file, 'r'))


def get_charm_dir():
    return os.path.join(os.environ['MOJO_REPO_DIR'],
                        os.environ['MOJO_SERIES'])


def sync_charmhelpers(charmdir):
    p = subprocess.Popen(['make', 'sync'], cwd=charmdir)
    p.communicate()


def sync_all_charmhelpers():
    charm_base_dir = get_charm_dir()
    for direc in os.listdir(charm_base_dir):
        charm_dir = os.path.join(charm_base_dir, direc)
        if os.path.isdir(charm_dir):
            sync_charmhelpers(charm_dir)


def parse_mojo_arg(options, mojoarg, multiargs=False):
    if mojoarg.upper() in os.environ:
        if multiargs:
            return os.environ[mojoarg.upper()].split()
        else:
            return os.environ[mojoarg.upper()]
    else:
        return getattr(options, mojoarg)
