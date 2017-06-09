import logging

import dcos_launch.util

log = logging.getLogger(__name__)

import json
from dcos_test_utils.dcos_api_session import DcosApiSession, DcosUser
from dcos_test_utils.helpers import Host
import retrying

class BareClusterLauncher(dcos_launch.util.AbstractLauncher):
    """ Launches a homogeneous cluster of plain AMIs intended for onprem DC/OS
    """

    def __init__(self, config: dict):
        dcos_user = DcosUser({"uid" : dcos_launch.util.set_from_env('ROOT_DCOS_USER'),
                              "password" : dcos_launch.util.set_from_env('ROOT_DCOS_PW')})
        dcos_url = config['dcos_url']
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
            master_json = dict(app_json)
            master_json.update({
                'id': "/" + self.config['deployment_name'] + "/" +"masters",
                'instances': self.config['num_masters'],
            })
            #master_json["container"]["docker"]["portMappings"] = [{"containerPort": 22, "hostPort": 0, "protocol": "tcp", "name": "ssh"}]
            #master_json["labels"] = {"HAPROXY_0_GROUP": "external"}
            priv_agent_json = dict(app_json)
            priv_agent_json.update({
                'id': "/" + self.config['deployment_name'] + "/" + "private-agents",
                'instances': self.config['num_private_agents'],
                'cpus': self.config['agent_cpus'],
                'mem': self.config['agent_mem']
            })
            pub_agent_json = dict(app_json)
            pub_agent_json.update({
                'id': "/" + self.config['deployment_name'] + "/" + "public-agents",
                'instances': self.config['num_public_agents'],
                'cpus': self.config['agent_cpus'],
                'mem': self.config['agent_mem']
            })
            bootstrap_json = dict(app_json)
            bootstrap_json.update({
                'id': "/" + self.config['deployment_name'] + "/" + "bootstrap",
                'instances': 1,
                'cpus': 1,
                'mem': 512
            })
            try:
                res_masters = self.root_dcos_api.marathon.deploy_app(master_json, timeout=120, check_health=False, ignore_failed_tasks=False)
                res_priv_agent = self.root_dcos_api.marathon.deploy_app(priv_agent_json, timeout=120, check_health=False, ignore_failed_tasks=False)
                res_pub_agent = self.root_dcos_api.marathon.deploy_app(pub_agent_json, timeout=120, check_health=False, ignore_failed_tasks=False)
                res_bootstrap = self.root_dcos_api.marathon.deploy_app(bootstrap_json, timeout=120, check_health=False, ignore_failed_tasks=False)
                self.config["master_ips"] = [Host(endpoint.ip, endpoint.ip) for endpoint in res_masters]
                self.config["private_agent_ips"] = [Host(endpoint.ip, endpoint.ip) for endpoint in res_priv_agent]
                self.config["public_agent_ips"] = [Host(endpoint.ip, endpoint.ip) for endpoint in res_pub_agent]
                self.config["bootstrap_ip"] = Host(res_bootstrap[0].ip, res_bootstrap[0].ip)
                return self.config
            #except retrying.RetryError:
            except:
                log.error("Hit an error on deploy marathon apps. Deleting the stack.")
                res = self.root_dcos_api.marathon.destroy_app_group("/" + self.config['deployment_name'], timeout=120)

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
        self.config["master_ips"] = [Host(i[0], i[1]) for i in self.config["master_ips"]]
        self.config["private_agent_ips"] = [Host(i[0], i[1]) for i in self.config["private_agent_ips"]]
        self.config["public_agent_ips"] = [Host(i[0], i[1]) for i in self.config["public_agent_ips"]]
        self.config["bootstrap_ip"] = Host(self.config["bootstrap_ip"][0], self.config["bootstrap_ip"][1])

        instances = self.config["master_ips"] + self.config["private_agent_ips"] + (
            self.config["public_agent_ips"] + [self.config["bootstrap_ip"]]
        )
        return instances

    def describe(self):
        #raise NotImplementedError()
        #return {'host_list': dcos_launch.util.convert_host_list(self.get_hosts())}
        self.get_hosts()


    #def test(self, args, env):
    #    raise NotImplementedError('Bare clusters cannot be tested!')

    def delete(self):
        # We can just delete the folder, it'll recursively delete everything else.
        res = self.root_dcos_api.marathon.destroy_app_group("/" + self.config['deployment_name'], timeout=120)

    def wait(self):
        # actually should wait until SSH is up
        #raise NotImplementedError()
        self.get_hosts()
        if self.get_hosts is not None:
            return True
