import os
import json
import logging
from django.template import defaultfilters as filters
from django.utils.safestring import mark_safe
import django_tables2 as tables
from lava_scheduler_app.models import (
    TestJob,
    Device,
    DeviceType,
    Worker,
    DeviceStateTransition,
)
from lava.utils.lavatable import LavaTable
from django.db.models import Q
from django.utils import timezone
from markupsafe import escape


# The query_set is based in the view, so split that into a View class
# Avoid putting queryset functionality into tables.
# base new views on FiltereSingleTableView. These classes can go into
# views.py later.

# No function in this file is directly accessible via urls.py - those
# functions need to go in views.py

# pylint: disable=invalid-name


class IDLinkColumn(tables.Column):

    def __init__(self, verbose_name="ID", **kw):
        kw['verbose_name'] = verbose_name
        super(IDLinkColumn, self).__init__(**kw)

    def render(self, record, table=None):  # pylint: disable=arguments-differ,unused-argument
        return pklink(record)


class RestrictedIDLinkColumn(IDLinkColumn):

    def render(self, record, table=None):
        user = table.context.get('request').user
        if record.can_view(user):
            return pklink(record)
        else:
            return record.pk


def pklink(record):
    job_id = record.pk
    if isinstance(record, TestJob):
        if record.sub_jobs_list:
            job_id = record.sub_id
    return mark_safe(
        '<a href="%s" title="job summary">%s</a>' % (
            record.get_absolute_url(),
            escape(job_id)))


class ExpandedStatusColumn(tables.Column):

    def __init__(self, verbose_name="Expanded Status", **kw):
        kw['verbose_name'] = verbose_name
        super(ExpandedStatusColumn, self).__init__(**kw)

    def render(self, record):
        """
        Expands the device status to include details of the job if the
        device is Reserved or Running. Logs error if reserved or running
        with no current job.
        """
        logger = logging.getLogger('lava_scheduler_app')
        if record.status == Device.RUNNING and record.current_job:
            return mark_safe("Running job #%s - %s submitted by %s" % (
                pklink(record.current_job),
                record.current_job.description,
                record.current_job.submitter))
        elif record.status == Device.RESERVED and record.current_job:
            return mark_safe("Reserved for job #%s %s - %s submitted by %s" % (
                pklink(record.current_job),
                record.current_job.status,
                record.current_job.description,
                record.current_job.submitter))
        elif record.status == Device.RESERVED and not record.current_job:
            logger.error("%s is reserved with no current job.", record)
            return mark_safe("Reserved with <b>no current job</b>.")
        elif record.status == Device.RUNNING and not record.current_job:
            logger.error("%s is running with no current job.", record)
            return mark_safe("Running with <b>no current job</b>.")
        else:
            return Device.STATUS_CHOICES[record.status][1]


class RestrictedDeviceColumn(tables.Column):

    def __init__(self, verbose_name="Submissions restricted to", **kw):
        kw['verbose_name'] = verbose_name
        super(RestrictedDeviceColumn, self).__init__(**kw)

    def render(self, record):
        """
        If the strings here are changed, ensure the strings in the restriction_query
        are changed to match.
        :param record: a database record
        :return: a text string describing the restrictions on this device.
        """
        label = None
        if record.status == Device.RETIRED:
            return "Retired, no submissions possible."
        if record.is_public:
            return ""
        if record.user:
            label = record.user.email
        if record.group:
            label = "group %s" % record.group
        return label


def all_jobs_with_custom_sort():
    jobs = TestJob.objects.select_related(
        "actual_device",
        "actual_device__user",
        "actual_device__group",
        "actual_device__device_type",
        "requested_device",
        "requested_device_type",
        "submitter",
        "user",
        "group").extra(select={'device_sort': 'coalesce('
                                              'actual_device_id, '
                                              'requested_device_id, requested_device_type_id)',
                               'duration_sort': "date_trunc('second', end_time - start_time)"}).all()
    return jobs.order_by('-submit_time')


class JobTable(LavaTable):
    """
    Common table for the TestJob model.
    There is no need to derive from this class merely
    to change the queryset - do that in the View.
    Do inherit from JobTable if you want to add new columns
    or change the exclusion list, i.e. the structure of the
    table, not the data shown by the table.
    To preserve custom handling of fields like id, device and duration,
    ensure those are copied into the new class.
    """
    def __init__(self, *args, **kwargs):
        super(JobTable, self).__init__(*args, **kwargs)
        self.length = 25

    id = tables.Column(verbose_name="ID")
    actions = tables.TemplateColumn(
        template_name="lava_scheduler_app/job_actions_field.html")
    actions.orderable = False
    device = tables.Column(accessor='device_sort')
    duration = tables.Column(accessor='duration_sort')
    duration.orderable = False
    submit_time = tables.DateColumn(format=u"Nd, g:ia")
    end_time = tables.DateColumn(format=u"Nd, g:ia")

    def render_status(self, record):
        text = 'text-default'
        if record.status == TestJob.COMPLETE:
            text = 'text-success'
        elif record.status == TestJob.RUNNING:
            text = 'text-info'
        elif record.status == TestJob.INCOMPLETE:
            text = 'text-danger'
        elif record.status in [TestJob.CANCELING, TestJob.CANCELED]:
            text = 'text-warning'
        elif record.status == TestJob.SUBMITTED:
            text = 'text-muted'
        return mark_safe('<span class="%s"><strong>%s</strong></span>' %
                         (text, TestJob.STATUS_CHOICES[record.status][1]))

    def render_device(self, record):
        if record.actual_device:
            device_type = record.actual_device.device_type
            retval = pklink(record.actual_device)
        elif record.requested_device:
            device_type = record.requested_device.device_type
            retval = pklink(record.requested_device)
        elif record.requested_device_type:
            device_type = record.requested_device_type
            retval = mark_safe('<i>%s</i>' % escape(record.requested_device_type.pk))
        elif record.dynamic_connection:
            return 'connection'
        else:
            return '-'
        if not device_type.some_devices_visible_to(self.context.get('request').user):
            return "Unavailable"
        return retval

    def render_description(self, value):  # pylint: disable=no-self-use
        if value:
            return value
        else:
            return ''

    class Meta(LavaTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        model = TestJob
        # alternatively, use 'fields' value to include specific fields.
        exclude = [
            'is_public',
            'user',
            'group',
            'sub_id',
            'target_group',
            'submit_token',
            'health_check',
            'definition',
            'original_definition',
            'multinode_definition',
            'admin_notifications',
            '_results_link',
            '_results_bundle',
            'requested_device_type',
            'start_time',
            'requested_device',
            'log_file',
            'actual_device',
        ]
        fields = (
            'id', 'actions', 'status', 'priority', 'device',
            'description', 'submitter', 'submit_time', 'end_time',
            'duration'
        )
        sequence = (
            'id', 'actions', 'status', 'priority', 'device',
            'description', 'submitter', 'submit_time', 'end_time',
            'duration'
        )
        # filter view functions supporting relational mappings and returning a Q()
        queries = {
            'device_query': "device",  # active_device
            'owner_query': "submitter",  # submitter
            'job_status_query': 'status',
        }
        # fields which can be searched with default __contains queries
        # note the enums cannot be searched this way.
        searches = {
            'id': 'contains',
            'sub_id': 'contains',
            'description': 'contains'
        }
        # dedicated time-based search fields
        times = {
            'submit_time': 'hours',
            'end_time': 'hours',
        }


class IndexJobTable(JobTable):

    id = tables.Column(verbose_name="ID")
    actions = tables.TemplateColumn(
        template_name="lava_scheduler_app/job_actions_field.html")
    actions.orderable = False
    device = tables.Column(accessor='device_sort')
    submit_time = tables.DateColumn("Nd, g:ia")
    end_time = tables.DateColumn("Nd, g:ia")

    def __init__(self, *args, **kwargs):
        super(IndexJobTable, self).__init__(*args, **kwargs)
        self.length = 25

    class Meta(JobTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        fields = (
            'id', 'actions', 'status', 'priority', 'device',
            'description', 'submitter', 'submit_time'
        )
        sequence = (
            'id', 'actions', 'status', 'priority', 'device',
            'description', 'submitter', 'submit_time'
        )
        exclude = ('end_time', 'duration', )


class TagsColumn(tables.Column):

    def render(self, value):
        tag_id = 'tag-%s' % os.urandom(4).encode('hex')
        tags = ''
        values = list(value.all())
        if len(values) > 0:
            tags = '<p class="collapse" id="%s">' % tag_id
            tags += ',<br>'.join('<abbr data-toggle="tooltip" title="%s">%s</abbr>' % (tag.description, tag.name) for tag in values)
            tags += '</p><a class="btn btn-xs btn-success" data-toggle="collapse" data-target="#%s"><span class="glyphicon glyphicon-eye-open"></span></a>' % tag_id
        return mark_safe(tags)


class FailedJobTable(JobTable):

    id = tables.Column(verbose_name="ID")
    actions = tables.TemplateColumn(
        template_name="lava_scheduler_app/job_actions_field.html")
    actions.orderable = False
    device = tables.Column(accessor='device_sort')
    duration = tables.Column(accessor='duration_sort')
    duration.orderable = False
    failure_tags = TagsColumn()
    failure_comment = tables.Column()
    submit_time = tables.DateColumn("Nd, g:ia")
    end_time = tables.DateColumn("Nd, g:ia")

    def __init__(self, *args, **kwargs):
        super(FailedJobTable, self).__init__(*args, **kwargs)
        self.length = 10

    class Meta(JobTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        fields = (
            'id', 'actions', 'status', 'device', 'submit_time'
        )
        sequence = (
            'id', 'actions', 'status', 'device', 'submit_time'
        )
        exclude = ('submitter', 'end_time', 'priority', 'description')


class LongestJobTable(JobTable):

    id = tables.Column(verbose_name="ID")
    id.orderable = False
    actions = tables.TemplateColumn(
        template_name="lava_scheduler_app/job_actions_field.html")
    actions.orderable = False
    status = tables.Column()
    status.orderable = False
    device = tables.Column(accessor='actual_device')
    device.orderable = False
    priority = tables.Column()
    priority.orderable = False
    description = tables.Column()
    description.orderable = False
    submitter = tables.Column()
    submitter.orderable = False
    start_time = tables.Column()
    start_time.orderable = True
    submit_time = tables.Column()
    submit_time.orderable = False
    running = tables.Column(accessor='start_time', verbose_name='Running')
    running.orderable = False

    def __init__(self, *args, **kwargs):
        super(LongestJobTable, self).__init__(*args, **kwargs)
        self.length = 10

    def render_running(self, record):  # pylint: disable=no-self-use
        if not record.start_time:
            return ''
        return str(timezone.now() - record.start_time)

    def render_device(self, record):  # pylint: disable=no-self-use
        if record.actual_device:
            return pklink(record.actual_device)
        return ''

    class Meta(JobTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        fields = (
            'id', 'actions', 'status', 'device'
        )
        sequence = (
            'id', 'actions', 'status', 'device'
        )
        exclude = ('duration', 'end_time')


class OverviewJobsTable(JobTable):

    id = tables.Column(verbose_name="ID")
    id.orderable = False
    actions = tables.TemplateColumn(
        template_name="lava_scheduler_app/job_actions_field.html")
    actions.orderable = False
    device = tables.Column(accessor='device_sort')
    duration = tables.Column(accessor='duration_sort')
    duration.orderable = False
    submit_time = tables.DateColumn("Nd, g:ia")
    end_time = tables.DateColumn("Nd, g:ia")

    def __init__(self, *args, **kwargs):
        super(OverviewJobsTable, self).__init__(*args, **kwargs)
        self.length = 10

    class Meta(JobTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        fields = (
            'id', 'actions', 'status', 'priority', 'device',
            'description', 'submitter', 'submit_time', 'end_time',
            'duration'
        )
        sequence = (
            'id', 'actions'
        )


class RecentJobsTable(JobTable):

    id = tables.Column(verbose_name="ID")
    id.orderable = False
    actions = tables.TemplateColumn(
        template_name="lava_scheduler_app/job_actions_field.html")
    actions.orderable = False
    device = tables.Column(accessor='device_sort')
    log_level = tables.Column(accessor="definition", verbose_name="Log level")
    duration = tables.Column(accessor='duration_sort')
    duration.orderable = False
    submit_time = tables.DateColumn("Nd, g:ia")
    end_time = tables.DateColumn("Nd, g:ia")

    def __init__(self, *args, **kwargs):
        super(RecentJobsTable, self).__init__(*args, **kwargs)
        self.length = 10

    def render_log_level(self, record):  # pylint: disable=no-self-use
        try:
            data = json.loads(record.definition)
        except ValueError:
            return "debug"
        try:
            data['logging_level']
        except KeyError:
            return ""
        return data['logging_level'].lower()

    class Meta(JobTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        fields = (
            'id', 'actions', 'status', 'priority',
            'description', 'submitter', 'submit_time', 'end_time',
            'duration'
        )
        sequence = (
            'id', 'actions', 'status', 'priority',
            'description', 'submitter', 'submit_time', 'end_time',
            'duration', 'log_level'
        )
        exclude = ('device',)


class DeviceHealthTable(LavaTable):

    def __init__(self, *args, **kwargs):
        super(DeviceHealthTable, self).__init__(*args, **kwargs)
        self.length = 25

    def render_last_health_report_job(self, record):  # pylint: disable=no-self-use
        report = record.last_health_report_job
        if report is None:
            return ''
        else:
            return pklink(report)

    hostname = tables.TemplateColumn('''
    <a href="{{ record.get_absolute_url }}">{{ record.hostname }}</a>
    ''')
    worker_host = tables.TemplateColumn('''
    {% if record.is_master %}
    <b><a href="{{ record.worker_host.get_absolute_url }}">{{ record.worker_host }}</a></b>
    {% else %}
    <a href="{{ record.worker_host.get_absolute_url }}">{{ record.worker_host }}</a>
    {% endif %}
    ''')
    health_status = tables.Column()
    last_report_time = tables.DateColumn(
        verbose_name="last report time",
        accessor="last_health_report_job.end_time")
    last_health_report_job = tables.Column("last report job")

    class Meta(LavaTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        sequence = [
            'hostname', 'worker_host', 'health_status', 'last_report_time',
            'last_health_report_job'
        ]
        searches = {
            'hostname': 'contains',
        }
        queries = {
            'health_status_query': 'health_status',
        }


class DeviceTypeTable(LavaTable):

    def __init__(self, *args, **kwargs):
        super(DeviceTypeTable, self).__init__(*args, **kwargs)
        self.length = 50

    def render_idle(self, record):  # pylint: disable=no-self-use
        return record['idle'] if record['idle'] > 0 else ""

    def render_offline(self, record):  # pylint: disable=no-self-use
        return record['offline'] if record['offline'] > 0 else ""

    def render_busy(self, record):  # pylint: disable=no-self-use
        return record['busy'] if record['busy'] > 0 else ""

    def render_restricted(self, record):  # pylint: disable=no-self-use
        return record['restricted'] if record['restricted'] > 0 else ""

    def render_name(self, record):  # pylint: disable=no-self-use
        return pklink(DeviceType.objects.get(name=record['device_type']))

    def render_queue(self, record):  # pylint: disable=no-self-use
        count = TestJob.objects.filter(
            Q(status=TestJob.SUBMITTED),
            Q(requested_device_type=record['device_type']) |
            Q(requested_device__in=Device.objects.filter(device_type=record['device_type'])))\
            .only('status', 'requested_device_type', 'requested_device').count()
        return count if count > 0 else ""

    name = tables.Column(accessor='idle', verbose_name='Name')
    # the change in the aggregation breaks the accessor.
    name.orderable = False
    idle = tables.Column()
    offline = tables.Column()
    busy = tables.Column()
    restricted = tables.Column()
    # sadly, this needs to be not orderable as it would otherwise sort by the accessor.
    queue = tables.Column(accessor="idle", verbose_name="Queue", orderable=False)

    class Meta(LavaTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        model = DeviceType
        exclude = [
            'display', 'disable_health_check', 'health_check_job', 'owners_only',
            'architecture', 'health_denominator', 'health_frequency',
            'processor', 'cpu_model', 'bits', 'cores', 'core_count', 'description'
        ]
        searches = {
            'name': 'contains',
        }


class DeviceTable(LavaTable):

    def __init__(self, *args, **kwargs):
        super(DeviceTable, self).__init__(*args, **kwargs)
        self.length = 50

    def render_device_type(self, record):  # pylint: disable=no-self-use
        return pklink(record.device_type)

    hostname = tables.TemplateColumn('''
    <a href="{{ record.get_absolute_url }}">{{ record.hostname }}</a>
    ''')
    worker_host = tables.TemplateColumn('''
    {% if record.is_master %}
    <b><a href="{{ record.worker_host.get_absolute_url }}">{{ record.worker_host }}</a></b>
    {% else %}
    <a href="{{ record.worker_host.get_absolute_url }}">{{ record.worker_host }}</a>
    {% endif %}
    ''')
    device_type = tables.Column()
    status = ExpandedStatusColumn("status")
    owner = RestrictedDeviceColumn()
    owner.orderable = False
    health_status = tables.Column(verbose_name='Health')
    tags = TagsColumn()

    json = tables.Column(accessor='is_pipeline', verbose_name='JSON jobs')

    def render_json(self, record):  # pylint: disable=no-self-use
        if record.is_exclusive:
            return mark_safe('<span class="glyphicon glyphicon-remove text-danger"></span>')
        return mark_safe('<span class="glyphicon glyphicon-ok"></span>')

    pipeline = tables.Column(accessor='is_pipeline', verbose_name='Pipeline jobs')

    def render_pipeline(self, record):  # pylint: disable=no-self-use
        if record.is_pipeline:
            return mark_safe('<span class="glyphicon glyphicon-ok"></span>')
        return mark_safe('<span class="glyphicon glyphicon-remove text-danger"></span>')

    class Meta(LavaTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        model = Device
        exclude = [
            'user', 'group', 'is_public', 'device_version',
            'physical_owner', 'physical_group', 'description',
            'current_job', 'last_health_report_job', 'is_pipeline'
        ]
        sequence = [
            'hostname', 'worker_host', 'device_type', 'status',
            'owner', 'health_status', 'json', 'pipeline'
        ]
        searches = {
            'hostname': 'contains',
        }
        queries = {
            'device_type_query': 'device_type',
            'device_status_query': 'status',
            'health_status_query': 'health_status',
            'restriction_query': 'restrictions',
            'tags_query': 'tags'
        }


class NoDTDeviceTable(DeviceTable):

    class Meta(LavaTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        exclude = [
            'device_type',
            'user', 'group', 'is_public', 'device_version',
            'physical_owner', 'physical_group', 'description',
            'current_job', 'last_health_report_job'
        ]
        searches = {
            'hostname': 'contains',
        }
        queries = {
            'device_status_query': 'status',
            'health_status_query': 'health_status',
        }


class WorkerTable(tables.Table):  # pylint: disable=too-few-public-methods,no-init

    def __init__(self, *args, **kwargs):
        super(WorkerTable, self).__init__(*args, **kwargs)
        self.length = 10
        self.show_help = True

    hostname = tables.TemplateColumn('''
    {% if record.is_master %}
    <b><a href="{{ record.get_absolute_url }}">{{ record.hostname }}</a></b>
    {% else %}
    <a href="{{ record.get_absolute_url }}">{{ record.hostname }}</a>
    {% endif %}
    ''')

    is_master = tables.Column()

    class Meta(LavaTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        model = Worker
        exclude = [
            'rpc2_url', 'display'
        ]
        sequence = [
            'hostname', 'description', 'is_master'
        ]


class NoWorkerDeviceTable(DeviceTable):

    class Meta(LavaTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        exclude = [
            'worker_host',
            'user', 'group', 'is_public', 'device_version',
            'physical_owner', 'physical_group', 'description',
            'current_job', 'last_health_report_job'
        ]
        searches = {
            'hostname': 'contains',
        }
        queries = {
            'device_status_query': 'status',
            'health_status_query': 'health_status',
        }


class HealthJobSummaryTable(tables.Table):  # pylint: disable=too-few-public-methods

    length = 10
    Duration = tables.Column()
    Complete = tables.Column()
    Failed = tables.Column()

    class Meta(LavaTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        model = None


class DeviceTransitionTable(LavaTable):

    def render_created_on(self, record):  # pylint: disable=no-self-use
        t = record
        base = "<a href='/scheduler/transition/%s'>%s</a>" \
               % (record.id, filters.date(t.created_on, "Y-m-d H:i"))
        return mark_safe(base)

    def render_transition(self, record):  # pylint: disable=no-self-use
        t = record
        return mark_safe(
            '%s &rarr; %s' % (t.get_old_state_display(), t.get_new_state_display(),))

    created_on = tables.Column('when')
    transition = tables.Column('transition', orderable=False, accessor='old_state')
    created_by = tables.Column('by', accessor='created_by')
    message = tables.TemplateColumn('''
    <div class="edit_transition" id="{{ record.id }}" style="width: 100%">{{ record.message }}</div>
        ''')

    class Meta(LavaTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        model = DeviceStateTransition
        exclude = [
            'device', 'job', 'old_state', 'new_state'
        ]
        sequence = [
            'id', 'created_on', 'transition', 'created_by', 'message'
        ]
        searches = {}
        queries = {}
        times = {}


class QueueJobsTable(JobTable):

    id = tables.Column(verbose_name="ID")
    id.orderable = False
    actions = tables.TemplateColumn(
        template_name="lava_scheduler_app/job_actions_field.html")
    actions.orderable = False
    device = tables.Column(accessor='device_sort')
    in_queue = tables.TemplateColumn('''
    for {{ record.submit_time|timesince }}
    ''')
    in_queue.orderable = False
    submit_time = tables.DateColumn("Nd, g:ia")
    end_time = tables.DateColumn("Nd, g:ia")

    def __init__(self, *args, **kwargs):
        super(QueueJobsTable, self).__init__(*args, **kwargs)
        self.length = 50

    class Meta(JobTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        fields = (
            'id', 'actions', 'device', 'description', 'submitter',
            'submit_time', 'in_queue'
        )
        sequence = (
            'id', 'actions', 'device', 'description', 'submitter',
            'submit_time', 'in_queue'
        )
        exclude = ('status', 'priority', 'end_time', 'duration')


class DeviceTypeTransitionTable(DeviceTransitionTable):

    device = tables.TemplateColumn('''
    <a href='/scheduler/device/{{ record.device.hostname }}'>{{ record.device.hostname}}</a>
        ''')

    class Meta(LavaTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        model = DeviceStateTransition
        exclude = [
            'id', 'job', 'old_state', 'new_state'
        ]
        sequence = [
            'device', 'created_on', 'transition', 'created_by', 'message'
        ]
        searches = {}
        queries = {}
        times = {}


class OnlineDeviceTable(DeviceTable):

    def __init__(self, *args, **kwargs):
        super(OnlineDeviceTable, self).__init__(*args, **kwargs)
        self.length = 25

    def render_status(self, record):  # pylint: disable=no-self-use
        status = Device.STATUS_CHOICES[record.status][1]
        try:
            t = DeviceStateTransition.objects.filter(device=record).order_by('-id')[0]
        except IndexError:
            return status
        else:
            return "%s (reason: %s)" % (status, t.message)

    class Meta(LavaTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        exclude = [
            'worker_host', 'user', 'group', 'is_public', 'device_version',
            'physical_owner', 'physical_group', 'description', 'current_job',
            'last_health_report_job', 'health_status'
        ]
        sequence = [
            'hostname', 'device_type', 'status', 'owner'
        ]
        searches = {
            'hostname': 'contains',
        }
        queries = {
            'device_type_query': 'device_type',
            'device_status_query': 'status',
            'restriction_query': 'restrictions',
        }


class PassingHealthTable(DeviceHealthTable):

    def __init__(self, *args, **kwargs):
        super(PassingHealthTable, self).__init__(*args, **kwargs)
        self.length = 25

    def render_device_type(self, record):  # pylint: disable=no-self-use
        return pklink(record.device_type)

    def render_last_health_report_job(self, record):  # pylint: disable=no-self-use
        report = record.last_health_report_job
        base = "<a href='/scheduler/job/%s'>%s</a>" % (report.id, report)
        return mark_safe(base)

    device_type = tables.Column()

    class Meta(LavaTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        exclude = [
            'worker_host', 'last_report_time'
        ]
        sequence = [
            'hostname', 'device_type', 'health_status',
            'last_health_report_job'
        ]
        searches = {
            'hostname': 'contains',
        }
        queries = {
            'health_status_query': 'health_status',
        }


class RunningTable(LavaTable):
    """
    Provide the admins with some information on the activity of the instance.
    Multinode jobs reserve devices whilst still in SUBMITITED
    Except for dynamic connections, there should not be more active jobs than active devices of
    any particular DeviceType.
    """

    def __init__(self, *args, **kwargs):
        super(RunningTable, self).__init__(*args, **kwargs)
        self.length = 50

    # deprecated: dynamic connections are TestJob without a device

    def render_jobs(self, record):  # pylint: disable=no-self-use
        count = TestJob.objects.filter(
            Q(status=TestJob.RUNNING),
            Q(requested_device_type=record.name) |
            Q(requested_device__in=Device.objects.filter(device_type=record.name)) |
            Q(actual_device__in=Device.objects.filter(device_type=record.name))
        ).count()
        return count if count > 0 else ""

    def render_reserved(self, record):  # pylint: disable=no-self-use
        count = Device.objects.filter(device_type=record.name, status=Device.RESERVED).count()
        return count if count > 0 else ""

    def render_running(self, record):  # pylint: disable=no-self-use
        count = Device.objects.filter(device_type=record.name, status=Device.RUNNING).count()
        return count if count > 0 else ""

    name = IDLinkColumn(accessor='name')

    reserved = tables.Column(accessor='display', orderable=False, verbose_name='Reserved')
    running = tables.Column(accessor='display', orderable=False, verbose_name='Running')
    jobs = tables.Column(accessor='display', orderable=False, verbose_name='Jobs')

    class Meta(LavaTable.Meta):  # pylint: disable=too-few-public-methods,no-init,no-self-use
        model = DeviceType
        sequence = [
            'name', 'reserved', 'running', 'jobs'
        ]
        exclude = [
            'display', 'disable_health_check', 'health_check_job', 'owners_only', 'architecture',
            'processor', 'cpu_model', 'bits', 'cores', 'core_count', 'description'
        ]
