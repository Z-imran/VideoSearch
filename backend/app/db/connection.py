import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector
from app.config import settings


def get_connection():
    connection = psycopg.connect(settings.database_url, row_factory=dict_row)
    register_vector(connection)
    return connection