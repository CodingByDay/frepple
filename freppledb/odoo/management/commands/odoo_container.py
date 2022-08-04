#
# Copyright (C) 2022 by frePPLe bv
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation; either version 3 of the License, or
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os.path
import psycopg2
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import DEFAULT_DB_ALIAS

from freppledb import __version__


class Command(BaseCommand):

    help = "Utility command for development to spin up an odoo docker container"

    requires_system_checks = []

    def get_version(self):
        return __version__

    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            dest="full",
            default=False,
            help="Complete rebuild of image and database",
        )
        parser.add_argument(
            "--nolog",
            action="store_true",
            dest="nolog",
            default=False,
            help="Tail the odoo log at the end of this command",
        )
        parser.add_argument(
            "--container-port",
            type=int,
            default=8069,
            help="Port number for odoo. Defaults to 8069",
        )
        parser.add_argument(
            "--frepple-url",
            default="http://localhost:8000",
            help="URL where frepple is available. Defaults to 'http://localhost:8000'",
        )
        parser.add_argument(
            "--odoo-db-host",
            default=settings.DATABASES[DEFAULT_DB_ALIAS]["HOST"],
            help="Database host to use for odoo. Defaults to the same as used by frepple.",
        )
        parser.add_argument(
            "--odoo-db-port",
            default=settings.DATABASES[DEFAULT_DB_ALIAS]["PORT"],
            help="Database port to use for odoo. Defaults to the same as used by frepple.",
        )
        parser.add_argument(
            "--odoo-db-user",
            default=settings.DATABASES[DEFAULT_DB_ALIAS]["USER"],
            help="Database user to use for odoo. Defaults to the same as used by frepple.",
        )
        parser.add_argument(
            "--odoo-db-password",
            default=settings.DATABASES[DEFAULT_DB_ALIAS]["PASSWORD"],
            help="Database password to use for odoo. Defaults to the same as used by frepple.",
        )

    def getOdooVersion(self, dockerfile):
        with open(dockerfile, mode="rt") as f:
            for l in f.read().splitlines():
                if l.startswith("FROM "):
                    return l.split(":", 1)[-1]
            raise CommandError("Can't find odoo version in dockerfile")

    def handle(self, **options):
        dockerfile = os.path.join(
            os.path.dirname(__file__), "..", "..", "odoo_addon", "dockerfile"
        )
        if not os.path.exists(dockerfile):
            raise CommandError("Can't find dockerfile")
        odooversion = self.getOdooVersion(dockerfile)

        # Used as a) docker image name, b) docker container name,
        # c) docker volume name and d) odoo database name.
        name = "odoo_frepple_%s" % odooversion

        if options["full"]:
            print("PULLING ODOO BASE IMAGE")
            subprocess.run(["docker", "pull", "odoo:%s" % odooversion])

        print("BUILDING DOCKER IMAGE")
        subprocess.run(
            [
                "docker",
                "build",
                "-f",
                dockerfile,
                "-t",
                name,
                ".",
            ],
            cwd=os.path.join(os.path.dirname(__file__), "..", "..", "odoo_addon"),
        )

        print("DELETE OLD CONTAINER")
        subprocess.run(["docker", "rm", "--force", name])
        if options["full"]:
            subprocess.run(["docker", "volume", "rm", "--force", name])

        if options["full"]:
            print("CREATE NEW DATABASE")
            os.environ["PGPASSWORD"] = options["odoo_db_password"]
            extraargs = []
            if options["odoo_db_host"]:
                extraargs = extraargs + [
                    "-h",
                    options["odoo_db_host"],
                ]
            if options["odoo_db_port"]:
                extraargs = extraargs + [
                    "-p",
                    options["odoo_db_port"],
                ]
            subprocess.run(
                [
                    "dropdb",
                    "-U",
                    options["odoo_db_user"],
                    "--force",
                    "--if-exists",
                    name,
                ]
                + extraargs
            )
            subprocess.run(
                [
                    "createdb",
                    "-U",
                    options["odoo_db_user"],
                    name,
                ]
                + extraargs
            )

            print("INITIALIZE ODOO DATABASE")
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-it",
                    "-v",
                    "%s:/var/lib/odoo" % name,
                    "-e",
                    "HOST=%s"
                    % (
                        "host.docker.internal"
                        if not options["odoo_db_host"]
                        else options["odoo_db_host"]
                    ),
                    "-e",
                    "USER=%s" % options["odoo_db_user"],
                    "-e",
                    "PASSWORD=%s" % options["odoo_db_password"],
                    "--name",
                    name,
                    "-t",
                    name,
                    "odoo",
                    "--init=base,product,purchase,sale,sale_management,resource,stock,mrp,frepple,freppledata,autologin",
                    "--load=web,autologin",
                    "--database=%s" % name,
                    "--stop-after-init",
                ]
            )

            print("CONFIGURE ODOO DATABASE")
            conn_params = {
                "database": name,
                "user": options["odoo_db_user"],
                "password": options["odoo_db_password"],
            }
            if options["odoo_db_host"]:
                conn_params["host"] = options["odoo_db_host"]
            if options["odoo_db_port"]:
                conn_params["port"] = options["odoo_db_port"]
            with psycopg2.connect(**conn_params) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        update res_company set
                          manufacturing_warehouse = (
                             select id
                             from stock_warehouse
                             where name = 'San Francisco'
                             ),
                          webtoken_key = '%s',
                          frepple_server = '%s',
                          disclose_stack_trace = true
                        where name in ('My Company (San Francisco)', 'YourCompany')
                        """
                        % (settings.SECRET_KEY, options["frepple_url"])
                    )
                    cursor.execute(
                        """
                        update res_company set
                          manufacturing_warehouse = (
                             select id
                             from stock_warehouse
                             where name = 'Chicago 1'
                             ),
                          webtoken_key = '%s',
                          frepple_server = '%s',
                          disclose_stack_trace = true
                        where name = 'My Company (Chicago)'
                        """
                        % (settings.SECRET_KEY, options["frepple_url"])
                    )

        print("CREATING DOCKER CONTAINER")
        container = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "-p",
                "8069:%s" % (options["container_port"],),
                "-p",
                "8071:%s" % (options["container_port"] + 2,),
                "-p",
                "8072:%s" % (options["container_port"] + 3,),
                "-v",
                "%s:/var/lib/odoo" % name,
                "-e",
                "HOST=%s"
                % (
                    "host.docker.internal"
                    if not options["odoo_db_host"]
                    else options["odoo_db_host"]
                ),
                "-e",
                "USER=%s" % options["odoo_db_user"],
                "-e",
                "PASSWORD=%s" % options["odoo_db_password"],
                "--name",
                name,
                "-t",
                name,
                "odoo",
                "--database=%s" % name,
            ],
            capture_output=True,
            text=True,
        ).stdout

        print("CONTAINER READY: %s " % container)
        if not options["nolog"]:
            print("Hit CTRL-C to stop displaying the container log")
            subprocess.run(["docker", "attach", container], shell=True)
