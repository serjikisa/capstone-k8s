from typing import List, Dict
from flask import Flask
import mysql.connector
import json
import math
import os

app = Flask(__name__)

class Query:
    def __init__(self):
        self.config = {
            'user': 'root',
            'password': os.environ.get('DB_PASSWORD'),
            'host': os.environ.get('DB_HOST'),
            'port': '3306',
            'database': 'knights'
        }

    def favorite_colors(self) -> List[Dict]:
        connection = mysql.connector.connect(**self.config)
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM favorite_colors')
        results = [{name: color} for (name, color) in cursor]
        cursor.close()
        connection.close()

        return results

    def db_exists(self):
        create_config = {**self.config}
        create_config['database'] = 'mysql'
        connection = mysql.connector.connect(**create_config)
        cursor = connection.cursor()
        try:
            cursor.execute('USE knights')
            return True
        except:
            return False

    def init_db(self):
        create_config = {**self.config}
        create_config['database'] = 'mysql'
        connection = mysql.connector.connect(**create_config)

        create_script = '''
    CREATE TABLE favorite_colors (
    name VARCHAR(20),
    color VARCHAR(10)
    )'''

        insert_script = '''
    INSERT INTO favorite_colors
    (name, color)
    VALUES
    ('Lancelot', 'blue'),
    ('Galahad', 'yellow')
        '''
        connection = mysql.connector.connect(**create_config)
        cursor = connection.cursor()
        cursor.execute('CREATE DATABASE knights')
        cursor.execute('USE knights')
        cursor.execute(create_script)
        cursor.execute(insert_script)
        connection.commit()
        cursor.close()
        connection.close()    


def use_cpu(cycles):
    x = 0.0001
    for i in range(cycles):
        x += math.sqrt(x)

@app.route('/')
def index() -> str:
    q = Query()
    if not q.db_exists():
        q.init_db()
    
    use_cpu(cycles=1000000)
    return json.dumps({'favorite_colors': Query().favorite_colors()})

if __name__ == '__main__':
    app.run(host='0.0.0.0')