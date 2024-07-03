#
# Copyright (C) 2017 by frePPLe bv
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

import csv
from datetime import datetime
import os
from freppledb.input.models import Item
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.template import Template, RequestContext
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import now

from freppledb import __version__
from freppledb.common.models import User
from freppledb.execute.models import Task

from ...utils import getERPconnection
from ...utils import update_or_create_record  # Import the utility function 03.07.2024 Janko Jovičić


class Command(BaseCommand):
    help = """
      Extract a set of flat files from an ERP system.
      """

    # Generate .csv or .cpy files:
    #  - csv files are thoroughly validated and load slower
    #  - cpy files load much faster and rely on database level validation
    #    Loading cpy files is only available in the Enterprise Edition
    ext = "csv"
    # ext = 'cpy'

    # For the display in the execution screen
    title = _("Import data from %(erp)s") % {"erp": "Pantheon"}

    # For the display in the execution screen
    index = 2

    requires_system_checks = []

    def get_version(self):
        return __version__

    def add_arguments(self, parser):
        parser.add_argument("--user", help="User running the command")
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Nominates the frePPLe database to load",
        )
        parser.add_argument(
            "--task",
            type=int,
            help="Task identifier (generated automatically if not provided)",
        )

    @staticmethod
    def getHTML(request):
        if "freppledb.pantheonconnector" in settings.INSTALLED_APPS:
            context = RequestContext(request)

            template = Template(
                """
        {% load i18n %}
        <form role="form" method="post" action="{{request.prefix}}/execute/launch/erp2frepple/">{% csrf_token %}
        <table>
          <tr>
            <td style="vertical-align:top; padding: 15px">

               <button  class="btn btn-primary"  type="submit" value="{% trans "launch"|capfirst %}">{% trans "launch"|capfirst %}</button>
            </td>
            <td  style="padding: 0px 15px;">{% trans "Import Pantheon data into frePPLe." %}
            </td>
          </tr>
        </table>
        </form>
          
        

      """
            )
            return template.render(context)
        else:
            return None

    def handle(self, **options):
        # Select the correct frePPLe scenario database
        self.database = options["database"]
        if self.database not in settings.DATABASES.keys():
            raise CommandError("No database settings known for '%s'" % self.database)

        # FrePPle user running this task
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

        # FrePPLe task identifier
        if options["task"]:
            try:
                self.task = (
                    Task.objects.all().using(self.database).get(pk=options["task"])
                )
            except Exception:
                raise CommandError("Task identifier not found")
            if (
                self.task.started
                or self.task.finished
                or self.task.status != "Waiting"
                or self.task.name != "erp2frepple"
            ):
                raise CommandError("Invalid task identifier")
        else:
            now = datetime.now()
            self.task = Task(
                name="erp2frepple",
                submitted=now,
                started=now,
                status="0%",
                user=self.user,
            )
        self.task.processid = os.getpid()
        self.task.save(using=self.database)

        # Set the destination folder
        self.destination = settings.DATABASES[self.database]["FILEUPLOADFOLDER"]
        if not os.access(self.destination, os.W_OK):
            raise CommandError("Can't write to folder %s " % self.destination)

        # Open database connection
        print("Connecting to the database")
        with getERPconnection(self.database) as erp_connection:
            self.cursor = erp_connection.cursor()
            self.fk = "_id" if self.ext == "cpy" else ""

            # Extract all files
            try:
                '''self.extractLocation()
                self.task.status = "6%"
                self.task.save(using=self.database)

                self.extractCustomer()
                self.task.status = "12%"
                self.task.save(using=self.database)'''

                self.extractItem()
                self.task.status = "18%"
                self.task.save(using=self.database)

                '''self.extractSupplier()
                self.task.status = "24%"
                self.task.save(using=self.database)

                self.extractResource()
                self.task.status = "30%"
                self.task.save(using=self.database)

                self.extractSalesOrder()
                self.task.status = "36%"
                self.task.save(using=self.database)

                self.extractOperation()
                self.task.status = "42%"
                self.task.save(using=self.database)

                # Note: the suboperation table is now deprecated.
                # The same data can now be directly loaded in the the operation table.
                self.extractSuboperation()
                self.task.status = "48%"
                self.task.save(using=self.database)

                self.extractOperationResource()
                self.task.status = "54%"
                self.task.save(using=self.database)

                self.extractOperationMaterial()
                self.task.status = "60%"
                self.task.save(using=self.database)

                self.extractCalendar()
                self.task.status = "72%"
                self.task.save(using=self.database)

                self.extractCalendarBucket()
                self.task.status = "78%"
                self.task.save(using=self.database)

                self.extractBuffer()
                self.task.status = "84%"
                self.task.save(using=self.database)


                self.extractCalendar()
                self.task.status = "96%"
                self.task.save(using=self.database)

                self.extractCalendarBucket()
                self.task.status = "100%"
                self.task.save(using=self.database) '''

                self.task.status = "Done"

            except Exception as e:
                self.task.status = "Failed"
                self.task.message = "Failed: %s" % e

            finally:
                self.task.processid = None
                self.task.finished = datetime.now()
                self.task.save(using=self.database)

    def extractLocation(self):
        """
        Straightforward mapping JobBOSS locations to frePPLe locations.
        Only the SHOP location is actually used in the frePPLe model.
        """
        outfilename = os.path.join(self.destination, "location.%s" % self.ext)
        print("Start extracting locations to %s" % outfilename)
        self.cursor.execute(
            """

            select * from uTN_V_Frepple_LocationData
                    
            """
        )
        with open(outfilename, "w", newline="") as outfile:
            outcsv = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            outcsv.writerow(["name", "description", "lastmodified"])       
            outcsv.writerows(self.cursor.fetchall())

    def extractCustomer(self):
        """
        Straightforward mapping JobBOSS customers to frePPLe customers.
        """
        outfilename = os.path.join(self.destination, "customer.%s" % self.ext)
        print("Start extracting customers to %s" % outfilename)
        self.cursor.execute(
            """


            select * from uTN_V_Frepple_CustomerData



            """
        )
        with open(outfilename, "w", newline="") as outfile:
            outcsv = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            outcsv.writerow(["name", "category", "lastmodified"])
            outcsv.writerows(self.cursor.fetchall())

    def extractItem(self):
        """
        Map active JobBOSS jobs into frePPLe items.
        """
        outfilename = os.path.join(self.destination, "item.%s" % self.ext)
        print("Start extracting items to %s" % outfilename)
        
        self.cursor.execute(
            """
            SELECT *
            FROM uTN_V_Frepple_ItemData
            """
        )
        
        rows = self.cursor.fetchall()
        
        for row in rows:
            name, subcategory, description, category, lastmodified = row
            
            lookup_fields = {'name': name}
            data = {
                'subcategory': subcategory,
                'description': description,
                'category': category,
                'lastmodified': lastmodified or now()
            }
            
            item, created = update_or_create_record(Item, lookup_fields, data)
            
            if created:
                print(f"Created new item: {name}")
            else:
                print(f"Updated existing item: {name}")
        
        print("Finished extracting items.")

    def extractSupplier(self):
        """
        Map active JobBOSS vendors into frePPLe suppliers.
        """
        outfilename = os.path.join(self.destination, "supplier.%s" % self.ext)
        print("Start extracting suppliers to %s" % outfilename)
        self.cursor.execute(
            """


            select * from uTN_V_Frepple_SupplierData 


            """
        )
        with open(outfilename, "w", newline="") as outfile:
            outcsv = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            outcsv.writerow(["name", "description", "lastmodified"])
            outcsv.writerows(self.cursor.fetchall())

    def extractResource(self):
        """
        Map JobBOSS work centers into frePPLe resources.
        Only take the top-level workcenters, and skip the inactive ones.
        """
        outfilename = os.path.join(self.destination, "resource.%s" % self.ext)
        print("Start extracting resources to %s" % outfilename)
        self.cursor.execute(
            """


            select * from uTN_V_Frepple_ResourcesData 


            """
        )
        with open(outfilename, "w", newline="") as outfile:
            outcsv = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            outcsv.writerow(
                [
                    "name",
                    "category",
                    "subcategory",
                    "maximum",
                    "location%s" % self.fk,
                    "type",
                    "lastmodified",
                ]
            )
            outcsv.writerows(self.cursor.fetchall())

    def extractSalesOrder(self):
        """
        Map JobBOSS top level jobs into frePPLe sales orders.
        """
        outfilename = os.path.join(self.destination, "demand.%s" % self.ext)
        print("Start extracting demand to %s" % outfilename)
        self.cursor.execute(
            """


            select * from uTN_V_Frepple_SalesOrderData 


            
            """
        )
        with open(outfilename, "w", newline="") as outfile:
            outcsv = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            outcsv.writerow(
                [
                    "name",
                    "item%s" % self.fk,
                    "location%s" % self.fk,
                    "customer%s" % self.fk,
                    "status",
                    "due",
                    "quantity",
                    "minimum shipment" if self.ext == "csv" else "minshipment",
                    "description",
                    "category",
                    "priority",
                    "lastmodified",
                ]
            )
            outcsv.writerows(self.cursor.fetchall())

    def extractOperation(self):
        """
        Map JobBOSS jobs into frePPLe operations.
        We extract a routing operation and also suboperations.
        SQL contains an ugly trick to avoid duplicate job-sequence combinations.
        """
        outfilename = os.path.join(self.destination, "operation.%s" % self.ext)
        print("Start extracting operations to %s" % outfilename)
        self.cursor.execute(
            """
               select * from uTN_V_Frepple_OperationData 
            """
        )
        with open(outfilename, "w", newline="") as outfile:
            outcsv = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            outcsv.writerow(
                [
                    "name",
                    "description",
                    "category",
                    "subcategory",
                    "type",
                    "item%s" % self.fk,
                    "location%s" % self.fk,
                    "duration",
                    "duration_per",
                    "lastmodified",
                ]
            )
            outcsv.writerows(self.cursor.fetchall())

    '''def extractSuboperation(self):
        """
        Map JobBOSS joboperations into frePPLe suboperations.
        """
        outfilename = os.path.join(self.destination, "suboperation.%s" % self.ext)
        print("Start extracting suboperations to %s" % outfilename)
        self.cursor.execute(
            """
     
            """
        )
        with open(outfilename, "w", newline="") as outfile:
            outcsv = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            outcsv.writerow(
                [
                    "operation%s" % self.fk,
                    "suboperation%s" % self.fk,
                    "priority",
                    "lastmodified",
                ]
            )
            outcsv.writerows(self.cursor.fetchall())'''

    def extractOperationResource(self):
        """
        Map JobBOSS joboperation workcenters into frePPLe operation-resources.
        """
        outfilename = os.path.join(self.destination, "operationresource.%s" % self.ext)
        print("Start extracting operationresource to %s" % outfilename)
        self.cursor.execute(
            """
                select * from uTN_V_Frepple_OperationResourcesData
            """
        )
        with open(outfilename, "w", newline="") as outfile:
            outcsv = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            outcsv.writerow(
                [
                    "operation%s" % self.fk,
                    "resource%s" % self.fk,
                    "quantity",
                    "lastmodified",
                ]
            )
            outcsv.writerows(self.cursor.fetchall())

    def extractOperationMaterial(self):
        """
        Map JobBOSS joboperation workcenters into frePPLe operation-materials.
        """
        outfilename = os.path.join(self.destination, "operationmaterial.%s" % self.ext)
        print("Start extracting operationmaterial to %s" % outfilename)
        self.cursor.execute(
            """
                select * from uTN_V_Frepple_OperationMaterialData 
            """
        )
        with open(outfilename, "w", newline="") as outfile:
            outcsv = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            outcsv.writerow(
                [
                    "operation%s" % self.fk,
                    "item%s" % self.fk,
                    "type",
                    "quantity",
                    "lastmodified",
                ]
            )
            outcsv.writerows(self.cursor.fetchall())

    def extractBuffer(self):
        """
        Map JobBOSS operation completed into frePPLe buffer onhand.
        """
        outfilename = os.path.join(self.destination, "buffer.%s" % self.ext)
        print("Start extracting buffer to %s" % outfilename)
        self.cursor.execute(
            """
            
            select * from uTN_V_Frepple_BufferData

            """
        )
        with open(outfilename, "w", newline="") as outfile:
            outcsv = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            outcsv.writerow(
                [
                    "name",
                    "item%s" % self.fk,
                    "location%s" % self.fk,
                    "onhand",
                    "lastmodified",
                ]
            )
            outcsv.writerows(self.cursor.fetchall())



    def extractCalendar(self):
        """
        Extract working hours calendars from the ERP system.
        """
        outfilename = os.path.join(self.destination, "calendar.%s" % self.ext)
        print("Start extracting calendar to %s" % outfilename)
        self.cursor.execute(
            """
      select * from uTN_V_Frepple_CalendarData
            """
        )
        with open(outfilename, "w", newline="") as outfile:
            outcsv = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            outcsv.writerow(["name", "lastmodified"])
            outcsv.writerows(self.cursor.fetchall())

    def extractCalendarBucket(self):
        """
        Extract working hours calendars from the ERP system.
        """
        outfilename = os.path.join(self.destination, "calendar.%s" % self.ext)
        print("Start extracting calendar to %s" % outfilename)
        self.cursor.execute(
            """
        select * from uTN_V_Frepple_CalendarBucketsData
            """
        )
        with open(outfilename, "w", newline="") as outfile:
            outcsv = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            outcsv.writerow(
                [
                    "value",
                    "start%s" % self.fk,
                    "end%s" % self.fk,
                    "priority%s" % self.fk,
                    "days",
                    "starttime",
                    "endtime",
                ]

            )
