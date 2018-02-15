#!/usr/bin/python
import logging
import sys
import time
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils


def main(argv):
    mojo_utils.setup_logging()
    overcloud_novarc = mojo_utils.get_overcloud_auth()
    keystone_session = mojo_os_utils.get_keystone_session(overcloud_novarc)
    aodhc = mojo_os_utils.get_aodh_session_client(keystone_session)
    nova_client = mojo_os_utils.get_nova_session_client(keystone_session)

    servers = nova_client.servers.list()
    assert servers, "No servers available for AODH testing"
    if servers:
        alarm_name = 'mojo_instance_off'
        server = servers[0]
        assert server.status == 'ACTIVE', "Server {} not active".format(
            server.name)
        logging.info('Using server {} for aodh test'.format(server.name))
        server = nova_client.servers.find(name=server.name)
        logging.info('Deleting alarm {} if it exists'.format(alarm_name))
        mojo_os_utils.delete_alarm(aodhc, alarm_name)
        logging.info('Creating alarm {}'.format(alarm_name))
        alarm_def = {
            'type': 'event',
            'name': alarm_name,
            'description': 'Instance powered OFF',
            'alarm_actions': ['log://'],
            'ok_actions': ['log://'],
            'insufficient_data_actions': ['log://'],
            'event_rule': {
                'event_type': 'compute.instance.power_off.*',
                'query': [{'field': 'traits.instance_id',
                           'op': 'eq',
                           'type': 'string',
                           'value': server.id}]}}
        alarm_info = aodhc.alarm.create(alarm_def)
        logging.info('Stopping server {}'.format(server.name))
        server.stop()
        for i in range(10):
            alarm_state = mojo_os_utils.get_alarm_state(
                aodhc,
                alarm_info['alarm_id'])
            if alarm_state == 'alarm':
                logging.info('Alarm triggered')
                server.start()
                break
            else:
                time.sleep(5)
        else:
            server.start()
            raise Exception("Alarm failed to trigger")


if __name__ == "__main__":
    sys.exit(main(sys.argv))