#!/usr/bin/env python
import six
import re
import argparse
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import logging


def get_upgrade_targets(target_release, current_versions):
    upgrade_list = []
    for svc in current_versions.keys():
        if current_versions[svc] < target_release:
            upgrade_list.append(svc)
    return upgrade_list


def main(argv):
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target_release",
        default='auto', help="Openstack release name to upgrade to or 'auto' "
                             "to have script upgrade based on the lowest value"
                             "across all services")
    options = parser.parse_args()
    target_release = mojo_utils.parse_mojo_arg(options, 'target_release')
    principle_services = mojo_utils.get_principle_services()
    current_versions = mojo_os_utils.get_current_os_versions(
        principle_services)
    if target_release == 'auto':
        # If in auto mode find the lowest value openstack release across all
        # services and make sure all servcies are upgraded to one release
        # higher than the lowest
        lowest_release = mojo_os_utils.get_lowest_os_version(current_versions)
        target_release = mojo_os_utils.next_release(lowest_release)[1]
    # Get a list of services that need upgrading
    needs_upgrade = get_upgrade_targets(target_release, current_versions)
    for service in mojo_os_utils.UPGRADE_SERVICES:
        if service['name'] not in principle_services:
            continue
        if service['name'] not in needs_upgrade:
            logging.info('Not upgrading {} it is at {} or higher'.format(
                service['name'],
                target_release)
            )
            continue
        logging.info('Upgrading {} to {}'.format(service['name'],
                                                 target_release))
        ubuntu_version = mojo_utils.get_ubuntu_version(service['name'])
        option = "{}=cloud:{}-{}/proposed".format(
            service['type']['origin_setting'],
            ubuntu_version, target_release
        )
        mojo_utils.juju_set(service['name'], option, wait=False)
        # NOTE: For liberty->mitaka upgrade ceilometer-agent gets stuck at
        # 'Services not running that should be: memcached' after nova-compute
        # upgrade, and test would wait forever. Therefore we upgrade
        # ceilometer-agent immediately after nova-compute.
        if service['name'] == 'nova-compute':
            mojo_utils.juju_set('ceilometer-agent', option, wait=False)
        mojo_utils.juju_wait_finished()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
