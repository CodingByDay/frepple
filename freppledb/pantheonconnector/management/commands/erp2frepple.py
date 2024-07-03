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
                self.extractLocation()
                self.task.status = "?%"
                self.task.save(using=self.database)

                self.extractCustomer()
                self.task.status = "?%"
                self.task.save(using=self.database)

                self.extractItem()
                self.task.status = "?%"
                self.task.save(using=self.database)

                self.extractCalendar()
                self.task.status = "?%"
                self.task.save(using=self.database)

                self.extractCalendarBucket()
                self.task.status = "?%"
                self.task.save(using=self.database)


                self.extractSupplier()
                self.task.status = "?%"
                self.task.save(using=self.database)

                self.task.status = "?%"
                self.task.save(using=self.database)
                self.extractItemSupplier()


                self.task.status = "?%"
                self.task.save(using=self.database)

                self.extractSalesOrder()
                self.task.status = "?%"
                self.task.save(using=self.database)

                self.extractOperation()
                self.task.status = "?%"
                self.task.save(using=self.database)

                '''self.extractSuboperation()
                self.task.status = "?%"
                self.task.save(using=self.database)'''

                self.extractOperationResource()
                self.task.status = "?%"
                self.task.save(using=self.database)

                self.extractOperationMaterial()
                self.task.status = "60%"
                self.task.save(using=self.database)

        
                self.extractBuffer()
                self.task.status = "?%"
                self.task.save(using=self.database)



                self.task.status = "Done"

            except Exception as e:
                self.task.status = "Failed"
                self.task.message = "Failed: %s" % e

            finally:
                self.task.processid = None
                self.task.finished = datetime.now()
                self.task.save(using=self.database)

    def extractLocation(self):
 
        self.cursor.execute(
            """

            select * from uTN_V_Frepple_LocationData
                    
            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:
           
            name = row[0]
            description = row[1]
            lastmodified = row[2]

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

        self.cursor.execute(
            """

            select * from uTN_V_Frepple_CustomerData


            """
        )

        rows = self.cursor.fetchall()
        
        for row in rows:
            
            name = row[0]
            category = row[1]
            lastmodified = row[2]

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
 
        self.cursor.execute(
            """
            SELECT *
            FROM uTN_V_Frepple_ItemData
            """
        )
        
        rows = self.cursor.fetchall()
        
        for row in rows:

            name = row[0]
            subcategory = row[1]
            description = row[2]
            category = row[3]
            lastmodified = row[4]
            
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

        self.cursor.execute(
            """

            select * from uTN_V_Frepple_SupplierData 


            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:

            name = row[0]
            description = row[1]
            lastmodified = row[2]

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


        self.cursor.execute(
            """

            select * from uTN_V_Frepple_ResourcesData 

            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:

            name = row[0]
            category = row[1]
            subcategory = row[2]
            maximum = row[3]
            location = row[4]
            type_val = row[5]
            lastmodified = row[6]
            available = row[7]
            
            lookup_fields = {'name': name }

            # Fetch the Calendar object for the 'available' field
            try:
                available_calendar = Calendar.objects.get(name=available)
            except Calendar.DoesNotExist:
                print(f"Calendar '{available}' does not exist.")
                available_calendar = None

            # Fetch the Location object
            try:
                location_obj = Location.objects.get(name=location)
            except Location.DoesNotExist:
                print(f"Location '{location}' does not exist.")
                location_obj = None
            

            data = {
                'name': name,
                'category': category,
                'subcategory': subcategory,
                'maximum': maximum,
                'location': location_obj,
                'type': type_val,
                'lastmodified': lastmodified or now(),
                'available': available_calendar
            }
            
            item, created = update_or_create_record(Resource, lookup_fields, data)
            
            if created:
                print(f"Created new resource: {name}")
            else:
                print(f"Updated existing resource: {name}")
        
        print("Finished extracting items.")

    def extractSalesOrder(self):

        self.cursor.execute(
            """


            select * from uTN_V_Frepple_SalesOrderData 


            
            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:

            name = row[0]
            item = row[1]
            location = row[2]
            customer = row[3]
            status = row[4]
            due = row[5]
            quantity = row[6]
            minshipment = row[7]
            description = row[8]
            category = row[9]
            priority = row[10]
            lastmodified = row[11]

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

        self.cursor.execute(
            """
               select * from uTN_V_Frepple_OperationData 
            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:

            name = row[0]
            description = row[1]
            category = row[2]
            subcategory = row[3]
            type_val = row[4]
            item = row[5]
            location = row[6]
            duration = row[7]
            duration_per = row[8]
            lastmodified = row[9]
            lookup_fields = {'name': name}

            data = {
                'name': name,
                'description': description,
                'category': category,
                'subcategory': subcategory,
                'type': type_val,
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

        ''' def extractSuboperation(self):
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

        self.cursor.execute(
            """
                select * from uTN_V_Frepple_OperationResourcesData
            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:

            name = row[0]
            resource = row[1]
            quantity = row[2]
            lastmodified = row[3]
            
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


        self.cursor.execute(
            """
                select * from uTN_V_Frepple_OperationMaterialData 
            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:

            operation = row[0]
            item = row[1]
            type_val = row[2]
            quantity = row[3]
            lastmodified = row[4]
            
            lookup_fields = {}
            data = {
                'operation': operation,
                'item': item,
                'type': type_val,
                'quantity': quantity,
                'lastmodified': lastmodified or now()
            }
            
            item, created = update_or_create_record(OperationMaterial, lookup_fields, data)
            
            if created:
                print(f"Created new operation material: {operation}")
            else:
                print(f"Updated existing operation material: {operation}")
        
        print("Finished extracting items.")



    def extractBuffer(self):


        self.cursor.execute(
            """
            
            select * from uTN_V_Frepple_BufferData

            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:

            item = row[0]
            location = row[1]
            batch = row[2]
            category = row[3]
            onhand = row[4]
            lastmodified = row[5]
            
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

        self.cursor.execute(
            """
      select * from uTN_V_Frepple_CalendarData
            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:

            name = row[0]
            default = row[1]
            
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


        self.cursor.execute(
            """
        select * from uTN_V_Frepple_CalendarBucketsData
            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:

            calendar_id = row[0]
            value = row[1]
            startdate = row[2]
            enddate = row[3]
            priority = row[4]
            days = row[5]
            starttime = row[6]
            endtime = row[7]
            lastmodified = row[8]
            
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



    def extractItemSupplier(self):

        self.cursor.execute(
            """
        select * from uTN_V_Frepple_ItemSupplierData
            """
        )
        rows = self.cursor.fetchall()
        
        for row in rows:

            supplier = row[0]
            item = row[1]
            
            lookup_fields = {}
            data = {
                'supplier': supplier,
                'item': item,

            }
            
            item, created = update_or_create_record(CalendarBucket, lookup_fields, data)
            
            if created:
                print(f"Created new item supplier")
            else:
                print(f"Updated existing item supplier")
        
        print("Finished extracting items.")
        pass