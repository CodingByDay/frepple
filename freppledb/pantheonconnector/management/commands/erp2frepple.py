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
ž
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
 
                self.extractItemSupplier()
                self.task.status = "?%"
                self.task.save(using=self.database)
            
 
                self.extractResource()
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
                self.task.status = "?%"
                self.task.save(using=self.database)
 
        
                self.extractBuffer()
                self.task.status = "?%"
                self.task.save(using=self.database)
 
 
 
                self.task.status = "Done. Errors:" + self.error_count
 
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
                
                existing_object = Location.objects.filter(**lookup_fields).first()

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
 
            select * from uTN_V_Frepple_CustomerData
 
 
            """
        )
 
        rows = self.cursor.fetchall()
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
                
                existing_object = Customer.objects.filter(**lookup_fields).first()

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
            SELECT *
            FROM uTN_V_Frepple_ItemData
            """
        )
        
        rows = self.cursor.fetchall()
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
                    'subcategory': subcategory,
                    'description': description,
                    'category': category,
                    'lastmodified': lastmodified or now()
                }
                
                existing_object = Item.objects.filter(**lookup_fields).first()

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
 
            select * from uTN_V_Frepple_SupplierData 
 
 
            """
        )
        rows = self.cursor.fetchall()
        objects_to_create = []
        objects_to_update = []
        for row in rows:
            try:
                name = row[0]
                description = row[1]
                lastmodified = row[2]
 
                lookup_fields = {'name': name}
                data = {
                    'subcategory': name,
                    'description': description,
                    'lastmodified': lastmodified or now()
                }
                
                existing_object = Supplier.objects.filter(**lookup_fields).first()

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
 
            select * from uTN_V_Frepple_ResourcesData 
 
            """
        )
        rows = self.cursor.fetchall()
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
 
                try:
                    available_calendar = Calendar.objects.get(name=available)
                except Calendar.DoesNotExist:
                    available_calendar = None
 
                try:
                    location_obj = Location.objects.get(name=location)
                except Location.DoesNotExist:
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
                
                existing_object = Resource.objects.filter(**lookup_fields).first()

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
 
 
            select * from uTN_V_Frepple_SalesOrderData 
 
 
            
            """
        )
        rows = self.cursor.fetchall()
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
                description = row[8]
                category = row[9]
                priority = row[10]
                lastmodified = row[11]
 
                try:
                    available_item = Item.objects.get(name=item)
                except Item.DoesNotExist:
                    available_item = None
 
                try:
                    available_location = Location.objects.get(name=location)
                except Location.DoesNotExist:
                    available_location = None
 
                try:
                    available_customer = Customer.objects.get(name=customer)
                except Customer.DoesNotExist:
                    available_customer = None
 
 
                lookup_fields = {'name': name}
                data = {
                    'name': name,
                    'item': available_item,
                    'location': available_location,
                    'customer': available_customer,
                    'status': status,
                    'due': due,
                    'quantity': quantity,
                    'minshipment': minshipment,
                    'description': description,
                    'category': category,
                    'priority': priority,
                    'lastmodified': lastmodified or now()
                }
                
                existing_object = Demand.objects.filter(**lookup_fields).first()

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
               select * from uTN_V_Frepple_OperationData 
            """
        )
        rows = self.cursor.fetchall()
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
                location = row[6]
                duration = row[7]
                duration_per = row[8]
                lastmodified = row[9]
                lookup_fields = {'name': name}
                try:
                    available_item = Item.objects.get(name=item)
                except Item.DoesNotExist:
                    available_item = None
 
                try:
                    available_location = Location.objects.get(name=location)
                except Location.DoesNotExist:
                    available_location = None
 
                data = {
                    'name': name,
                    'description': description,
                    'category': category,
                    'subcategory': subcategory,
                    'type': type_val,
                    'item': available_item,
                    'location': available_location,
                    'duration': duration,
                    'duration_per': duration_per,
                    'lastmodified': lastmodified or now()
                }
                
                existing_object = Operation.objects.filter(**lookup_fields).first()

                if existing_object:
                    update_object = Operation(**data)
                    objects_to_update.append(update_object)
                else:
                    new_object= Operation(**data)
                    objects_to_create.append(new_object)
            except Exception as e:
                self.error_count += 1
        with transaction.atomic(using=self.database):
            Operation.objects.bulk_create(objects_to_create, ignore_conflicts=True, batch_size=100000)
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
                select * from uTN_V_Frepple_OperationResourcesData
            """
        )
        rows = self.cursor.fetchall()
        objects_to_create = []
        objects_to_update = []
        for row in rows:
            try:               
                name = row[0]
                resource = row[1]
                quantity = row[2]
                lastmodified = row[3]
                
                lookup_fields = {'name': name, 'resource': resource, quantity: quantity}
 
                try:
                    available_resource = Resource.objects.get(name=resource)
                except resource.DoesNotExist:
                    available_resource = None
 
                data = {
                    'name': name,
                    'resource': available_resource,
                    'quantity': quantity,
                    'lastmodified': lastmodified or now()
                }
                
                existing_object = OperationResource.objects.filter(**lookup_fields).first()

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
                select * from uTN_V_Frepple_OperationMaterialData 
            """
        )
        rows = self.cursor.fetchall()
        
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
 
                try:
                    available_operation = Resource.objects.get(name=operation)
                except resource.DoesNotExist:
                    available_operation = None
 
                try:
                    available_item = Resource.objects.get(name=item)
                except resource.DoesNotExist:
                    available_item = None
                
                data = {
                    'operation': available_operation,
                    'item': available_item,
                    'type': type_val,
                    'quantity': quantity,
                    'lastmodified': lastmodified or now()
                }
                
                existing_object = OperationMaterial.objects.filter(**lookup_fields).first()

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
            
            select * from uTN_V_Frepple_BufferData
 
            """
        )
        rows = self.cursor.fetchall()

        objects_to_create = []
        objects_to_update = []
        
        for row in rows:
            try:              
                item = row[0]
                location = row[1]
                batch = row[2]
                onhand = row[3]
 
                
                try:
                    available_item = Item.objects.get(name=item)
                except Item.DoesNotExist:
                    available_item = None
 
                try:
                    available_location = Location.objects.get(name=location)
                except Location.DoesNotExist:
                    available_location = None
                
                lookup_fields = {'item': item, 'location': location, 'batch': batch }
 
                data = {
                    'item': available_item,
                    'location': available_location,
                    'batch': batch,
                    'onhand': onhand,
                }
                
                existing_object = Buffer.objects.filter(**lookup_fields).first()

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
      select * from uTN_V_Frepple_CalendarData
            """
        )
        rows = self.cursor.fetchall()
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
                
                existing_object = Calendar.objects.filter(**lookup_fields).first()

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
        select * from uTN_V_Frepple_CalendarBucketsData
            """
        )
        rows = self.cursor.fetchall()
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
                
                try:
                    available_calendar = Calendar.objects.get(name=calendar_id)
                except Calendar.DoesNotExist:
                    available_calendar = None
 
 
                lookup_fields = {'calendar': available_calendar, 'startdate': startdate, 'enddate': enddate, 'priority': priority}
 
            
 
                data = {
                    'calendar': available_calendar,
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
                
                existing_object = CalendarBucket.objects.filter(**lookup_fields).first()

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
        select * from uTN_V_Frepple_ItemSupplierData
            """
        )
        rows = self.cursor.fetchall()
        objects_to_create = []
        objects_to_update = []
        for row in rows:
            try:              
                supplier = row[0]
                item = row[1]
 
                try:
                    item_available = Item.objects.get(name=item)
                except Item.DoesNotExist:
                    item_available = None
 
                try:
                    supplier_available = Supplier.objects.get(name=supplier)
                except Location.DoesNotExist:
                    supplier_available = None
 
 
                lookup_fields = {'supplier': supplier, 'item': item}
 
                data = {
                    'supplier': supplier_available,
                    'item': item_available,
                }
                
                existing_object = ItemSupplier.objects.filter(**lookup_fields).first()

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