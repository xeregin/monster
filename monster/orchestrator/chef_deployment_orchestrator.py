from chef import autoconfigure
from chef import Environment

from monster import util
from monster.config import Config
from monster.orchestrator.deployment_orchestrator import DeploymentOrchestrator
from monster.nodes.chef_node_wrapper_factory import ChefNodeWrapperFactory
from monster.provisioners.provisioner import get_provisioner
from monster.features.node_feature import ChefServer
from monster.deployments.chef_deployment import ChefDeployment
from monster.environments.chef_environment_wrapper import \
    ChefEnvironmentWrapper


class ChefDeploymentOrchestrator(DeploymentOrchestrator):
    def create_deployment_from_file(self, name, template, branch,
                                    provisioner_name):
        """
        Returns a new deployment given a deployment template at path
        :param name: name for the deployment
        :type name: string
        :param name: name of template to use
        :type name: string
        :param branch: branch of the RCBOPS chef cookbook repo to use
        :type branch:: string
        :param provisioner_name: provisioner to use for nodes
        :type provisioner_name: str
        :rtype: ChefDeployment
        """
        util.logger.info("Building deployment object for {0}".format(name))
        provisioner = get_provisioner(provisioner_name)

        if Environment(name, api=self.local_api).exists:
            util.logger.info("Using previous deployment:{0}".format(name))
            return self.load_deployment_from_name(name)

        environment = ChefEnvironmentWrapper(name, self.local_api,
                                             description=name)

        template = Config.fetch_template(template, branch)

        os, product, features = template.fetch('os', 'product', 'features')

        deployment = ChefDeployment(name, os, branch, environment,
                                    provisioner, "provisioning", product,
                                    features=features)
        deployment.nodes = provisioner.build_nodes(template, deployment,
                                                   ChefNodeWrapperFactory)
        return deployment

    def load_deployment_from_name(self, name):
        """
        Rebuilds a Deployment given a deployment name
        :param name: name of deployment
        :type name: string
        :rtype: ChefDeployment
        """
        default, override, remote_api = self.load_environment_attributes(name)
        env = ChefEnvironmentWrapper(name, self.local_api, description=name,
                                     default=default, override=override,
                                     remote_api=remote_api)

        provisioner = get_provisioner(env.provisioner)

        deployment = ChefDeployment(name, env.os_name, env.branch, env,
                                    provisioner, "provisioning", env.product,
                                    features=env.features)
        deployment.nodes = provisioner.load_nodes(env, deployment,
                                                  ChefNodeWrapperFactory)
        return deployment

    def load_environment_attributes(self, name):
        local_env = Environment(name, self.local_api)
        chef_auth = local_env.override_attributes.get('remote_chef', None)

        if chef_auth and chef_auth['key']:
            remote_api = ChefServer._remote_chef_api(chef_auth)
            remove_env = Environment(name, remote_api)
            default = remove_env.default_attributes
            override = remove_env.override_attributes
        else:
            remote_api = None
            default = local_env.default_attributes
            override = local_env.override_attributes

        return default, override, remote_api

    @property
    def local_api(self):
        return autoconfigure()
