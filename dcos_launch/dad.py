import logging

import dcos_launch.util

log = logging.getLogger(__name__)

import json
from dcos_test_utils.dcos_api_session import DcosApiSession, DcosUser
from dcos_test_utils.helpers import Host

class BareClusterLauncher(dcos_launch.util.AbstractLauncher):
    """ Launches a homogeneous cluster of plain AMIs intended for onprem DC/OS
    """

    def __init__(self, config: dict):
        dcos_user = DcosUser({"uid" : dcos_launch.util.set_from_env('ROOT_DCOS_USER'),
                              "password" : dcos_launch.util.set_from_env('ROOT_DCOS_PW')})
        dcos_url = config['dcos_url']
        print (dcos_user.credentials)
        #self.root_dcos_api = DcosApiSession(dcos_url, None, None, None, "root", CI_CREDENTIALS)
        self.root_dcos_api = DcosApiSession(dcos_url, None, None, None, "root", dcos_user)
        self.root_dcos_api._authenticate_default_user()
        self.config = config
    def create(self):
        """ Amend the config to add a template_body and the appropriate parameters
        """
        # make marathon dict for app, taking parameters from config
        num_instances = (1 + self.config['num_masters'] + self.config['num_public_agents'] +
                        self.config['num_private_agents'])
        with open(self.config['marathon_json_filename']) as data_file:
            app_json = json.load(data_file)
            app_json.update({
                'id': self.config['deployment_name'],
                'instances': num_instances,
            })
            res = self.root_dcos_api.marathon.deploy_app(app_json, timeout=120, check_health=False, ignore_failed_tasks=False)
            self.host_ips = [Host(endpoint.ip, endpoint.ip) for endpoint in res]
            self.config["host_ips"] = self.host_ips
            return self.config

        #template_parameters = {
        #    'AllowAccessFrom': self.config['admin_location'],
        #    # cluster size is +1 for the bootstrap node
        #    'ClusterSize': (1 + self.config['num_masters'] + self.config['num_public_agents'] +
        #                    self.config['num_private_agents']),
        #    'InstanceType': self.config['instance_type'],
        #    'AmiCode': self.config['instance_ami']}
        #if not self.config['key_helper']:
        #    template_parameters['KeyName'] = self.config['aws_key_name']
        #self.config.update({
        #    'template_body': dcos_test_utils.aws.template_by_instance_type(self.config['instance_type']),
        #    'template_parameters': template_parameters})
        #return super().create()

    def get_hosts(self):
        instances = self.config["host_ips"]
        return [Host(i[0], i[1]) for i in instances]

    def describe(self):
        raise NotImplementedError()
        #return {'host_list': dcos_launch.util.convert_host_list(self.get_hosts())}

    def test(self, args, env):
        raise NotImplementedError('Bare clusters cannot be tested!')

    def delete(self):
        raise NotImplementedError()

    def wait(self):
        # actually should wait until SSH is up
        #raise NotImplementedError()
        if self.config["host_ips"] is not None:
            return True
