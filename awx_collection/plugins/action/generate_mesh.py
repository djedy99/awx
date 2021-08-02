#!/usr/bin/python
# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase
from datetime import datetime
from collections import defaultdict


class ActionModule(ActionBase):

    __res = """
    strict digraph "" {
    rankdir = LR
    subgraph cluster_0 {
        graph [label="Control Nodes", type=solid];
    """

    _CONTROL_PLANE = "automationcontroller"
    _EXECUTION_PLANE = "execution_nodes"

    _NODE_VALID_TYPES = {
        "automationcontroller": {
            "types": frozenset(("control", "hybrid")),
            "default_type": "hybrid",
        },
        "execution_nodes": {
            "types": frozenset(("execution", "hop")),
            "default_type": "execution",
        },
    }

    def generate_control_plane_topology(self, data):
        res = defaultdict(set)
        for index, control_node in enumerate(data[self._CONTROL_PLANE]["hosts"]):
            res[control_node] |= set(data[self._CONTROL_PLANE]["hosts"][(index + 1) :])
        return res

    def connect_peers(self, group_name, data):
        res = defaultdict(set)

        for node in data["groups"][group_name]:
            # if "peers" in data["hostvars"][node].keys():
            res[node]
            for peer in (
                data["hostvars"][node].get("peers", "").split(",")
            ):  # to-do: make work with yaml list
                # handle groups
                if not peer:
                    continue
                if peer in data["groups"]:
                    ## list comprehension to produce peers list. excludes circular reference to node
                    res[node] |= {x for x in data["groups"][peer] if x != node}
                else:
                    res[node].add(peer)

        return res

    def deep_merge_dicts(*args):

        data = defaultdict(set)

        for d in args:
            for k, v in d.items():
                data[k] |= set(v)

        return dict(data)

    def generate_dot_syntax_from_dict(dict=None):

        if dict is None:
            return

        res = ""

        for label, nodes in dict.items():
            for node in nodes:
                res += '"{0}" -> "{1}";\n'.format(label, node)

        return res

    def detect_cycles(data):
        conflicts = set()
        for node, peers in data.items():  # k = host, v = set(hosts)
            for host in peers:
                if node in data.get(host, set()):
                    conflicts.add(frozenset((node, host)))
        if conflicts:
            conflict_str = ", ".join(f"{n1} <-> {n2}" for n1, n2 in conflicts)
            raise AnsibleError(
                f"Two-way link(s) detected: {conflict_str}\nCannot have an inbound and outbound connection between the same two nodes"
            )

    def assert_node_type(self, host=None, vars=None, group_name=None, valid_types=None):
        """
        Members of given group_name must have a valid node_type.
        """
        if "node_type" not in vars.keys():
            return valid_types[group_name]["default_type"]

        if vars["node_type"] not in valid_types[group_name]["types"]:
            raise AnsibleError(
                "The host {0} must have one of the valid node_types: {1}".format(
                    host,
                    ", ".join(str(i) for i in valid_types[group_name]["types"]),
                )
            )
        return vars["node_type"]

    def assert_unique_group(self, task_vars=None):
        """
        A given host cannot be part of the automationcontroller and execution_nodes group.
        """
        automation_group = task_vars.get("groups").get("automationcontroller")
        execution_nodes = task_vars.get("groups").get("execution_nodes")

        if automation_group and execution_nodes:
            intersection = list(set(automation_group) & set(execution_nodes))
            if intersection:
                raise AnsibleError(
                    "The following hosts cannot be members of both [automationcontroller] and [execution_nodes] groups: {0}".format(
                        ", ".join(str(i) for i in intersection)
                    )
                )
        return

    def run(self, tmp=None, task_vars=None):

        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        result = {}

        self.assert_unique_group(task_vars)

        for group in ["automationcontroller", "execution_nodes"]:
            for host in task_vars.get("groups").get(group):
                _host_vars = dict(task_vars.get("hostvars").get(host))
                myhost_data = {}
                myhost_data["name"] = host
                myhost_data["peers"] = {}
                myhost_data["node_type"] = self.assert_node_type(
                    host=host,
                    vars=_host_vars,
                    group_name=group,
                    valid_types=self._NODE_VALID_TYPES,
                )
                result.append(myhost_data)

        d1 = self.connect_peers("automationcontroller", task_vars)

        return dict(stdout={k: list(v) for k, v in d1.items()})
