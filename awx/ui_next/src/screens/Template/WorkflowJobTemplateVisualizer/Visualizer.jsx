import React, { Fragment, useState, useEffect } from 'react';
import { withI18n } from '@lingui/react';
import { t } from '@lingui/macro';
import styled from 'styled-components';
import { layoutGraph } from '@util/workflow';
import ContentError from '@components/ContentError';
import ContentLoading from '@components/ContentLoading';
import NodeDeleteModal from './Modals/NodeDeleteModal';
import VisualizerGraph from './VisualizerGraph';
import VisualizerStartScreen from './VisualizerStartScreen';
import VisualizerToolbar from './VisualizerToolbar';
import { WorkflowJobTemplatesAPI } from '@api';

const CenteredContent = styled.div`
  display: flex;
  flex-flow: column;
  height: 100%;
  align-items: center;
  justify-content: center;
`;

const Wrapper = styled.div`
  display: flex;
  flex-flow: column;
  height: 100%;
`;

const fetchWorkflowNodes = async (templateId, pageNo = 1, nodes = []) => {
  try {
    const { data } = await WorkflowJobTemplatesAPI.readNodes(templateId, {
      page_size: 200,
      page: pageNo,
    });
    if (data.next) {
      return await fetchWorkflowNodes(
        templateId,
        pageNo + 1,
        nodes.concat(data.results)
      );
    }
    return nodes.concat(data.results);
  } catch (error) {
    throw error;
  }
};

function Visualizer({ template, i18n }) {
  const [contentError, setContentError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [graphLinks, setGraphLinks] = useState([]);
  // We'll also need to store the original set of nodes...
  const [graphNodes, setGraphNodes] = useState([]);
  const [nodePositions, setNodePositions] = useState(null);
  const [nodeToDelete, setNodeToDelete] = useState(null);

  const deleteNode = () => {
    const nodeId = nodeToDelete.id;
    const newGraphNodes = [...graphNodes];
    const newGraphLinks = [...graphLinks];

    // Remove the node from the array
    for (let i = newGraphNodes.length; i--; ) {
      if (newGraphNodes[i].id === nodeId) {
        newGraphNodes.splice(i, 1);
        i = 0;
      }
    }

    // Update the links
    const parents = [];
    const children = [];
    const linkParentMapping = {};

    // Remove any links that reference this node
    for (let i = newGraphLinks.length; i--; ) {
      const link = newGraphLinks[i];

      if (!linkParentMapping[link.target.id]) {
        linkParentMapping[link.target.id] = [];
      }

      linkParentMapping[link.target.id].push(link.source.id);

      if (link.source.id === nodeId || link.target.id === nodeId) {
        if (link.source.id === nodeId) {
          children.push({ id: link.target.id, edgeType: link.edgeType });
        } else if (link.target.id === nodeId) {
          parents.push(link.source.id);
        }
        newGraphLinks.splice(i, 1);
      }
    }

    // Add the new links
    parents.forEach(parentId => {
      children.forEach(child => {
        if (parentId === 1) {
          // We only want to create a link from the start node to this node if it
          // doesn't have any other parents
          if (linkParentMapping[child.id].length === 1) {
            newGraphLinks.push({
              source: { id: parentId },
              target: { id: child.id },
              edgeType: 'always',
              type: 'link',
            });
          }
        } else if (!linkParentMapping[child.id].includes(parentId)) {
          newGraphLinks.push({
            source: { id: parentId },
            target: { id: child.id },
            edgeType: child.edgeType,
            type: 'link',
          });
        }
      });
    });
    // need to track that this node has been deleted if it's not new

    setNodeToDelete(null);
    setGraphNodes(newGraphNodes);
    setGraphLinks(newGraphLinks);
  };

  useEffect(() => {
    const buildGraphArrays = nodes => {
      const nonRootNodeIds = [];
      const allNodeIds = [];
      const arrayOfLinksForChart = [];
      const nodeIdToChartNodeIdMapping = {};
      const chartNodeIdToIndexMapping = {};
      const nodeRef = {};
      let nodeIdCounter = 1;
      const arrayOfNodesForChart = [
        {
          id: nodeIdCounter,
          unifiedJobTemplate: {
            name: i18n._(t`START`),
          },
          type: 'node',
        },
      ];
      nodeIdCounter++;
      // Assign each node an ID - 0 is reserved for the start node.  We need to
      // make sure that we have an ID on every node including new nodes so the
      // ID returned by the api won't do
      nodes.forEach(node => {
        node.workflowMakerNodeId = nodeIdCounter;
        nodeRef[nodeIdCounter] = {
          originalNodeObject: node,
        };

        const nodeObj = {
          index: nodeIdCounter - 1,
          id: nodeIdCounter,
          type: 'node',
        };

        if (node.summary_fields.job) {
          nodeObj.job = node.summary_fields.job;
        }
        if (node.summary_fields.unified_job_template) {
          nodeRef[nodeIdCounter].unifiedJobTemplate =
            node.summary_fields.unified_job_template;
          nodeObj.unifiedJobTemplate = node.summary_fields.unified_job_template;
        }

        arrayOfNodesForChart.push(nodeObj);
        allNodeIds.push(node.id);
        nodeIdToChartNodeIdMapping[node.id] = node.workflowMakerNodeId;
        chartNodeIdToIndexMapping[nodeIdCounter] = nodeIdCounter - 1;
        nodeIdCounter++;
      });

      nodes.forEach(node => {
        const sourceIndex = chartNodeIdToIndexMapping[node.workflowMakerNodeId];
        node.success_nodes.forEach(nodeId => {
          const targetIndex =
            chartNodeIdToIndexMapping[nodeIdToChartNodeIdMapping[nodeId]];
          arrayOfLinksForChart.push({
            source: arrayOfNodesForChart[sourceIndex],
            target: arrayOfNodesForChart[targetIndex],
            edgeType: 'success',
            type: 'link',
          });
          nonRootNodeIds.push(nodeId);
        });
        node.failure_nodes.forEach(nodeId => {
          const targetIndex =
            chartNodeIdToIndexMapping[nodeIdToChartNodeIdMapping[nodeId]];
          arrayOfLinksForChart.push({
            source: arrayOfNodesForChart[sourceIndex],
            target: arrayOfNodesForChart[targetIndex],
            edgeType: 'failure',
            type: 'link',
          });
          nonRootNodeIds.push(nodeId);
        });
        node.always_nodes.forEach(nodeId => {
          const targetIndex =
            chartNodeIdToIndexMapping[nodeIdToChartNodeIdMapping[nodeId]];
          arrayOfLinksForChart.push({
            source: arrayOfNodesForChart[sourceIndex],
            target: arrayOfNodesForChart[targetIndex],
            edgeType: 'always',
            type: 'link',
          });
          nonRootNodeIds.push(nodeId);
        });
      });

      const uniqueNonRootNodeIds = Array.from(new Set(nonRootNodeIds));

      const rootNodes = allNodeIds.filter(
        nodeId => !uniqueNonRootNodeIds.includes(nodeId)
      );

      rootNodes.forEach(rootNodeId => {
        const targetIndex =
          chartNodeIdToIndexMapping[nodeIdToChartNodeIdMapping[rootNodeId]];
        arrayOfLinksForChart.push({
          source: arrayOfNodesForChart[0],
          target: arrayOfNodesForChart[targetIndex],
          edgeType: 'always',
          type: 'link',
        });
      });

      setGraphNodes(arrayOfNodesForChart);
      setGraphLinks(arrayOfLinksForChart);
    };

    async function fetchData() {
      try {
        const nodes = await fetchWorkflowNodes(template.id);
        buildGraphArrays(nodes);
      } catch (error) {
        setContentError(error);
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, [template.id, i18n]);

  // Update positions of nodes/links
  useEffect(() => {
    if (graphNodes) {
      const newNodePositions = {};
      const g = layoutGraph(graphNodes, graphLinks);

      g.nodes().forEach(node => {
        newNodePositions[node] = g.node(node);
      });

      setNodePositions(newNodePositions);
    }
  }, [graphLinks, graphNodes]);

  if (isLoading) {
    return (
      <CenteredContent>
        <ContentLoading />
      </CenteredContent>
    );
  }

  if (contentError) {
    return (
      <CenteredContent>
        <ContentError error={contentError} />
      </CenteredContent>
    );
  }

  return (
    <Fragment>
      <Wrapper>
        <VisualizerToolbar template={template} />
        {graphLinks.length > 0 ? (
          <VisualizerGraph
            links={graphLinks}
            nodes={graphNodes}
            nodePositions={nodePositions}
            readOnly={!template.summary_fields.user_capabilities.edit}
            onDeleteNodeClick={setNodeToDelete}
          />
        ) : (
          <VisualizerStartScreen />
        )}
      </Wrapper>
      <NodeDeleteModal
        nodeToDelete={nodeToDelete}
        onConfirm={deleteNode}
        onCancel={() => setNodeToDelete(null)}
      />
    </Fragment>
  );
}

export default withI18n()(Visualizer);
