#
# Copyright (C) 2016 by frePPLe bv
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import os
import errno
import gzip
import logging

from datetime import datetime
from time import localtime, strftime
from django.conf import settings
from django.db import connections, DEFAULT_DB_ALIAS
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.utils.translation import gettext_lazy as _

from freppledb.common.middleware import _thread_locals
from freppledb.common.models import User
from freppledb.common.report import GridReport
from freppledb import __version__
from freppledb.execute.models import Task
from freppledb.output.views import resource
from freppledb.output.views import buffer

logger = logging.getLogger(__name__)


def timesince(st):
    return str(datetime.now() - st).split(".")[0]


class Command(BaseCommand):
    help = """
    Exports tables from the frePPLe database to CSV files in a folder
    """

    requires_system_checks = []

    # Any sql statements that should be executed before the export
    pre_sql_statements = ()

    # Any SQL statements that should be executed before the export
    post_sql_statements = ()

    statements = [
        {
            "filename": "purchaseorder.csv.gz",
            "folder": "export",
            "sql": """COPY
                (select source, lastmodified, reference, status , reference, quantity,
                to_char(startdate,'%s HH24:MI:SS') as "ordering date",
                to_char(enddate,'%s HH24:MI:SS') as "receipt date",
                criticality, EXTRACT(EPOCH FROM delay) as delay,
                owner_id, item_id, location_id, supplier_id from operationplan
                where status <> 'confirmed' and type='PO')
                TO STDOUT WITH CSV HEADER"""
            % (settings.DATE_FORMAT_JS, settings.DATE_FORMAT_JS),
        },
        {
            "filename": "distributionorder.csv.gz",
            "folder": "export",
            "sql": """COPY
                (select source, lastmodified, reference, status, reference, quantity,
                to_char(startdate,'%s HH24:MI:SS') as "ordering date",
                to_char(enddate,'%s HH24:MI:SS') as "receipt date",
                criticality, EXTRACT(EPOCH FROM delay) as delay,
                plan, destination_id, item_id, origin_id from operationplan
                where status <> 'confirmed' and type='DO')
                TO STDOUT WITH CSV HEADER"""
            % (settings.DATE_FORMAT_JS, settings.DATE_FORMAT_JS),
        },
        {
            "filename": "manufacturingorder.csv.gz",
            "folder": "export",
            "sql": """COPY
                (select source, lastmodified, reference, status ,reference ,quantity,
                to_char(startdate,'%s HH24:MI:SS') as startdate,
                to_char(enddate,'%s HH24:MI:SS') as enddate,
                criticality, EXTRACT(EPOCH FROM delay) as delay,
                operation_id, owner_id, plan, item_id, batch
                from operationplan where status <> 'confirmed' and type='MO')
                TO STDOUT WITH CSV HEADER"""
            % (settings.DATE_FORMAT_JS, settings.DATE_FORMAT_JS),
        },
        {
            "filename": "problems.csv.gz",
            "folder": "export",
            "sql": """COPY (
                select
                    entity, owner, name, description,
                    to_char(startdate,'%s HH24:MI:SS') as startdate,
                    to_char(enddate,'%s HH24:MI:SS') as enddate,
                    weight
                from out_problem
                where name <> 'material excess'
                order by entity, name, startdate
                ) TO STDOUT WITH CSV HEADER"""
            % (settings.DATE_FORMAT_JS, settings.DATE_FORMAT_JS),
        },
        {
            "filename": "operationplanmaterial.csv.gz",
            "folder": "export",
            "sql": """COPY (
                select
                    item_id as item, location_id as location, quantity,
                    to_char(flowdate,'%s HH24:MI:SS') as date, onhand,
                    operationplan_id as operationplan, status
                from operationplanmaterial
                order by item_id, location_id, flowdate, quantity desc
                ) TO STDOUT WITH CSV HEADER"""
            % settings.DATE_FORMAT_JS,
        },
        {
            "filename": "operationplanresource.csv.gz",
            "folder": "export",
            "sql": """COPY (
                select
                    operationplanresource.resource_id as resource,
                    to_char(operationplan.startdate,'%s HH24:MI:SS') as startdate,
                    to_char(operationplan.enddate,'%s HH24:MI:SS') as enddate,
                    operationplanresource.setup,
                    operationplanresource.operationplan_id as operationplan,
                    operationplan.status
                from operationplanresource
                inner join operationplan on operationplan.reference = operationplanresource.operationplan_id
                order by operationplanresource.resource_id,
                operationplan.startdate,
                operationplanresource.quantity
                ) TO STDOUT WITH CSV HEADER"""
            % (settings.DATE_FORMAT_JS, settings.DATE_FORMAT_JS),
        },
        {
            "filename": "capacityreport.csv.gz",
            "folder": "export",
            "report": resource.OverviewReport,
            "data": {
                "format": "csvlist",
                "buckets": "week",
                "horizontype": True,
                "horizonunit": "month",
                "horizonlength": 6,
            },
        },
        {
            "filename": "inventoryreport.csv.gz",
            "folder": "export",
            "report": buffer.OverviewReport,
            "data": {
                "format": "csvlist",
                "buckets": "week",
                "horizontype": True,
                "horizonunit": "month",
                "horizonlength": 6,
            },
        },
    ]

    if "freppledb.forecast" in settings.INSTALLED_APPS:
        from freppledb.forecast.views import OverviewReport as ForecastOverviewReport

        statements.append(
            {
                "filename": "forecastreport.csv.gz",
                "folder": "export",
                "report": ForecastOverviewReport,
                "data": {
                    "format": "csvlist",
                    "buckets": "month",
                    "horizontype": True,
                    "horizonunit": "month",
                    "horizonlength": 6,
                },
            }
        )

    def get_version(self):
        return __version__

    def add_arguments(self, parser):
        parser.add_argument("--user", help="User running the command")
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Nominates a specific database to load the data into",
        )
        parser.add_argument(
            "--task",
            type=int,
            help="Task identifier (generated automatically if not provided)",
        )

    def handle(self, *args, **options):
        # Pick up the options
        now = datetime.now()
        self.database = options["database"]
        if self.database not in settings.DATABASES:
            raise CommandError("No database settings known for '%s'" % self.database)

        if options["user"]:
            try:
                self.user = (
                    User.objects.all()
                    .using(self.database)
                    .get(username=options["user"])
                )
            except Exception:
                raise CommandError("User '%s' not found" % options["user"])
        else:
            self.user = None

        timestamp = now.strftime("%Y%m%d%H%M%S")
        if self.database == DEFAULT_DB_ALIAS:
            logfile = "exporttofolder-%s.log" % timestamp
        else:
            logfile = "exporttofolder_%s-%s.log" % (self.database, timestamp)

        try:
            handler = logging.FileHandler(
                os.path.join(settings.FREPPLE_LOGDIR, logfile), encoding="utf-8"
            )
            # handler.setFormatter(logging.Formatter(settings.LOGGING['formatters']['simple']['format']))
            logger.addHandler(handler)
            logger.propagate = False
        except Exception as e:
            print("Failed to open logfile %s: %s" % (logfile, e))

        task = None
        errors = 0
        old_thread_locals = getattr(_thread_locals, "database", None)
        startofall = datetime.now()
        try:
            # Initialize the task
            setattr(_thread_locals, "database", self.database)
            if options["task"]:
                try:
                    task = (
                        Task.objects.all().using(self.database).get(pk=options["task"])
                    )
                except Exception:
                    raise CommandError("Task identifier not found")
                if (
                    task.started
                    or task.finished
                    or task.status != "Waiting"
                    or task.name not in ("frepple_exporttofolder", "exporttofolder")
                ):
                    raise CommandError("Invalid task identifier")
                task.status = "0%"
                task.started = now
                task.logfile = logfile
            else:
                task = Task(
                    name="exporttofolder",
                    submitted=now,
                    started=now,
                    status="0%",
                    user=self.user,
                    logfile=logfile,
                )
            task.arguments = " ".join(['"%s"' % i for i in args])
            task.processid = os.getpid()
            task.save(using=self.database)

            # Try to create the upload if doesn't exist yet
            if not os.path.isdir(settings.DATABASES[self.database]["FILEUPLOADFOLDER"]):
                try:
                    os.makedirs(settings.DATABASES[self.database]["FILEUPLOADFOLDER"])
                except Exception:
                    pass

            # Execute
            if os.path.isdir(settings.DATABASES[self.database]["FILEUPLOADFOLDER"]):
                if not os.path.isdir(
                    os.path.join(
                        settings.DATABASES[self.database]["FILEUPLOADFOLDER"], "export"
                    )
                ):
                    try:
                        os.makedirs(
                            os.path.join(
                                settings.DATABASES[self.database]["FILEUPLOADFOLDER"],
                                "export",
                            )
                        )
                    except OSError as exception:
                        if exception.errno != errno.EEXIST:
                            raise

                logger.info("Started export to folder")

                cursor = connections[self.database].cursor()

                task.status = "0%"
                task.save(using=self.database)

                i = 0
                cnt = len(self.statements)

                # Calling all the pre-sql statements
                idx = 1
                for stmt in self.pre_sql_statements:
                    try:
                        starting = datetime.now()
                        logger.info("Executing pre-statement %s" % idx)
                        cursor.execute(stmt)
                        if cursor.rowcount > 0:
                            logger.info(
                                "%s record(s) modified in %s"
                                % (cursor.rowcount, timesince(starting))
                            )
                    except Exception:
                        errors += 1
                        logger.error(
                            "An error occurred when executing statement %s" % idx
                        )
                    idx += 1

                for cfg in self.statements:
                    # Validate filename
                    filename = cfg.get("filename", None)
                    if not filename:
                        raise Exception("Missing filename in export configuration")
                    folder = cfg.get("folder", None)
                    if not folder:
                        raise Exception(
                            "Missing folder in export configuration for %s" % filename
                        )

                    # Report progress
                    starting = datetime.now()
                    logger.info("Started export of %s" % filename)
                    if task:
                        task.message = "Exporting %s" % filename
                        task.save(using=self.database)

                    # Make sure export folder exists
                    exportFolder = os.path.join(
                        settings.DATABASES[self.database]["FILEUPLOADFOLDER"], folder
                    )
                    if not os.path.isdir(exportFolder):
                        os.makedirs(exportFolder)

                    try:
                        reportclass = cfg.get("report", None)
                        sql = cfg.get("sql", None)
                        if reportclass:
                            # Export from report class

                            # Create a dummy request
                            factory = RequestFactory()
                            request = factory.get("/dummy/", cfg.get("data", {}))
                            if self.user:
                                request.user = self.user
                            else:
                                request.user = User.objects.all().get(username="admin")
                            request.database = self.database
                            request.LANGUAGE_CODE = settings.LANGUAGE_CODE
                            request.prefs = cfg.get("prefs", None)

                            # Initialize the report
                            if hasattr(reportclass, "initialize"):
                                reportclass.initialize(request)
                            if hasattr(reportclass, "rows"):
                                if callable(reportclass.rows):
                                    request.rows = reportclass.rows(request)
                                else:
                                    request.rows = reportclass.rows
                            if hasattr(reportclass, "crosses"):
                                if callable(reportclass.crosses):
                                    request.crosses = reportclass.crosses(request)
                                else:
                                    request.crosses = reportclass.crosses
                            if reportclass.hasTimeBuckets:
                                reportclass.getBuckets(request)

                            # Write the report file
                            if filename.lower().endswith(".gz"):
                                datafile = gzip.open(
                                    os.path.join(exportFolder, filename), "wb"
                                )
                            else:
                                datafile = open(
                                    os.path.join(exportFolder, filename), "wb"
                                )
                            if filename.lower().endswith(".xlsx"):
                                reportclass._generate_spreadsheet_data(
                                    request,
                                    [request.database],
                                    datafile,
                                    **cfg.get("data", {})
                                )
                            elif filename.lower().endswith(
                                ".csv"
                            ) or filename.lower().endswith(".csv.gz"):
                                for r in reportclass._generate_csv_data(
                                    request, [request.database], **cfg.get("data", {})
                                ):
                                    datafile.write(
                                        r.encode(settings.CSV_CHARSET)
                                        if isinstance(r, str)
                                        else r
                                    )
                            else:
                                raise Exception(
                                    "Unknown output format for %s" % filename
                                )
                        elif sql:
                            # Exporting using SQL
                            if filename.lower().endswith(".gz"):
                                datafile = gzip.open(
                                    os.path.join(exportFolder, filename), "wb"
                                )
                            else:
                                datafile = open(
                                    os.path.join(exportFolder, filename), "wb"
                                )
                            cursor.copy_expert(sql, datafile)
                        else:
                            raise Exception("Unknown export type for %s" % filename)
                        datafile.close()
                        i += 1

                    except Exception as e:
                        errors += 1
                        logger.error("Failed to export %s: %s" % (filename, e))
                        if task:
                            task.message = "Failed to export %s" % filename

                    logger.info(
                        "Finished export of %s in %s" % (filename, timesince(starting))
                    )
                    task.status = str(int(i / cnt * 100)) + "%"
                    task.save(using=self.database)

                logger.info("Exported %s files" % (cnt - errors))

                idx = 1
                for stmt in self.post_sql_statements:
                    try:
                        starting = datetime.now()
                        logger.info("Executing post-statement %s" % idx)
                        cursor.execute(stmt)
                        if cursor.rowcount > 0:
                            logger.info(
                                "%s record(s) modified in %s"
                                % (cursor.rowcount, timesince(starting))
                            )
                    except Exception:
                        errors += 1
                        logger.error(
                            "An error occured when executing statement %s" % idx
                        )
                    idx += 1

            else:
                errors += 1
                logger.error("Failed, folder does not exist")
                task.message = "Destination folder does not exist"
                task.save(using=self.database)

        except Exception as e:
            logger.error("Failed to export: %s" % e)
            errors += 1
            if task:
                task.message = "Failed to export"

        finally:
            logger.info("End of export to folder in %s\n" % timesince(startofall))
            if task:
                if not errors:
                    task.status = "100%"
                    task.message = "Exported %s data files" % (cnt)
                else:
                    task.status = "Failed"
                    #  task.message = "Exported %s data files, %s failed" % (cnt-errors, errors)
                task.finished = datetime.now()
                task.processid = None
                task.save(using=self.database)
            setattr(_thread_locals, "database", old_thread_locals)

    # accordion template
    title = _("Export plan result")
    index = 1200
    help_url = "command-reference.html#exporttofolder"

    @staticmethod
    def getHTML(request):
        if (
            "FILEUPLOADFOLDER" not in settings.DATABASES[request.database]
            or not request.user.is_superuser
        ):
            return None

        # Function to convert from bytes to human readable format
        def sizeof_fmt(num):
            for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
                if abs(num) < 1024.0:
                    return "%3.0f %sB" % (num, unit)
                num /= 1024.0
            return "%.0f %sB" % (num, "Yi")

        # List available data files
        filesexported = []
        if "FILEUPLOADFOLDER" in settings.DATABASES[request.database]:
            exportfolder = os.path.join(
                settings.DATABASES[request.database]["FILEUPLOADFOLDER"], "export"
            )
            if os.path.isdir(exportfolder):
                tzoffset = GridReport.getTimezoneOffset(request)
                for file in os.listdir(exportfolder):
                    if file.endswith(
                        (".xlsx", ".xlsm", ".xlsx.gz", ".csv", ".csv.gz", ".log")
                    ):
                        filesexported.append(
                            [
                                file[:-3] if file.endswith(".csv.gz") else file,
                                strftime(
                                    "%Y-%m-%d %H:%M:%S",
                                    localtime(
                                        os.stat(
                                            os.path.join(exportfolder, file)
                                        ).st_mtime
                                        + tzoffset.total_seconds()
                                    ),
                                ),
                                sizeof_fmt(
                                    os.stat(os.path.join(exportfolder, file)).st_size
                                ),
                            ]
                        )

        return render_to_string(
            "commands/exporttofolder.html",
            {"filesexported": filesexported},
            request=request,
        )
