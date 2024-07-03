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
from freppledb.input.models import  * # Required for the pantheon ERP connection 03.07.2024
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
 
        outfilename = os.path.join(self.destination, "location.%s" % self.ext)
        print("Start extracting locations to %s" % outfilename)
        self.cursor.execute(
            """

            select * from uTN_V_Frepple_LocationData
                    
            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:
            name, description, lastmodified = row
            
            lookup_fields = {'name': name}

            data = {
                'name': name,
                'description': description,
                'lastmodified': lastmodified or now()
            }
            
            item, created = update_or_create_record(Location, lookup_fields, data)
            
            if created:
                print(f"Created new location: {name}")
            else:
                print(f"Updated existing location: {name}")
        
        print("Finished extracting items.")

    def extractCustomer(self):

        outfilename = os.path.join(self.destination, "customer.%s" % self.ext)
        print("Start extracting customers to %s" % outfilename)
        self.cursor.execute(
            """


            select * from uTN_V_Frepple_CustomerData


            """
        )

        rows = self.cursor.fetchall()
        
        for row in rows:
            name, category,lastmodified = row
            
            lookup_fields = {'name': name}
            data = {
                'name': name,
                'category': category,
                'lastmodified': lastmodified or now()
            }
            
            item, created = update_or_create_record(Customer, lookup_fields, data)
            
            if created:
                print(f"Created new customer: {name}")
            else:
                print(f"Updated existing customer: {name}")
        
        print("Finished extracting items.")

    def extractItem(self):

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

        outfilename = os.path.join(self.destination, "supplier.%s" % self.ext)
        print("Start extracting suppliers to %s" % outfilename)
        self.cursor.execute(
            """


            select * from uTN_V_Frepple_SupplierData 


            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:
            name, description, lastmodified = row
            
            lookup_fields = {'name': name}
            data = {
                'subcategory': name,
                'description': description,
                'lastmodified': lastmodified or now()
            }
            
            item, created = update_or_create_record(Supplier, lookup_fields, data)
            
            if created:
                print(f"Created new supplier: {name}")
            else:
                print(f"Updated existing supplier: {name}")
        
        print("Finished extracting items.")

    def extractResource(self):

        outfilename = os.path.join(self.destination, "resource.%s" % self.ext)
        print("Start extracting resources to %s" % outfilename)
        self.cursor.execute(
            """


            select * from uTN_V_Frepple_ResourcesData 


            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:
            name, category, subcategory, maximum, location, type, lastmodified = row
            
            lookup_fields = {'name': name}
            data = {
                'name': name,
                'category': category,
                'subcategory': subcategory,
                'maximum': maximum,
                'location': location,
                'type': type,
                'lastmodified': lastmodified or now()
            }
            
            item, created = update_or_create_record(Resource, lookup_fields, data)
            
            if created:
                print(f"Created new resource: {name}")
            else:
                print(f"Updated existing resource: {name}")
        
        print("Finished extracting items.")

    def extractSalesOrder(self):

        outfilename = os.path.join(self.destination, "demand.%s" % self.ext)
        print("Start extracting demand to %s" % outfilename)
        self.cursor.execute(
            """


            select * from uTN_V_Frepple_SalesOrderData 


            
            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:
            name, item, location, customer, status, due, quantity, minshipment, description, category, priority, lastmodified = row
            
            lookup_fields = {'name': name}
            data = {
                'name': name,
                'item': item,
                'location': location,
                'customer': customer,
                'status': status,
                'due': due,
                'quantity': quantity,
                'minshipment': minshipment,
                'description': description,
                'category': category,
                'priority': priority,
                'lastmodified': lastmodified or now()
            }
            
            item, created = update_or_create_record(Demand, lookup_fields, data)
            
            if created:
                print(f"Created new sales order: {name}")
            else:
                print(f"Updated existing sales order: {name}")
        
        print("Finished extracting items.")
    def extractOperation(self):

        outfilename = os.path.join(self.destination, "operation.%s" % self.ext)
        print("Start extracting operations to %s" % outfilename)
        self.cursor.execute(
            """
               select * from uTN_V_Frepple_OperationData 
            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:

            name, description, category, subcategory, type, item, location, duration, duration_per, lastmodified = row
            
            lookup_fields = {'name': name}

            data = {
                'name': name,
                'description': description,
                'category': category,
                'subcategory': subcategory,
                'type': type,
                'item': item,
                'location': location,
                'duration': duration,
                'duration_per': duration_per,
                'lastmodified': lastmodified or now()
            }
            
            item, created = update_or_create_record(Operation, lookup_fields, data)
            
            if created:
                print(f"Created new operation: {name}")
            else:
                print(f"Updated existing operation: {name}")
        
        print("Finished extracting items.")

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
            outcsv.writerows(self.cursor.fetchall()) Not needed currently '''

    def extractOperationResource(self):
        outfilename = os.path.join(self.destination, "operationresource.%s" % self.ext)
        print("Start extracting operationresource to %s" % outfilename)
        self.cursor.execute(
            """
                select * from uTN_V_Frepple_OperationResourcesData
            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:
            name, resource, quantity, lastmodified = row
            
            lookup_fields = {}
            data = {
                'name': name,
                'resource': resource,
                'quantity': quantity,
                'lastmodified': lastmodified or now()
            }
            
            item, created = update_or_create_record(OperationResource, lookup_fields, data)
            
            if created:
                print(f"Created new operation resource: {name}")
            else:
                print(f"Updated existing operation resource: {name}")
        
        print("Finished extracting items.")


    def extractOperationMaterial(self):

        outfilename = os.path.join(self.destination, "operationmaterial.%s" % self.ext)
        print("Start extracting operationmaterial to %s" % outfilename)
        self.cursor.execute(
            """
                select * from uTN_V_Frepple_OperationMaterialData 
            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:
            operation, item, type, quantity, lastmodified = row
            
            lookup_fields = {}
            data = {
                'operation': operation,
                'item': item,
                'type': type,
                'type': quantity,
                'lastmodified': lastmodified or now()
            }
            
            item, created = update_or_create_record(OperationMaterial, lookup_fields, data)
            
            if created:
                print(f"Created new operation material: {operation}")
            else:
                print(f"Updated existing operation material: {operation}")
        
        print("Finished extracting items.")



    def extractBuffer(self):

        outfilename = os.path.join(self.destination, "buffer.%s" % self.ext)
        print("Start extracting buffer to %s" % outfilename)
        self.cursor.execute(
            """
            
            select * from uTN_V_Frepple_BufferData

            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:
            item, location, batch, category, onhand, lastmodified = row
            
            lookup_fields = {'item': item, 'location': location, 'batch': batch }
            data = {
                'item': item,
                'location': location,
                'batch': batch,
                'category': category,
                'onhand': onhand,
                'lastmodified': lastmodified or now()
            }
            
            item, created = update_or_create_record(Buffer, lookup_fields, data)
            
            if created:
                print(f"Created new buffer: {item}")
            else:
                print(f"Updated existing buffer: {item}")
        
        print("Finished extracting items.")



    def extractCalendar(self):

        outfilename = os.path.join(self.destination, "calendar.%s" % self.ext)
        print("Start extracting calendar to %s" % outfilename)
        self.cursor.execute(
            """
      select * from uTN_V_Frepple_CalendarData
            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:
            name, default = row
            
            lookup_fields = {'name': name}
            data = {
                'name': name,
                'default': default,

            }
            
            item, created = update_or_create_record(Calendar, lookup_fields, data)
            
            if created:
                print(f"Created new calendar: {name}")
            else:
                print(f"Updated existing calendar: {name}")
        
        print("Finished extracting items.")

    def extractCalendarBucket(self):

        outfilename = os.path.join(self.destination, "calendar.%s" % self.ext)
        print("Start extracting calendar to %s" % outfilename)
        self.cursor.execute(
            """
        select * from uTN_V_Frepple_CalendarBucketsData
            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:
            calendar_id, value, startdate, enddate, priority, days, starttime, endtime, lastmodified = row
            
            lookup_fields = {}
            data = {
                'calendar_id': calendar_id,
                'value': value,
                'startdate': startdate,
                'enddate': enddate,
                'priority': priority,
                'days': days,
                'starttime': starttime,
                'endtime': endtime,
                'lastmodified': lastmodified or now()
            }
            
            item, created = update_or_create_record(CalendarBucket, lookup_fields, data)
            
            if created:
                print(f"Created new calendar bucket: {calendar_id}")
            else:
                print(f"Updated existing calendar bucket: {calendar_id}")
        
        print("Finished extracting items.")