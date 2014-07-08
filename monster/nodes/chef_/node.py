import chef
import logging

import monster.active as active
import monster.nodes.base as base

logger = logging.getLogger(__name__)


class Node(base.Node):
    """Wraps a Chef node.
    Provides chef related server functions."""
    def __init__(self, name, ip, user, password, deployment, uuid,
                 run_list=None, features=None):
        super(Node, self).__init__(name, ip, user, password, deployment, uuid)
        self.environment = deployment.environment
        self.branch = deployment.branch
        self.run_list = run_list or []
        self.add_features(features)
        self.set_chef_environment()

    def __getitem__(self, item):
        """Node has access to chef attributes."""
        logger.debug("getting {0} on {1}".format(item, self.name))
        return self.local_node[item]

    def __setitem__(self, item, value):
        """Node can set chef attributes."""
        logger.debug("setting {0} to {1} on {2}".format(item, value,
                                                        self.name))
        local_node = self.local_node
        local_node[item] = value
        self.save(local_node)

    def set_chef_environment(self):
        node = self.local_node
        node.chef_environment = self.environment.name
        node.save()

    def build(self):
        """Builds the node."""
        self.clear_run_list()
        super(Node, self).build()

    def destroy(self):
        self.local_node.delete()
        self.client.delete()
        super(Node, self).destroy()

    def upgrade(self, times=1, accept_failure=False):
        """Upgrade the node according to its features.
        :param times: number of times to run chef-client
        :type times: int
        :param accept_failure: whether to accept failure of chef-client runs
        :type accept_failure: boolean
        """
        self.branch = self.deployment.branch
        super(Node, self).upgrade()
        if not self.has_feature("chefserver"):
            try:
                self.run(times=times)
            except Exception as e:
                if accept_failure:
                    pass
                else:
                    raise Exception("chef-client upgrade failure:{0}".
                                    format(e))

    def apply_feature(self):
        """Runs chef client before apply features on node."""
        self.status = "apply-feature"
        if not self.has_feature("chefserver"):
            self.run()
        super(Node, self).apply_feature()

    def save(self, node=None):
        """Saves a chef node to local and remote chef server."""
        logger.debug("Saving chef_node:{0}".format(self.name))
        node = node or self.local_node
        node.save(self.local_api)
        if self.remote_api:
            node.save(self.remote_api)

    def save_locally(self, node=None):
        """Syncs the remote chef nodes attribute to the local chef server."""
        logger.debug("Syncing chef node from remote:{0}".format(
            self.name))
        if self.remote_api:
            node = node or self.remote_node
            node.save(self.local_api)

    def get_run_list(self):
        return self.local_node.run_list

    def add_run_list_item(self, items):
        """Adds list of items to run_list."""
        logger.debug("run_list:{0} add:{1}".format(self.run_list, items))
        self.run_list.extend(items)
        node = self.local_node
        node.run_list = self.run_list
        self.save(node)

    def remove_run_list_item(self, item):
        """Adds list of items to run_list."""
        logger.debug("run_list:{0} remove:{1}".format(self.run_list, item))
        self.run_list.pop(self.run_list.index(item))
        node = self.local_node
        node.run_list = self.run_list
        self.save(node)

    def clear_run_list(self):
        self.run_list = []
        node = self.local_node
        node.run_list = []
        node.save()

    def run(self, times=1, debug=True, accept_failure=True):
        cmd = active.config['chef']['client']['run_cmd']
        for i in xrange(times):
            if debug:
                time = self.run_cmd("date +%F_%T")['return'].rstrip()
                log_file = '{0}-client-run.log'.format(time)
                cmd = '{0} -l debug -L "/opt/chef/{1}"'.format(cmd, log_file)
            chef_run = self.run_cmd(cmd)
            self.save_locally()
            if not chef_run['success'] and not accept_failure:
                raise Exception("Chef client failure")

    @property
    def client(self):
        return chef.Client(self.name, self.local_api)

    @property
    def local_node(self):
        return chef.Node(self.name, self.local_api)

    @property
    def remote_node(self):
        return chef.Node(self.name, self.remote_api)

    @property
    def local_api(self):
        return self.environment.local_api

    @property
    def remote_api(self):
        return self.environment.remote_api
