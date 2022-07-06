import React from 'react';
import { Link } from 'react-router-dom';

import { t } from '@lingui/macro';
import { Button, Chip } from '@patternfly/react-core';
import { Tr as PFTr, Td, ExpandableRowContent } from '@patternfly/react-table';
import { RocketIcon } from '@patternfly/react-icons';
import styled, { keyframes } from 'styled-components';
import { formatDateString } from 'util/dates';
import { isJobRunning } from 'util/jobs';
import getScheduleUrl from 'util/getScheduleUrl';
import { ActionsTd, ActionItem, TdBreakWord } from '../PaginatedTable';
import { LaunchButton, ReLaunchDropDown } from '../LaunchButton';
import StatusLabel from '../StatusLabel';
import {
  DetailList,
  Detail,
  DeletedDetail,
  LaunchedByDetail,
} from '../DetailList';
import ChipGroup from '../ChipGroup';
import CredentialChip from '../CredentialChip';
import ExecutionEnvironmentDetail from '../ExecutionEnvironmentDetail';
import { JOB_TYPE_URL_SEGMENTS } from '../../constants';
import JobCancelButton from '../JobCancelButton';

const Dash = styled.span``;
const addRow = keyframes`
  0% {
    padding-top: 0;
    padding-buttom: 0;
    transform: scale(1, 0);
    line-height: 0px;
    visibility: collapse;
  }
  100% {
    padding-top: 24px;
    padding-buttom: 24px;
    transform: scale(1, 1);
    line-height: 24px;
    visibility: visible;
  }
`;

const Tr = styled(PFTr)`
  &.isNew > td {
    transition-duration: 1s;
    animation: ${addRow} 700ms 1 ease-in;
    transform-origin: top;
  }
`;

function JobListItem({
  isExpanded,
  onExpand,
  job,
  rowIndex,
  isSelected,
  onSelect,
  showTypeColumn = false,
  isSuperUser = false,
  inventorySourceLabels,
}) {
  const labelId = `check-action-${job.id}`;

  const jobTypes = {
    project_update: t`Source Control Update`,
    inventory_update: t`Inventory Sync`,
    job: job.job_type === 'check' ? t`Playbook Check` : t`Playbook Run`,
    ad_hoc_command: t`Command`,
    system_job: t`Management Job`,
    workflow_job: t`Workflow Job`,
  };

  const {
    credentials,
    execution_environment,
    inventory,
    job_template,
    labels,
    project,
    schedule,
    source_workflow_job,
    workflow_job_template,
  } = job.summary_fields;

  const {
    job_slice_number: jobSliceNumber,
    job_slice_count: jobSliceCount,
    is_sliced_job: isSlicedJob,
  } = job;

  return (
    <>
      <Tr
        id={`job-row-${job.id}`}
        ouiaId={`job-row-${job.id}`}
        className={job.isNew ? 'isNew' : null}
      >
        <Td
          expand={{
            rowIndex: job.id,
            isExpanded,
            onToggle: onExpand,
          }}
        />
        <Td
          select={{
            rowIndex,
            isSelected,
            onSelect,
          }}
          dataLabel={t`Select`}
        />
        <TdBreakWord id={labelId} dataLabel={t`Name`}>
          <span>
            <Link to={`/jobs/${JOB_TYPE_URL_SEGMENTS[job.type]}/${job.id}`}>
              <b>
                {job.id} <Dash>&mdash;</Dash> {job.name}
              </b>
            </Link>
          </span>
        </TdBreakWord>
        <Td dataLabel={t`Status`}>
          {job.status && <StatusLabel status={job.status} />}
        </Td>
        {showTypeColumn && <Td dataLabel={t`Type`}>{jobTypes[job.type]}</Td>}
        <Td dataLabel={t`Start Time`}>{formatDateString(job.started)}</Td>
        <Td dataLabel={t`Finish Time`}>
          {job.finished ? formatDateString(job.finished) : ''}
        </Td>
        <ActionsTd dataLabel={t`Actions`}>
          <ActionItem
            visible={
              ['pending', 'waiting', 'running'].includes(job.status) &&
              (job.type === 'system_job' ? isSuperUser : true)
            }
          >
            <JobCancelButton
              job={job}
              errorTitle={t`Job Cancel Error`}
              title={t`Cancel ${job.name}`}
              errorMessage={t`Failed to cancel ${job.name}`}
              showIconButton
            />
          </ActionItem>
          <ActionItem
            visible={
              job.type !== 'system_job' &&
              job.summary_fields?.user_capabilities?.start
            }
            tooltip={
              job.status === 'failed' && job.type === 'job'
                ? t`Relaunch using host parameters`
                : t`Relaunch Job`
            }
          >
            {job.status === 'failed' && job.type === 'job' ? (
              <LaunchButton resource={job}>
                {({ handleRelaunch, isLaunching }) => (
                  <ReLaunchDropDown
                    handleRelaunch={handleRelaunch}
                    isLaunching={isLaunching}
                    id={`relaunch-job-${job.id}`}
                  />
                )}
              </LaunchButton>
            ) : (
              <LaunchButton resource={job}>
                {({ handleRelaunch, isLaunching }) => (
                  <Button
                    ouiaId={`${job.id}-relaunch-button`}
                    variant="plain"
                    onClick={() => handleRelaunch()}
                    aria-label={t`Relaunch`}
                    isDisabled={isLaunching}
                  >
                    <RocketIcon />
                  </Button>
                )}
              </LaunchButton>
            )}
          </ActionItem>
        </ActionsTd>
      </Tr>
      <Tr
        isExpanded={isExpanded}
        id={`expanded-job-row-${job.id}`}
        ouiaId={`expanded-job-row-${job.id}`}
      >
        <Td colSpan={2} />
        <Td colSpan={showTypeColumn ? 6 : 5}>
          <ExpandableRowContent>
            <DetailList>
              {job.type === 'inventory_update' && (
                <Detail
                  dataCy="job-inventory-source-type"
                  label={t`Source`}
                  value={inventorySourceLabels?.map(([string, label]) =>
                    string === job.source ? label : null
                  )}
                  isEmpty={inventorySourceLabels?.length === 0}
                />
              )}
              <LaunchedByDetail job={job} />
              {job.launch_type === 'scheduled' &&
                (schedule ? (
                  <Detail
                    dataCy="job-schedule"
                    label={t`Schedule`}
                    value={
                      <Link to={getScheduleUrl(job)}>{schedule.name}</Link>
                    }
                  />
                ) : (
                  <DeletedDetail label={t`Schedule`} />
                ))}
              {job_template && (
                <Detail
                  label={t`Job Template`}
                  value={
                    <Link to={`/templates/job_template/${job_template.id}`}>
                      {job_template.name}
                    </Link>
                  }
                />
              )}
              {workflow_job_template && (
                <Detail
                  label={t`Workflow Job Template`}
                  value={
                    <Link
                      to={`/templates/workflow_job_template/${workflow_job_template.id}`}
                    >
                      {workflow_job_template.name}
                    </Link>
                  }
                />
              )}
              {source_workflow_job && (
                <Detail
                  label={t`Source Workflow Job`}
                  value={
                    <Link to={`/jobs/workflow/${source_workflow_job.id}`}>
                      {source_workflow_job.id} - {source_workflow_job.name}
                    </Link>
                  }
                />
              )}
              {inventory && (
                <Detail
                  label={t`Inventory`}
                  value={
                    <Link
                      to={
                        inventory.kind === 'smart'
                          ? `/inventories/smart_inventory/${inventory.id}`
                          : `/inventories/inventory/${inventory.id}`
                      }
                    >
                      {inventory.name}
                    </Link>
                  }
                />
              )}
              {project && (
                <Detail
                  label={t`Project`}
                  value={
                    <Link to={`/projects/${project.id}/details`}>
                      {project.name}
                    </Link>
                  }
                  dataCy={`job-${job.id}-project`}
                />
              )}
              {job.type !== 'workflow_job' &&
                !isJobRunning(job.status) &&
                job.status !== 'canceled' && (
                  <ExecutionEnvironmentDetail
                    executionEnvironment={execution_environment}
                    verifyMissingVirtualEnv={false}
                    dataCy={`execution-environment-detail-${job.id}`}
                  />
                )}
              {credentials && (
                <Detail
                  fullWidth
                  label={t`Credentials`}
                  dataCy={`job-${job.id}-credentials`}
                  value={
                    <ChipGroup
                      numChips={5}
                      totalChips={credentials.length}
                      ouiaId={`job-${job.id}-credential-chips`}
                    >
                      {credentials.map((c) => (
                        <CredentialChip
                          credential={c}
                          isReadOnly
                          key={c.id}
                          ouiaId={`credential-${c.id}-chip`}
                        />
                      ))}
                    </ChipGroup>
                  }
                  isEmpty={credentials.length === 0}
                />
              )}
              {labels && labels.count > 0 && (
                <Detail
                  fullWidth
                  label={t`Labels`}
                  value={
                    <ChipGroup
                      numChips={5}
                      totalChips={labels.results.length}
                      ouiaId={`job-${job.id}-label-chips`}
                    >
                      {labels.results.map((l) => (
                        <Chip
                          key={l.id}
                          isReadOnly
                          ouiaId={`label-${l.id}-chip`}
                        >
                          {l.name}
                        </Chip>
                      ))}
                    </ChipGroup>
                  }
                />
              )}
              {job.job_explanation && (
                <Detail
                  fullWidth
                  label={t`Explanation`}
                  value={job.job_explanation}
                />
              )}
              {typeof jobSliceNumber === 'number' &&
                typeof jobSliceCount === 'number' && (
                  <Detail
                    label={t`Job Slice`}
                    value={`${jobSliceNumber}/${jobSliceCount}`}
                  />
                )}
              {job.type === 'workflow_job' && isSlicedJob && (
                <Detail label={t`Job Slice Parent`} value={t`True`} />
              )}
            </DetailList>
          </ExpandableRowContent>
        </Td>
      </Tr>
    </>
  );
}

export { JobListItem as _JobListItem };
export default JobListItem;
