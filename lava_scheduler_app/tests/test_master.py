import os
import sys
import logging
import unittest
from lava_scheduler_app.dbutils import (
    create_job,
    select_device,
)
from lava_scheduler_app.tests.test_pipeline import YamlFactory, TestCaseWithFactory
from lava_scheduler_app.models import (
    Device,
    Tag,
    TestJob,
    Worker
)
from lava_dispatcher.utils.shell import infrastructure_error


class MasterTest(TestCaseWithFactory):  # pylint: disable=too-many-ancestors

    def setUp(self):
        super(MasterTest, self).setUp()
        self.factory = YamlFactory()
        self.device_type = self.factory.make_device_type()
        self.worker, _ = Worker.objects.get_or_create(hostname='localhost')
        self.remote, _ = Worker.objects.get_or_create(hostname='remote')
        # exclude remote from the list
        self.dispatchers = [self.worker.hostname]
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        logger = logging.getLogger('unittests')
        logger.disabled = True
        logger.propagate = False
        logger = logging.getLogger('dispatcher')
        logging.disable(logging.DEBUG)
        logger.disabled = True
        logger.propagate = False

    def restart(self):  # pylint: disable=no-self-use
        # make sure the DB is in a clean state wrt devices and jobs
        Device.objects.all().delete()  # pylint: disable=no-member
        TestJob.objects.all().delete()  # pylint: disable=no-member
        Tag.objects.all().delete()

    @unittest.skipIf(infrastructure_error('qemu-system-x86_64'),
                     'qemu-system-x86_64 not installed')
    def test_select_device(self):
        self.restart()
        hostname = 'fakeqemu3'
        device = self.factory.make_device(self.device_type, hostname)
        job = TestJob.from_yaml_and_user(
            self.factory.make_job_yaml(),
            self.factory.make_user())
        # this uses the system jinja2 path - local changes to the qemu.jinja2
        # will not be available.
        selected = select_device(job, self.dispatchers)
        self.assertIsNone(selected)
        job.actual_device = device
        selected = select_device(job, self.dispatchers)
        self.assertIsNone(selected)
        device.worker_host = self.worker
        selected = select_device(job, self.dispatchers)
        self.assertIsNone(selected)
        # device needs to be in reserved state
        # fake up the assignment which needs a separate test
        job.actual_device = device
        job.save()
        device.current_job = job
        device.status = Device.RESERVED
        device.save()
        selected = select_device(job, self.dispatchers)
        self.assertEqual(selected, device)
        # print(selected)  # pylint: disable=superfluous-parens

    def test_job_handlers(self):
        self.restart()
        hostname = 'fakeqemu3'
        device = self.factory.make_device(self.device_type, hostname)
        job = TestJob.from_yaml_and_user(
            self.factory.make_job_yaml(),
            self.factory.make_user())
        selected = select_device(job, self.dispatchers)
        self.assertIsNone(selected)
        job.actual_device = device
        selected = select_device(job, self.dispatchers)
        self.assertIsNone(selected)
        device.worker_host = self.worker
        selected = select_device(job, self.dispatchers)
        self.assertIsNone(selected)
        create_job(job, device)
        self.assertEqual(job.actual_device, device)
        self.assertEqual(device.status, Device.RESERVED)

    def test_dispatcher_restart(self):
        self.restart()
        hostname = 'fakeqemu3'
        device = self.factory.make_device(self.device_type, hostname)
        job = TestJob.from_yaml_and_user(
            self.factory.make_job_yaml(),
            self.factory.make_user())
        job.actual_device = device
        self.assertEqual(job.status, TestJob.SUBMITTED)
        device.worker_host = self.remote
        selected = select_device(job, self.dispatchers)
        self.assertIsNone(selected)
        self.assertEqual(job.status, TestJob.SUBMITTED)
        create_job(job, device)
        self.assertEqual(job.actual_device, device)
        self.assertEqual(device.status, Device.RESERVED)
        selected = select_device(job, self.dispatchers)
        self.assertIsNone(selected)
        self.assertEqual(job.status, TestJob.SUBMITTED)
