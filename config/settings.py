from dotenv import load_dotenv
import os

load_dotenv()

DEBUG = True
PORT = 8080

DB_CONFIG = {
    "DB_HOST": "localhost",
    "DB_USER": "root",
    "DB_PASSWORD":"",
    "DB_NAME": "term_project"
}