import datetime
import multiprocessing
import random
import signal
import time
import yaml
from unittest import mock

from django.utils.timezone import now as tz_now
import pytest

from awx.main.models import Job, WorkflowJob, Instance
from awx.main.dispatch import reaper
from awx.main.dispatch.pool import StatefulPoolWorker, WorkerPool, AutoscalePool
from awx.main.dispatch.publish import task
from awx.main.dispatch.worker import BaseWorker, TaskWorker
from awx.main.dispatch.periodic import Scheduler


'''
Prevent logger.<warn, debug, error> calls from triggering database operations
'''


@pytest.fixture(autouse=True)
def _disable_database_settings(mocker):
    m = mocker.patch('awx.conf.settings.SettingsWrapper.all_supported_settings', new_callable=mock.PropertyMock)
    m.return_value = []


def restricted(a, b):
    raise AssertionError("This code should not run because it isn't decorated with @task")


@task()
def add(a, b):
    return a + b


class BaseTask(object):
    def add(self, a, b):
        return add(a, b)


class Restricted(object):
    def run(self, a, b):
        raise AssertionError("This code should not run because it isn't decorated with @task")


@task()
class Adder(BaseTask):
    def run(self, a, b):
        return super(Adder, self).add(a, b)


@task(queue='hard-math')
def multiply(a, b):
    return a * b


class SimpleWorker(BaseWorker):
    def perform_work(self, body, *args):
        pass


class ResultWriter(BaseWorker):
    def perform_work(self, body, result_queue):
        result_queue.put(body + '!!!')


class SlowResultWriter(BaseWorker):
    def perform_work(self, body, result_queue):
        time.sleep(3)
        super(SlowResultWriter, self).perform_work(body, result_queue)


@pytest.mark.usefixtures("disable_database_settings")
class TestPoolWorker:
    def setup_method(self, test_method):
        self.worker = StatefulPoolWorker(1000, self.tick, tuple())

    def tick(self):
        self.worker.finished.put(self.worker.queue.get()['uuid'])
        time.sleep(0.5)

    def test_qsize(self):
        assert self.worker.qsize == 0
        for i in range(3):
            self.worker.put({'task': 'abc123'})
        assert self.worker.qsize == 3

    def test_put(self):
        assert len(self.worker.managed_tasks) == 0
        assert self.worker.messages_finished == 0
        self.worker.put({'task': 'abc123'})

        assert len(self.worker.managed_tasks) == 1
        assert self.worker.messages_sent == 1

    def test_managed_tasks(self):
        self.worker.put({'task': 'abc123'})
        self.worker.calculate_managed_tasks()
        assert len(self.worker.managed_tasks) == 1

        self.tick()
        self.worker.calculate_managed_tasks()
        assert len(self.worker.managed_tasks) == 0

    def test_current_task(self):
        self.worker.put({'task': 'abc123'})
        assert self.worker.current_task['task'] == 'abc123'

    def test_quit(self):
        self.worker.quit()
        assert self.worker.queue.get() == 'QUIT'

    def test_idle_busy(self):
        assert self.worker.idle is True
        assert self.worker.busy is False
        self.worker.put({'task': 'abc123'})
        assert self.worker.busy is True
        assert self.worker.idle is False


@pytest.mark.django_db
class TestWorkerPool:
    def setup_method(self, test_method):
        self.pool = WorkerPool(min_workers=3)

    def teardown_method(self, test_method):
        self.pool.stop(signal.SIGTERM)

    def test_worker(self):
        self.pool.init_workers(SimpleWorker().work_loop)
        assert len(self.pool) == 3
        for worker in self.pool.workers:
            assert worker.messages_sent == 0
            assert worker.alive is True

    def test_single_task(self):
        self.pool.init_workers(SimpleWorker().work_loop)
        self.pool.write(0, 'xyz')
        assert self.pool.workers[0].messages_sent == 1  # worker at index 0 handled one task
        assert self.pool.workers[1].messages_sent == 0
        assert self.pool.workers[2].messages_sent == 0

    def test_queue_preference(self):
        self.pool.init_workers(SimpleWorker().work_loop)
        self.pool.write(2, 'xyz')
        assert self.pool.workers[0].messages_sent == 0
        assert self.pool.workers[1].messages_sent == 0
        assert self.pool.workers[2].messages_sent == 1  # worker at index 2 handled one task

    def test_worker_processing(self):
        result_queue = multiprocessing.Queue()
        self.pool.init_workers(ResultWriter().work_loop, result_queue)
        for i in range(10):
            self.pool.write(random.choice(range(len(self.pool))), 'Hello, Worker {}'.format(i))
        all_messages = [result_queue.get(timeout=1) for i in range(10)]
        all_messages.sort()
        assert all_messages == ['Hello, Worker {}!!!'.format(i) for i in range(10)]

        total_handled = sum([worker.messages_sent for worker in self.pool.workers])
        assert total_handled == 10


@pytest.mark.django_db
class TestAutoScaling:
    def setup_method(self, test_method):
        self.pool = AutoscalePool(min_workers=2, max_workers=10)

    def teardown_method(self, test_method):
        self.pool.stop(signal.SIGTERM)

    def test_scale_up(self):
        result_queue = multiprocessing.Queue()
        self.pool.init_workers(SlowResultWriter().work_loop, result_queue)

        # start with two workers, write an event to each worker and make it busy
        assert len(self.pool) == 2
        for i, w in enumerate(self.pool.workers):
            w.put('Hello, Worker {}'.format(0))
        assert len(self.pool) == 2

        # wait for the subprocesses to start working on their tasks and be marked busy
        time.sleep(1)
        assert len(self.pool.workers) == self.pool.max_workers

        # write a third message, expect a new worker to spawn because all
        # workers are busy
        self.pool.write(0, 'Hello, Worker {}'.format(2))
        assert len(self.pool) == 3

    def test_scale_down(self):
        self.pool.init_workers(ResultWriter().work_loop, multiprocessing.Queue())

        # start with two workers, and scale up to 10 workers
        assert len(self.pool) == 2
        for i in range(8):
            self.pool.up()
        assert len(self.pool) == 10

        # cleanup should scale down to 8 workers
        self.pool.cleanup()
        assert len(self.pool) == 2

    def test_max_scale_up(self):
        self.pool.init_workers(ResultWriter().work_loop, multiprocessing.Queue())

        assert len(self.pool) == 2
        for i in range(25):
            self.pool.up()
        assert self.pool.max_workers == 10
        assert self.pool.full is True
        assert len(self.pool) == 10

    def test_equal_worker_distribution(self):
        # if all workers are busy, spawn new workers *before* adding messages
        # to an existing queue
        self.pool.init_workers(SlowResultWriter().work_loop, multiprocessing.Queue)

        # start with two workers, write an event to each worker and make it busy
        assert len(self.pool) == 2
        for i in range(10):
            self.pool.write(0, 'Hello, World!')
        assert len(self.pool) == 10
        for w in self.pool.workers:
            assert w.busy
            assert len(w.managed_tasks) == 1

        # the queue is full at 10, the _next_ write should put the message into
        # a worker's backlog
        assert len(self.pool) == 10
        for w in self.pool.workers:
            assert w.messages_sent == 1
        self.pool.write(0, 'Hello, World!')
        assert len(self.pool) == 10
        assert self.pool.workers[0].messages_sent == 2

    @pytest.mark.timeout(20)
    def test_lost_worker_autoscale(self):
        # if a worker exits, it should be replaced automatically up to min_workers
        self.pool.init_workers(ResultWriter().work_loop, multiprocessing.Queue())

        # start with two workers, kill one of them
        assert len(self.pool) == 2
        alive_pid = self.pool.workers[1].pid
        self.pool.workers[0].process.kill()
        self.pool.workers[0].process.join()  # waits for process to full terminate

        # clean up and the dead worker
        self.pool.cleanup()
        assert len(self.pool) == 1
        assert self.pool.workers[0].pid == alive_pid

        # the next queue write should replace the lost worker
        self.pool.write(0, 'Hello, Worker')
        assert len(self.pool) == 2


@pytest.mark.usefixtures("disable_database_settings")
class TestTaskDispatcher:
    @property
    def tm(self):
        return TaskWorker()

    def test_function_dispatch(self):
        result = self.tm.perform_work({'task': 'awx.main.tests.functional.test_dispatch.add', 'args': [2, 2]})
        assert result == 4

    def test_function_dispatch_must_be_decorated(self):
        result = self.tm.perform_work({'task': 'awx.main.tests.functional.test_dispatch.restricted', 'args': [2, 2]})
        assert isinstance(result, ValueError)
        assert str(result) == 'awx.main.tests.functional.test_dispatch.restricted is not decorated with @task()'  # noqa

    def test_method_dispatch(self):
        result = self.tm.perform_work({'task': 'awx.main.tests.functional.test_dispatch.Adder', 'args': [2, 2]})
        assert result == 4

    def test_method_dispatch_must_be_decorated(self):
        result = self.tm.perform_work({'task': 'awx.main.tests.functional.test_dispatch.Restricted', 'args': [2, 2]})
        assert isinstance(result, ValueError)
        assert str(result) == 'awx.main.tests.functional.test_dispatch.Restricted is not decorated with @task()'  # noqa

    def test_python_function_cannot_be_imported(self):
        result = self.tm.perform_work(
            {
                'task': 'os.system',
                'args': ['ls'],
            }
        )
        assert isinstance(result, ValueError)
        assert str(result) == 'os.system is not a valid awx task'  # noqa

    def test_undefined_function_cannot_be_imported(self):
        result = self.tm.perform_work({'task': 'awx.foo.bar'})
        assert isinstance(result, ModuleNotFoundError)
        assert str(result) == "No module named 'awx.foo'"  # noqa


class TestTaskPublisher:
    def test_function_callable(self):
        assert add(2, 2) == 4

    def test_method_callable(self):
        assert Adder().run(2, 2) == 4

    def test_function_apply_async(self):
        message, queue = add.apply_async([2, 2], queue='foobar')
        assert message['args'] == [2, 2]
        assert message['kwargs'] == {}
        assert message['task'] == 'awx.main.tests.functional.test_dispatch.add'
        assert queue == 'foobar'

    def test_method_apply_async(self):
        message, queue = Adder.apply_async([2, 2], queue='foobar')
        assert message['args'] == [2, 2]
        assert message['kwargs'] == {}
        assert message['task'] == 'awx.main.tests.functional.test_dispatch.Adder'
        assert queue == 'foobar'

    def test_apply_async_queue_required(self):
        with pytest.raises(ValueError) as e:
            message, queue = add.apply_async([2, 2])
        assert "awx.main.tests.functional.test_dispatch.add: Queue value required and may not be None" == e.value.args[0]

    def test_queue_defined_in_task_decorator(self):
        message, queue = multiply.apply_async([2, 2])
        assert queue == 'hard-math'

    def test_queue_overridden_from_task_decorator(self):
        message, queue = multiply.apply_async([2, 2], queue='not-so-hard')
        assert queue == 'not-so-hard'

    def test_apply_with_callable_queuename(self):
        message, queue = add.apply_async([2, 2], queue=lambda: 'called')
        assert queue == 'called'


yesterday = tz_now() - datetime.timedelta(days=1)
minute = tz_now() - datetime.timedelta(seconds=120)
now = tz_now()


@pytest.mark.django_db
class TestJobReaper(object):
    @pytest.mark.parametrize(
        'status, execution_node, controller_node, modified, fail',
        [
            ('running', '', '', None, False),  # running, not assigned to the instance
            ('running', 'awx', '', None, True),  # running, has the instance as its execution_node
            ('running', '', 'awx', None, True),  # running, has the instance as its controller_node
            ('waiting', '', '', None, False),  # waiting, not assigned to the instance
            ('waiting', 'awx', '', None, False),  # waiting, was edited less than a minute ago
            ('waiting', '', 'awx', None, False),  # waiting, was edited less than a minute ago
            ('waiting', 'awx', '', yesterday, False),  # waiting, managed by another node, ignore
            ('waiting', '', 'awx', yesterday, True),  # waiting, assigned to the controller_node, stale
        ],
    )
    def test_should_reap(self, status, fail, execution_node, controller_node, modified):
        i = Instance(hostname='awx')
        i.save()
        j = Job(
            status=status,
            execution_node=execution_node,
            controller_node=controller_node,
            start_args='SENSITIVE',
        )
        j.save()
        if modified:
            # we have to edit the modification time _without_ calling save()
            # (because .save() overwrites it to _now_)
            Job.objects.filter(id=j.id).update(modified=modified)
        reaper.reap(i)
        reaper.reap_waiting(i)
        job = Job.objects.first()
        if fail:
            assert job.status == 'failed'
            assert 'marked as failed' in job.job_explanation
            assert job.start_args == ''
        else:
            assert job.status == status

    @pytest.mark.parametrize(
        'excluded_uuids, fail, started',
        [
            (['abc123'], False, None),
            ([], False, None),
            ([], True, minute),
        ],
    )
    def test_do_not_reap_excluded_uuids(self, excluded_uuids, fail, started):
        """Modified Test to account for ref_time in reap()"""
        i = Instance(hostname='awx')
        i.save()
        j = Job(
            status='running',
            execution_node='awx',
            controller_node='',
            start_args='SENSITIVE',
            celery_task_id='abc123',
        )
        j.save()
        if started:
            Job.objects.filter(id=j.id).update(started=started)

        # if the UUID is excluded, don't reap it
        reaper.reap(i, excluded_uuids=excluded_uuids, ref_time=now)
        job = Job.objects.first()

        if fail:
            assert job.status == 'failed'
            assert 'marked as failed' in job.job_explanation
            assert job.start_args == ''
        else:
            assert job.status == 'running'

    def test_workflow_does_not_reap(self):
        i = Instance(hostname='awx')
        i.save()
        j = WorkflowJob(status='running', execution_node='awx')
        j.save()
        reaper.reap(i)

        assert WorkflowJob.objects.first().status == 'running'

    def test_should_not_reap_new(self):
        """
        This test is designed specifically to ensure that jobs that are launched after the dispatcher has provided a list of UUIDs aren't reaped.
        It is very racy and this test is designed with that in mind
        """
        i = Instance(hostname='awx')
        # ref_time is set to 10 seconds in the past to mimic someone launching a job in the heartbeat window.
        ref_time = tz_now() - datetime.timedelta(seconds=10)
        # creating job at current time
        job = Job.objects.create(status='running', controller_node=i.hostname)
        reaper.reap(i, ref_time=ref_time)
        # explictly refreshing from db to ensure up to date cache
        job.refresh_from_db()
        assert job.started > ref_time
        assert job.status == 'running'
        assert job.job_explanation == ''


@pytest.mark.django_db
class TestScheduler:
    def test_too_many_schedules_freak_out(self):
        with pytest.raises(RuntimeError):
            Scheduler({'job1': {'schedule': datetime.timedelta(seconds=1)}, 'job2': {'schedule': datetime.timedelta(seconds=1)}})

    def test_spread_out(self):
        scheduler = Scheduler(
            {
                'job1': {'schedule': datetime.timedelta(seconds=16)},
                'job2': {'schedule': datetime.timedelta(seconds=16)},
                'job3': {'schedule': datetime.timedelta(seconds=16)},
                'job4': {'schedule': datetime.timedelta(seconds=16)},
            }
        )
        assert [job.offset for job in scheduler.jobs] == [0, 4, 8, 12]

    def test_missed_schedule(self, mocker):
        scheduler = Scheduler({'job1': {'schedule': datetime.timedelta(seconds=10)}})
        assert scheduler.jobs[0].missed_runs(time.time() - scheduler.global_start) == 0
        mocker.patch('awx.main.dispatch.periodic.time.time', return_value=scheduler.global_start + 50)
        scheduler.get_and_mark_pending()
        assert scheduler.jobs[0].missed_runs(50) > 1

    def test_advance_schedule(self, mocker):
        scheduler = Scheduler(
            {
                'job1': {'schedule': datetime.timedelta(seconds=30)},
                'joba': {'schedule': datetime.timedelta(seconds=20)},
                'jobb': {'schedule': datetime.timedelta(seconds=20)},
            }
        )
        for job in scheduler.jobs:
            # HACK: the offsets automatically added make this a hard test to write... so remove offsets
            job.offset = 0.0
        mocker.patch('awx.main.dispatch.periodic.time.time', return_value=scheduler.global_start + 29)
        to_run = scheduler.get_and_mark_pending()
        assert set(job.name for job in to_run) == set(['joba', 'jobb'])
        mocker.patch('awx.main.dispatch.periodic.time.time', return_value=scheduler.global_start + 39)
        to_run = scheduler.get_and_mark_pending()
        assert len(to_run) == 1
        assert to_run[0].name == 'job1'

    @staticmethod
    def get_job(scheduler, name):
        for job in scheduler.jobs:
            if job.name == name:
                return job

    def test_scheduler_debug(self, mocker):
        scheduler = Scheduler(
            {
                'joba': {'schedule': datetime.timedelta(seconds=20)},
                'jobb': {'schedule': datetime.timedelta(seconds=50)},
                'jobc': {'schedule': datetime.timedelta(seconds=500)},
                'jobd': {'schedule': datetime.timedelta(seconds=20)},
            }
        )
        rel_time = 119.9  # slightly under the 6th 20-second bin, to avoid offset problems
        current_time = scheduler.global_start + rel_time
        mocker.patch('awx.main.dispatch.periodic.time.time', return_value=current_time - 1.0e-8)
        self.get_job(scheduler, 'jobb').mark_run(rel_time)
        self.get_job(scheduler, 'jobd').mark_run(rel_time - 20.0)

        output = scheduler.debug()
        data = yaml.safe_load(output)
        assert data['schedule_list']['jobc']['last_run_seconds_ago'] is None
        assert data['schedule_list']['joba']['missed_runs'] == 4
        assert data['schedule_list']['jobd']['missed_runs'] == 3
        assert data['schedule_list']['jobd']['completed_runs'] == 1
        assert data['schedule_list']['jobb']['next_run_in_seconds'] > 25.0
