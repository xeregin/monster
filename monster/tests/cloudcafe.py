"""
Module to test OpenStack deployments with CloudCafe
"""

import os

from monster import util
from monster.util import Logger
from monster.tests.test import Test
from monster.server_helper import run_cmd

logger = Logger("cloudcafe")

class CloudCafe(Test):
    def __init__(self, deployment):
        super(CloudCafe, self).__init__(deployment)
        logger.set_log_level()

    def test(self):
        raise NotImplementedError

    def get_endpoint(self):
        auth_url = "http://{0}:5000".format(self.deployment.horizon_ip())
        return auth_url

    def get_admin_user(self):
        override = self.deployment.environment.override_attributes
        keystone = override['keystone']
        user = keystone['admin_user']
        users = keystone['users']
        password = users[user]['password']
        tenant = users[user]['roles']['admin'][0]
        return (user, password, tenant)

    def get_non_admin_user(self):
        override = self.deployment.environment.override_attributes
        keystone = override['keystone']
        users = keystone['users']
        non_admin_users = (user for user in users.keys()
                           if "admin" not in users[user]['roles'].keys())
        user = next(non_admin_users)
        password = users[user]['password']
        tenant = users[user]['roles']['Member'][0]
        return (user, password, tenant)

    def get_image_ids(self):
        nova = self.deployment.openstack_clients.novaclient
        image_ids = (i.id for i in nova.images.list())
        try:
            image_id1 = next(image_ids)
        except StopIteration:
            # No images
            exit(1)
        try:
            image_id2 = next(image_ids)
        except StopIteration:
            # Only one image
            image_id2 = image_id1
        return (image_id1, image_id2)

    def get_admin_ids(self, user, tenant, project):
        keystone = self.deployment.openstack_clients.keystoneclient
        user_id = keystone.user_id
        tenant_id = keystone.tenant_id
        project_id = keystone.project_id
        return (tenant_id, user_id, project_id)

    def export_variables(self, section, values):
        for variable, value in values.items():
            export = "CAFE_{0}_{1}".format(section, variable)
            os.environ[export] = value

    def config(self, cmd, network_name="ENV01-FLAT", files=None):
        endpoint = self.get_endpoint()
        admin_user, admin_password, admin_tenant = self.get_admin_user()
        admin_tenant_id, admin_user_id, admin_project_id = self.get_admin_ids(
            admin_user, admin_password, admin_tenant)
        second_user, second_password, second_tenant = self.get_non_admin_user()
        primary_image_id, secondary_image_id = self.get_image_ids()

        networks = "{'%s':{'v4': True, 'v6': False}}" % network_name

        admin_endpoint = endpoint.replace("5000", "35357")

        args = {
            "compute_admin_user": {
                "username": admin_user,
                "password": admin_password,
                "tenant_name": admin_tenant
                },
            "user_auth_config": {
                "endpoint": endpoint
                },
            "coumpute_admin_auth_config": {
                "endpoint": endpoint
                },
            "user": {
                # "username": admin_user,
                # "password": admin_password,
                # "tenant_name": admin_tenant,
                "tenant_id": admin_tenant_id,
                "user_id": admin_user_id,
                "project_id": admin_project_id
                },
            "compute_secondary_user": {
                "username": second_user,
                "password": second_password,
                "tenant_name": second_tenant
                },
            "images": {
                "primary_image": primary_image_id,
                "secondary_image": secondary_image_id
                },
            "servers": {
                "network_for_ssh": network_name,
                "expected_networks": networks,
                "default_network": network_name
                },
            "identity_v2_user": {
                "username": second_user,
                "password": second_password,
                "tenant_name": second_tenant,
                "authentication_endpoint": endpoint
                },
            "identity_v2_admin": {
                "username": admin_user,
                "password": admin_password,
                "tenant_name": admin_tenant,
                "authentication_endpoint": admin_endpoint
                }
            }

        for section, values in args.items():
            self.export_variables(section, values)

        run_cmd(cmd)
