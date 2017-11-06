# Copyright (C) 2017 Linaro Limited
#
# Author: Remi Duraffort <remi.duraffort@linaro.org>
#
# This file is part of LAVA Dispatcher.
#
# LAVA Dispatcher is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# LAVA Dispatcher is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along
# with this program; if not, see <http://www.gnu.org/licenses>.

from django.core.management.base import BaseCommand

from lava_scheduler_app.models import (
    Device,
    DeviceType,
)

import errno
import os
import re


def is_device_type_retired(dt):
    """
    Return True if all devices of this type are RETIRED.
    """
    return all([device.status == Device.RETIRED for device in dt.device_set.all()])


def is_device_type_exclusive(dt):
    return all([device.is_exclusive or device.status == Device.RETIRED for device in dt.device_set.all()])


class Command(BaseCommand):
    help = """
Writes health check jobs into /etc/lava-server/dispatcher-config/health-checks
using the existing database entry for the health check job
of the device-type. Optionally deletes the health check job
entry from the database as long as all devices of this type
are exclusive to V2.

If devices of one type extend different jinja templates, one
health check will be used for each variant."""

    def add_arguments(self, parser):
        parser.add_argument("--clean", action="store_true", default=False,
                            help="Remove from the database the health-checks that were moved")

    def handle(self, *_, **options):
        health_dir = "/etc/lava-server/dispatcher-config/health-checks"
        self.stdout.write("Moving health checks to %s:" % health_dir)

        # Create the directory
        try:
            os.mkdir(health_dir, 0o755)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                self.stderr.write("Unable to create the directory: %s" % str(exc))
                return

        dt_skipped = []
        extends_pattern = re.compile(r"^{% extends '([^.]+).jinja2' %}$")
        for dt in DeviceType.objects.order_by('name'):

            if not dt.health_check_job or not dt.display or is_device_type_retired(dt):
                dt_skipped.append((dt.name, False))
                continue

            # Dump to the filesystem
            self.stdout.write("* %s" % dt.name)
            filename = os.path.join(health_dir, dt.name + '.yaml')
            with open(filename, 'w') as f_out:
                f_out.write(dt.health_check_job)

            # Remove the health check from the data base (if needed)
            if options["clean"]:
                if is_device_type_exclusive(dt) or is_device_type_retired(dt) or not dt.display:
                    dt.health_check_job = None
                    dt.save(update_fields=["health_check_job"])
                else:
                    self.stderr.write("-> Not cleaning %s, some devices still support V1" % dt.name)

        self.stdout.write("Device types skipped:")
        for (dt, has_health_check) in dt_skipped:
            if has_health_check:
                self.stdout.write("* %s (v1 health check)" % dt)
            else:
                self.stdout.write("* %s" % dt)

        self.stdout.write("Checking devices:")
        for device in Device.objects.exclude(status=Device.RETIRED).order_by('hostname'):
            device_dict = device.load_configuration(output_format="raw")
            if not device_dict:
                self.stderr.write("* %s => no device dictionary" % device.hostname)
                continue
            extends = device.get_extends()
            if not extends:
                self.stderr.write("* %s => no 'extends' found" % device.hostname)
                continue

            filename = os.path.join("/etc/lava-server/dispatcher-config/health-checks",
                                    "%s.yaml" % extends)
            if os.path.exists(filename):
                self.stdout.write("* %s => %s.yaml" % (device.hostname, extends))
            else:
                self.stderr.write("* %s => no health check found for %s.yaml" % (device.hostname, extends))
