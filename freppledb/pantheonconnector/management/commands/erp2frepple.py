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
from django.db import transaction

from freppledb import __version__
from freppledb.common.models import User, Parameter
from freppledb.execute.models import Task
 
from ...utils import getERPconnection
from ...utils import update_or_create_record, hours_to_duration  # Import the utility function 03.07.2024 Janko Joviд█iд┤
 
 
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
 
    # For the display in the execution screen
 
 
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
 
        self.error_count = 0
 
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
 
            # Extract all tables
            try:
                print("Location")
                self.extractLocation()
                self.task.status = "7%"
                self.task.save(using=self.database)
 
                print("Customer")
                self.extractCustomer()
                self.task.status = "14%"
                self.task.save(using=self.database)
 
                print("Item")
                self.extractItem()
                self.task.status = "21%"
                self.task.save(using=self.database)

                print("Calendar")
                self.extractCalendar()
                self.task.status = "28%"
                self.task.save(using=self.database)
 
                print("Calendar bucket")
                self.extractCalendarBucket()
                self.task.status = "35%"
                self.task.save(using=self.database)
 
                print("Supplier")
                self.extractSupplier()
                self.task.status = "42%"
                self.task.save(using=self.database)
 
                print("ItemSupplier")
                self.extractItemSupplier()
                self.task.status = "49%"
                self.task.save(using=self.database)
            
                print("Resource")
                self.extractResource()
                self.task.status = "56%"
                self.task.save(using=self.database)
 

                print("Sales order")
                self.extractSalesOrder()
                self.task.status = "63%"
                self.task.save(using=self.database)
 
                print("Operation")
                self.extractOperation()
                self.task.status = "70%"
                self.task.save(using=self.database)
 

                print("Operation resource")
                self.extractOperationResource()
                self.task.status = "77%"
                self.task.save(using=self.database)
 
                print("Operation material")
                self.extractOperationMaterial()
                self.task.status = "85%"
                self.task.save(using=self.database)
 
                print("Buffer") 
                self.extractBuffer()
                self.extractParameters()
                self.extractItemDistribution()

                
                self.task.status = "99%"
                self.task.save(using=self.database)
 

                self.task.status = "Done. Errors:" + str(self.error_count)
 
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
 
            SELECT Name, Description, LastModified FROM uTN_V_Frepple_LocationData;
                    
            """
        )
        rows = self.cursor.fetchall()


        existing_objects = {}
        for obj in Location.objects.all():
            existing_objects[(obj.name)] = obj

        objects_to_create = []
        objects_to_update = []

        for row in rows:
            try:
                name = row[0]
                description = row[1]
                lastmodified = row[2]
 
                lookup_fields = {'name': name}
 
                data = {
                    'name': name,
                    'description': description,
                    'lastmodified': lastmodified or now()
                }
                
                existing_object = existing_objects.get((name))

                if existing_object:
                    update_object = Location(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object= Location(**data)
                    objects_to_create.append(new_object)
            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            Location.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=100000)
            for object_current in objects_to_update:
                object_current.save()
 
 
 
    def extractCustomer(self):
 
        self.cursor.execute(
            """
            SELECT Name, Category, LastModified FROM uTN_V_Frepple_CustomerData;
            """
        )
 
        rows = self.cursor.fetchall()

        existing_objects = {}
        for obj in Customer.objects.all():
            existing_objects[(obj.name)] = obj

        objects_to_create = []
        objects_to_update = []
        for row in rows:
            try:
                name = row[0]
                category = row[1]
                lastmodified = row[2]
 
                lookup_fields = {'name': name}

                data = {
                    'name': name,
                    'category': category,
                    'lastmodified': lastmodified or now()
                }
                
                existing_object = existing_objects.get((name))

                if existing_object:
                    update_object = Customer(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object= Customer(**data)
                    objects_to_create.append(new_object)
            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            Customer.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=100000)
            for object_current in objects_to_update:
                object_current.save()
 
    def extractItem(self):
 
        self.cursor.execute(
            """
            SELECT Name, Subcategory, Description, Category, timeStamp FROM uTN_V_Frepple_ItemData;
            """
        )
        
        rows = self.cursor.fetchall()
        existing_objects = {}
        for obj in Item.objects.all():
            existing_objects[(obj.name)] = obj
        objects_to_create = []
        objects_to_update = []


        for row in rows:
            try:
                name = row[0]
                subcategory = row[1]
                description = row[2]
                category = row[3]
                lastmodified = row[4]
                
                lookup_fields = {'name': name}
                data = {
                    'name': name,
                    'subcategory': subcategory,
                    'description': description,
                    'category': category,
                    'lastmodified': lastmodified or now()
                }
                
                existing_object = existing_objects.get((name))

                if existing_object:
                    update_object = Item(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object= Item(**data)
                    objects_to_create.append(new_object)
            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            Item.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=100000)
            for object_current in objects_to_update:
                object_current.save()
        
 
 
    def extractSupplier(self):
 
        self.cursor.execute(
            """
            SELECT Name, Description, LastModified FROM uTN_V_Frepple_SupplierData; 
            """
        )
        rows = self.cursor.fetchall()

        existing_objects = {}
        for obj in Supplier.objects.all():
            existing_objects[(obj.name)] = obj


        objects_to_create = []
        objects_to_update = []
        for row in rows:
            try:
                name = row[0]
                description = row[1]
                lastmodified = row[2]
 
                lookup_fields = {'name': name}

                data = {
                    'name': name,
                    'description': description,
                    'lastmodified': lastmodified or now()
                }
                
                existing_object = existing_objects.get((name))

                if existing_object:
                    update_object = Supplier(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object= Supplier(**data)
                    objects_to_create.append(new_object)
            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            Supplier.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=100000)
            for object_current in objects_to_update:
                object_current.save()
 
    def extractResource(self):
 
 
        self.cursor.execute(
            """
            SELECT Name, Category, Subcategory, Maximum, Location, Type, LastModified, Available FROM uTN_V_Frepple_ResourcesData; 
            """
        )
        rows = self.cursor.fetchall()

        calendars= {calendar.name: calendar for calendar in Calendar.objects.all()}
        locations = {location.name: location for location in Location.objects.all()}

        existing_objects = {}
        for obj in Resource.objects.all():
            existing_objects[(obj.name)] = obj

        objects_to_create = []
        objects_to_update = []
        for row in rows:
            try:
                name = row[0]
                category = row[1]
                subcategory = row[2]
                maximum = row[3]
                location = row[4]
                type_val = row[5]
                lastmodified = row[6]
                available = row[7]
                
                lookup_fields = {'name': name }
 
                location_available = locations.get(location)
                calendar_available = calendars.get(available)

                if location_available is None or calendar_available is None:
                    continue
                
 
                data = {
                    'name': name,
                    'category': category,
                    'subcategory': subcategory,
                    'maximum': maximum,
                    'location': location_available,
                    'type': type_val,
                    'lastmodified': lastmodified or now(),
                    'available': calendar_available
                }
                
                existing_object = existing_objects.get((name))

                if existing_object:
                    update_object = Resource(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object= Resource(**data)
                    objects_to_create.append(new_object)

            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            Resource.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=100000)
            for object_current in objects_to_update:
                object_current.save()
 
    def extractSalesOrder(self):
 
        self.cursor.execute(
            """
            SELECT Name, Item, Location, Customer, Status, Due, Quantity, MinShipment, Description, Category, Priority, LastModified FROM uTN_V_Frepple_SalesOrderData;            
            """
        )
        rows = self.cursor.fetchall()

        items = {item.name: item for item in Item.objects.all()}
        locations = {location.name: location for location in Location.objects.all()}
        customers = {customer.name: customer for customer in Customer.objects.all()}

        existing_objects = {}
        for obj in Demand.objects.all():
            existing_objects[(obj.name)] = obj

        objects_to_create = []
        objects_to_update = []
        for row in rows:
            try:
                name = row[0]
                item = row[1]
                location = row[2]
                customer = row[3]
                status = row[4]
                due = row[5]
                quantity = row[6]
                minshipment = row[7]
                description = row[8][:500]
                category = row[9]
                priority = row[10]
                lastmodified = row[11]
 
                item_available = items.get(item)
                location_available = locations.get(location)
                customer_available = customers.get(customer)


                if item_available is None or location_available is None or customer_available is None:
                    continue


                lookup_fields = {'name': name}



                data = {
                    'name': name,
                    'item': item_available,
                    'location': location_available,
                    'customer': customer_available,
                    'status': status,
                    'due': due,
                    'quantity': quantity,
                    'minshipment': minshipment,
                    'description': description,
                    'category': category,
                    'priority': priority,
                    'lastmodified': lastmodified or now()
                }
                
                existing_object = existing_objects.get((name))

                if existing_object:
                    update_object = Demand(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object= Demand(**data)
                    objects_to_create.append(new_object)
            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            Demand.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=100000)
            for object_current in objects_to_update:
                object_current.save()
 
 
    def extractOperation(self):
 
        self.cursor.execute(
            """
               SELECT Name, acDescr, Category, Subcategory, Type, Item, Location, Duration, "Duration Per Unit", LastModified FROM uTN_V_Frepple_OperationData;
            """
        )
        rows = self.cursor.fetchall()

        items = {item.name: item for item in Item.objects.all()}
        locations = {location.name: location for location in Location.objects.all()}
        existing_objects = {}
        for obj in Operation.objects.all():
            existing_objects[(obj.name)] = obj
        objects_to_create = []
        objects_to_update = []
        for row in rows:
            try:
                name = row[0]
                description = row[1]
                category = row[2]
                subcategory = row[3]
                type_val = row[4]
                item = row[5]
                location = "factory" # For now, just for testing purposes.
                duration = row[7]
                duration_per = row[8]
                lastmodified = row[9]


                lookup_fields = {'name': name}
                

                item_available = items.get(item)
                location_available = locations.get(location)
 

                if item_available is None or location_available is None:
                        continue
                
                data = {
                    'name': name,
                    'description': description,
                    'category': category,
                    'subcategory': subcategory,
                    'type': type_val,
                    'item': item_available,
                    'location': location_available,
                    'duration': hours_to_duration(duration),
                    'duration_per': hours_to_duration(duration_per),
                    'lastmodified': lastmodified or now()
                }
                
                existing_object = existing_objects.get((name))

                if existing_object:
                    update_object = Operation(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object= Operation(**data)
                    objects_to_create.append(new_object)
            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            Operation.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=1000)
            for object_current in objects_to_update:
                object_current.save()
 
 
 
 
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
 
        self.cursor.execute (
            """
                SELECT Name, Resource, Quantity, LastModified FROM uTN_V_Frepple_OperationResourcesData;
            """
        )
        rows = self.cursor.fetchall()

        resources = {resource.name: resource for resource in Resource.objects.all()}
        operations = {operation.name: operation for operation in Operation.objects.all()}


        existing_objects = {}
        for obj in OperationResource.objects.all():
            existing_objects[(obj.name, obj.resource, obj.quantity)] = obj

        objects_to_create = []
        objects_to_update = []
        for row in rows:
            try:               
                operation = row[0]
                resource = row[1]
                quantity = row[2]
                lastmodified = row[3]
                
                lookup_fields = {'operation': operation, 'resource': resource, quantity: quantity}
 
                resource_available = resources.get(resource)
                operation_available = operations.get(operation)

                if resource_available is None or operation_available is None:
                    continue

                data = {
                    'operation': operation_available,
                    'resource': resource_available,
                    'quantity': quantity,
                    'lastmodified': lastmodified or now()
                }
                
                existing_object = existing_objects.get((operation, resource, quantity))

                if existing_object:
                    update_object = OperationResource(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object= OperationResource(**data)
                    objects_to_create.append(new_object)
            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            OperationResource.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=100000)
            for object_current in objects_to_update:
                object_current.save()
        
 
 
    def extractOperationMaterial(self):
 
 
        self.cursor.execute(
            """
                SELECT Operation, Item, Type, Quantity, LastModified FROM uTN_V_Frepple_OperationMaterialData; 
            """
        )
        rows = self.cursor.fetchall()
        
        items = {item.name: item for item in Item.objects.all()}
        operations = {operation.name: operation for operation in Operation.objects.all()}
        existing_objects = {}
        for obj in OperationMaterial.objects.all():
            existing_objects[(obj.operation, obj.item, obj.type, obj.quantity)] = obj
        objects_to_create = []
        objects_to_update = []

        for row in rows:
            try:
                operation = row[0]
                item = row[1]
                type_val = row[2]
                quantity = row[3]
                lastmodified = row[4]
                
                lookup_fields = {'operation': operation, 'item': item, 'type_val': type_val, 'quantity': quantity}
 
                item_available = items.get(item)
                operation_available = operations.get(operation)
                

                if item_available is None or operation_available is None:
                    continue

                data = {
                    'operation': operation_available,
                    'item': item_available,
                    'type': type_val,
                    'quantity': quantity,
                    'lastmodified': lastmodified or now()
                }
                
                existing_object = existing_objects.get((operation, item, type_val, quantity))

                if existing_object:
                    update_object = OperationMaterial(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object= OperationMaterial(**data)
                    objects_to_create.append(new_object)
            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            OperationMaterial.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=100000)
            for object_current in objects_to_update:
                object_current.save()
 
 
 
    def extractBuffer(self):
 
 
        self.cursor.execute(
            """
            
            SELECT Item, Location, Batch, OnHand FROM uTN_V_Frepple_BufferData;
 
            """
        )
        rows = self.cursor.fetchall()
        
        items = {item.name: item for item in Item.objects.all()}
        locations = {location.name: location for location in Location.objects.all()}
        existing_objects = {}
        for obj in Buffer.objects.all():
            existing_objects[(obj.item, obj.location, obj.batch)] = obj
        objects_to_create = []
        objects_to_update = []
        
        for row in rows:
            try:              
                item = row[0]
                location = row[1]
                batch = row[2]
                onhand = row[3]
 
                
                item_available = items.get(item)
                location_available = locations.get(location)

                if item_available is None or location_available is None:
                    continue
                
                lookup_fields = {'item': item, 'location': location, 'batch': batch }
 
                data = {
                    'item': item_available,
                    'location': location_available,
                    'batch': batch,
                    'onhand': onhand,
                }
                
                existing_object = existing_objects.get((item, location, location, batch))

                if existing_object:
                    update_object = Buffer(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object= Buffer(**data)
                    objects_to_create.append(new_object)

            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            Buffer.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=100000)
            for object_current in objects_to_update:
                object_current.save()
 
 
 
    def extractCalendar(self):
 
        self.cursor.execute(
            """
      SELECT Name, "Default" FROM uTN_V_Frepple_CalendarData;
            """
        )
        rows = self.cursor.fetchall()

        existing_objects = {}
        for obj in Calendar.objects.all():
            existing_objects[(obj.name)] = obj

        objects_to_create = []
        objects_to_update = []
        for row in rows:
            try:             
                name = row[0]
                default = row[1]
                
                lookup_fields = {'name': name}
                data = {
                    'name': name,
                    'defaultvalue': default,
 
                }
                
                existing_object = existing_objects.get((name))

                if existing_object:
                    update_object = Calendar(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object= Calendar(**data)
                    objects_to_create.append(new_object)

            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            Calendar.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=100000)
            for object_current in objects_to_update:
                object_current.save()
 
    def extractCalendarBucket(self):
 
 
        self.cursor.execute(
            """
           SELECT Calendar, Value, Start, "End", Priority, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday, StartTime, EndTime FROM uTN_V_Frepple_CalendarBucketsData;
            """
        )
        rows = self.cursor.fetchall()
        calendars = {calendar.name: calendar for calendar in Calendar.objects.all()}


        existing_objects = {}
        for obj in CalendarBucket.objects.all():
            existing_objects[(obj.calendar,obj.startdate,obj.enddate,obj.priority)] = obj


        objects_to_create = []
        objects_to_update = []
        for row in rows:
            try:               
                calendar_id = row[0]
                value = row[1]
                startdate = row[2]
                enddate = row[3]
                priority = row[4]
                monday = row[5]
                tuesday = row[6]
                wednesday = row[7]
                thursday = row[8]
                friday = row[9]
                saturday = row[10]
                sunday = row[11]
                starttime = row[12]
                endtime = row[13]
                
                calendar_available = calendars.get(calendar_id)

                if calendar_available is None:
                    continue
 
 
                lookup_fields = {'calendar': calendar_id, 'startdate': startdate, 'enddate': enddate, 'priority': priority}
 
            
 
                data = {
                    'calendar': calendar_available,
                    'value': value,
                    'startdate': startdate,
                    'enddate': enddate,
                    'priority': priority,
                    'monday': monday,
                    'tuesday': tuesday,
                    'wednesday': wednesday,
                    'thursday': thursday,
                    'friday': friday,
                    'saturday': saturday,
                    'sunday': sunday,
                    'starttime': starttime,
                    'endtime': endtime,
                }
                
                existing_object = existing_objects.get((calendar_id, startdate, enddate, priority))

                if existing_object:
                    update_object = CalendarBucket(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object= CalendarBucket(**data)
                    objects_to_create.append(new_object)
            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            CalendarBucket.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=100000)
            for object_current in objects_to_update:
                object_current.save()
 
 
 
    def extractItemSupplier(self):
 
        self.cursor.execute(
            """
        SELECT Supplier, Item FROM uTN_V_Frepple_ItemSupplierData;
            """
        )
        rows = self.cursor.fetchall()

        # Cache all items and suppliers in memory
        items = {item.name: item for item in Item.objects.all()}
        suppliers = {supplier.name: supplier for supplier in Supplier.objects.all()}

        existing_objects = {}
        for obj in ItemSupplier.objects.all():
            existing_objects[(obj.supplier,obj.item)] = obj

        objects_to_create = []
        objects_to_update = []
        for row in rows:
            try:              
                supplier = row[0]
                item = row[1]
 
                item_available = items.get(item)
                supplier_available = suppliers.get(supplier)

                if item_available is None or supplier_available is None:
                    continue
 
                lookup_fields = {'supplier': supplier, 'item': item}
 
                data = {
                    'supplier_id': supplier_available,
                    'item_id': item_available,
                }
                
                existing_object = existing_objects.get((supplier, item))


                if existing_object:
                    update_object = ItemSupplier(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object= ItemSupplier(**data)
                    objects_to_create.append(new_object)
            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            ItemSupplier.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=100000)
            for object_current in objects_to_update:
                object_current.save()



    def extractParameters(self):
 
        self.cursor.execute(
            """
        SELECT Name, Value, Description FROM uTN_V_Frepple_ParametersData;
            """
        )

        rows = self.cursor.fetchall()


        existing_objects = {}
        for obj in Parameter.objects.all():
            existing_objects[(obj.name,obj.value,obj.description)] = obj

        objects_to_create = []
        objects_to_update = []

        for row in rows:
            try:              
                name = row[0]
                value = row[1]
                description = row[2]

                lookup_fields = {'supplier': supplier, 'item': item}
 
                data = {
                    'name': name,
                    'value': value,
                    'description': description,
                }
                
                existing_object = existing_objects.get((name, value, description))


                if existing_object:
                    update_object = Parameter(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object= Parameter(**data)
                    objects_to_create.append(new_object)
            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            Parameter.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=100000)
            for object_current in objects_to_update:
                object_current.save()




    def extractItemDistribution(self):

        self.cursor.execute(
            """
        SELECT Item, Origin, Destination, Cost, LeadTime, SizeMinimum, SizeMultiple, SizeMaximum, BatchWindow, EffectiveStart, EffectiveEnd, Priority, Resource, ResourceQty, Fence FROM uTN_V_Frepple_ItemDistribution;
            """
        )

        rows = self.cursor.fetchall()

        items = {item.name: item for item in Item.objects.all()}
        locations = {location.name: location for location in Location.objects.all()}
        # resources = {resource.name: resource for resource in Resource.objects.all()}

        existing_objects = {}
        for obj in ItemDistribution.objects.all():
            existing_objects[(obj.item,obj.origin,obj.location, obj.cost,
                              obj.leadtime, obj.sizeminimum, sizemaximum, batchwindow,
                              obj.effectivestart, obj.effective_end, obj.priority,
                              obj.resource, obj.resource_qty, obj.fence)] = obj


        objects_to_create = []
        objects_to_update = []

        for row in rows:
            try:       
                item = row[0]
                origin = row[1]
                destination = row[2]
                cost = row[3]
                leadtime = row[4]
                sizeminimum = row[5]
                sizemultiple = row[6]
                sizemaximum = row[7]
                batchwindow = row[8]
                effectivestart = row[9]
                effectiveend = row[10]
                priority = row[11]
                resource = row[12]
                resourceQty = row[13]
                fence = row[14]

                lookup_fields = {'supplier': supplier, 'item': item}

                item_available = items.get(item)
                location_available_origin = locations.get(origin)
                location_available_destination = locations.get(destination)

                if item_available is None or location_available_origin is None:
                    continue

                if destination == "":
                    data = {
                    'item': item_available,
                    'origin': location_available_origin,
                    'location': location_available_destination,
                    'cost': cost,
                    'leadtime': hours_to_duration(leadtime),
                    'sizeminimum': sizeminimum,
                    'sizemultiple': sizemultiple,
                    'sizemaximum': sizemaximum,
                    'batchwindow': hours_to_duration(batchwindow),
                    'effective_start': effectivestart,
                    'effective_end': effectiveend,
                    'priority': priority,
                    'resource_qty': resourceQty,
                    'fence': hours_to_duration(fence),
                }
                else:
                    data = {
                    'item': item_available,
                    'origin': location_available_origin,
                    'location': location_available_destination,
                    'cost': cost,
                    'leadtime': hours_to_duration(leadtime),
                    'sizeminimum': sizeminimum,
                    'sizemultiple': sizemultiple,
                    'sizemaximum': sizemaximum,
                    'batchwindow': hours_to_duration(batchwindow),
                    'effective_start': effectivestart,
                    'effective_end': effectiveend,
                    'priority': priority,
                    'resource_qty': resourceQty,
                    'fence': hours_to_duration(fence),
                }
              
                
                existing_object = existing_objects.get((item, origin, cost, leadtime, 
                                                        sizeminimum, sizemultiple, sizemaximum, batchwindow, effectivestart, 
                                                        effectiveend, priority, resourceQty, fence))

                if existing_object:
                    update_object = ItemDistribution(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object = ItemDistribution(**data)
                    objects_to_create.append(new_object)
            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            ItemDistribution.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=100000)
            for object_current in objects_to_update:
                object_current.save()