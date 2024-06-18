
import pyodbc

from django.db import DEFAULT_DB_ALIAS

def getERPconnection(
    server='your_sql_server_hostname_or_ip',
    database_name='acutec',
    username='acutec',
    password='acutec',
    database=DEFAULT_DB_ALIAS
):
    """
    Customize this method to connect to the ERP database.

    This implementation uses pyodbc to connect from an Ubuntu machine to an MS SQL Server database.
    """

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