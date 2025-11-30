import mysql.connector
from mysql.connector import Error

def create_connection():
    connection = None
    try:
        # Connect to the MySQL Server
        connection = mysql.connector.connect(
            host='localhost',       # Or '127.0.0.1'
            user='root',            # The default user
            password='14625478Az' # The password you set during installation
        )

        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"✅ Successfully connected to MySQL Server version {db_info}")
            
            # Optional: Run a quick query to verify cursor works
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE();")
            record = cursor.fetchone()
            print(f"You are currently connected to database: {record[0]}")

    except Error as e:
        print(f"❌ Error while connecting to MySQL: {e}")
        
    finally:
        # Always close the connection when done
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("🔒 MySQL connection is closed")

if __name__ == '__main__':
    create_connection()