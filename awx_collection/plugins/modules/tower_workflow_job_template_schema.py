#!/usr/bin/python
# coding: utf-8 -*-


# (c) 2020, John Westcott IV <john.westcott.iv@redhat.com>, Sean Sullivan <ssulliva@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: tower_workflow_job_template_schema
author: "John Westcott IV (@john-westcott-iv), Sean Sullivan (@sean-m-sullivan)"
version_added: "2.9"
short_description: create, update, or destroy Ansible Tower workflow job template graphs.
description:
    - Create, update, or destroy Ansible Tower workflow job template graphs.
    - Use this to build a graph for a workflow, which dictates what the workflow runs.
    - Replaces the deprecated tower_workflow_template module schema command.
    - This module takes a json list of inputs to first create nodes, then link them, and does not worry about ordering.
      For failsafe referencing of a node, specify identifier, WFJT, and organization.
      With those specified, you can choose to modify or not modify any other parameter.
    - This Module will accept schemas from tower_export.
options:
    workflow_job_template:
      description:
        - The workflow job template the node exists in.
        - Used for looking up the node, cannot be modified after creation.
      required: True
      type: str
      aliases:
        - workflow
    organization:
      description:
        - The organization of the workflow job template the node exists in.
        - Used for looking up the workflow, not a direct model field.
      type: str
    schema:
      description:
        - A json list of nodes and their coresponding options. The following suboptions describe a single node.
      type: list
      required: True
      suboptions:
        extra_data:
          description:
            - Variables to apply at launch time.
            - Will only be accepted if job template prompts for vars or has a survey asking for those vars.
          type: dict
          default: {}
        inventory:
          description:
            - Inventory applied as a prompt, if job template prompts for inventory
          type: str
        scm_branch:
          description:
            - SCM branch applied as a prompt, if job template prompts for SCM branch
          type: str
        job_type:
          description:
            - Job type applied as a prompt, if job template prompts for job type
          type: str
          choices:
            - 'run'
            - 'check'
        job_tags:
          description:
            - Job tags applied as a prompt, if job template prompts for job tags
          type: str
        skip_tags:
          description:
            - Tags to skip, applied as a prompt, if job tempalte prompts for job tags
          type: str
        limit:
          description:
            - Limit to act on, applied as a prompt, if job template prompts for limit
          type: str
        diff_mode:
          description:
            - Run diff mode, applied as a prompt, if job template prompts for diff mode
          type: bool
        verbosity:
          description:
            - Verbosity applied as a prompt, if job template prompts for verbosity
          type: str
          choices:
            - '0'
            - '1'
            - '2'
            - '3'
            - '4'
            - '5'
        all_parents_must_converge:
          description:
            - If enabled then the node will only run if all of the parent nodes have met the criteria to reach this node
          type: bool
        identifier:
          description:
            - An identifier for this node that is unique within its workflow.
            - It is copied to workflow job nodes corresponding to this node.
          required: True
          type: str
        state:
          description:
            - Desired state of the resource.
          choices: ["present", "absent"]
          default: "present"
          type: str

        unified_job_template:
          description:
            - Name of unified job template to run in the workflow.
            - Can be a job template, project sync, inventory source sync, etc.
            - Omit if creating an approval node (not yet implemented).
          type: dict
          suboptions:
            organization:
              description:
                - Name of key for use in model for organizational reference
                - Only Valid and used if referencing a job template or project sync
              type: dict
              suboptions:
                name:
                  description:
                    - The organization of the job template or project sync the node exists in.
                    - Used for looking up the job template or project sync, not a direct model field.
                  type: str
            inventory:
              description:
                - Name of key for use in model for organizational reference
                - Only Valid and used if referencing an inventory sync
              type: dict
              suboptions:
                organization:
                  description:
                    - Name of key for use in model for organizational reference
                  type: dict
                  suboptions:
                    name:
                      description:
                        - The organization of the inventory the node exists in.
                        - Used for looking up the job template or project, not a direct model field.
                      type: str
        related:
          description:
            - Related items to this workflow node.
            - Must include credentials, failure_nodes, always_nodes, success_nodes, even if empty.
          type: dict
          suboptions:
            always_nodes:
              description:
                - Nodes that will run after this node completes.
                - List of node identifiers.
              type: list
              suboptions:
                identifier:
                description:
                  - Identifier of Node that will run after this node completes given this option.
                elements: str
            success_nodes:
              description:
                - Nodes that will run after this node on success.
                - List of node identifiers.
              type: list
              suboptions:
                identifier:
                description:
                  - Identifier of Node that will run after this node completes given this option.
                elements: str
            failure_nodes:
              description:
                - Nodes that will run after this node on failure.
                - List of node identifiers.
              type: list
              suboptions:
                identifier:
                description:
                  - Identifier of Node that will run after this node completes given this option.
                elements: str
            credentials:
              description:
                - Credentials to be applied to job as launch-time prompts.
                - List of credential names.
                - Uniqueness is not handled rigorously.
              type: list
              suboptions:
                name:
                description:
                  - Name Credentials to be applied to job as launch-time prompts.
                elements: str
    destroy_current_schema:
      description:
        - Set in order to destroy current schema on the workflow.
        - This option is used for full schema update, if not used, nodes not described in schema will persist and keep current associations and links.
      type: Bool
      default: False


extends_documentation_fragment: awx.awx.auth
'''

EXAMPLES = '''
More advanced examples can be made from using the tower_export module

- name: Create a workflow job template schema
  awx.awx.tower_workflow_job_template_schema:
    workflow_job_template: "{{ wfjt_name }}"
    schema:
      - identifier: node101
        unified_job_template:
          name: "Default Inventory"
          inventory:
            organization:
              name: Default
        related:
          success_nodes: []
          failure_nodes:
            - identifier: node201
          always_nodes: []
          credentials: []
      - identifier: node201
        unified_job_template:
          organization:
            name: Default
          name: "Job Template 1"
        credentials: []
        related:
          success_nodes:
            - identifier: node301
          failure_nodes: []
          always_nodes: []
          credentials: []
      - identifier: node202
        unified_job_template:
          organization:
            name: Default
          name: "Default Project Name"
        related:
          success_nodes: []
          failure_nodes: []
          always_nodes: []
          credentials: []
      - all_parents_must_converge: false
        identifier: node301
        unified_job_template:
          organization:
            name: Default
          name: "Job Template 2"
        related:
          success_nodes: []
          failure_nodes: []
          always_nodes: []
          credentials: []

- name: Destroy schema and create new one
  awx.awx.tower_workflow_job_template_schema:
    workflow_job_template: "{{ wfjt_name }}"
    destroy_current_schema: true
    schema:
      - identifier: node101
        unified_job_template:
          organization:
            name: Default
          name: "Job Template Name"
        credentials: []
        related:
          success_nodes:
            - identifier: node201
          failure_nodes: []
          always_nodes: []
          credentials: []
      - identifier: node201
        unified_job_template:
          name: "Project Name"
          inventory:
            organization:
              name: Default
        related:
          success_nodes: []
          failure_nodes: []
          always_nodes: []
          credentials: []

'''

from ..module_utils.tower_api import TowerAPIModule
from ansible.errors import AnsibleError

response = []


def main():
    # Any additional arguments that are not fields of the item can be added here
    argument_spec = dict(
        workflow_job_template=dict(required=True, aliases=['workflow']),
        organization=dict(),
        schema=dict(required=True, type='list', elements='dict'),
        destroy_current_schema=dict(type='bool', default=False),
    )

    # Create a module for ourselves
    module = TowerAPIModule(argument_spec=argument_spec)

    # Extract our parameters
    schema = None
    if module.params.get('schema'):
        schema = module.params.get('schema')
    destroy_current_schema = module.params.get('destroy_current_schema')

    new_fields = {}

    node_loop = ''

    # Attempt to look up the related items the user specified (these will fail the module if not found)
    workflow_job_template = module.params.get('workflow_job_template')
    workflow_job_template_id = None
    if workflow_job_template:
        wfjt_search_fields = {'name': workflow_job_template}
        organization = module.params.get('organization')
        if organization:
            organization_id = module.resolve_name_to_id('organizations', organization)
            wfjt_search_fields['organization'] = organization_id
        wfjt_data = module.get_one('workflow_job_templates', **{'data': wfjt_search_fields})
        if wfjt_data is None:
            module.fail_json(msg="The workflow {0} in organization {1} was not found on the Tower server".format(
                workflow_job_template, organization
            ))
        workflow_job_template_id = wfjt_data['id']

    # Work thorugh and lookup value for schema fields
    # Destroy current nodes if selected.
    if destroy_current_schema:
        module.destroy_schema_nodes(response, workflow_job_template_id)
    # Create Schema Nodes
    module.create_schema_nodes(response, schema, workflow_job_template_id)
    # Create Schema Associations
    module.create_schema_nodes_association(response, schema, workflow_job_template_id)
    module.exit_json(**module.json_output)


if __name__ == '__main__':
    main()
