import pyodbc
from django.db import DEFAULT_DB_ALIAS
from django.db import transaction



def getERPconnection(database=DEFAULT_DB_ALIAS):

    """
    In.Sist d.o.o. 19 june 2024 Janko Jovičić
    """

    server = '172.17.1.77\\CROATIAN,1500'
    database_name = 'PA_METAL_PRODUCT'
    username = 'metalweb'
    password = 'net321tnet!'

    # Construct the connection string
    connection_string = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database_name};"
        f"UID={username};"
        f"PWD={password}"
    )

    # Attempt to establish the connection
    try:
        conn = pyodbc.connect(connection_string, timeout=10)
        print("Connection successful!")
        return conn
    except Exception as e:
        print(f"Error connecting to MSSQL: {str(e)}")
        return None
    
def update_or_create_record(model, lookup_fields, data):
    """
    Update or create a record in the specified model.

    :param model: The model class to update or create the record in.
    :param lookup_fields: A dictionary of fields to use for looking up the record.
    :param data: A dictionary of fields to update or create the record with.
    :return: The created or updated model instance and a boolean indicating if it was created.
    """
    with transaction.atomic():
        instance, created = model.objects.update_or_create(
            **lookup_fields,
            defaults=data
        )
    return instance, created