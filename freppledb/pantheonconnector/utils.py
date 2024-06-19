import pyodbc
from django.db import DEFAULT_DB_ALIAS

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