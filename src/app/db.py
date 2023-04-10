import os
import shutil
from datetime import datetime
import sqlite3
from sqlite3 import Error
from flask import Flask
from . import utils

class DB:
    last_backup = None

    def __init__(self, app: Flask) -> None:
        self.db_path = os.path.join(app.instance_path, 'db.sqlite')
        
        self.connection = None
        try:
            self.connection = sqlite3.connect(self.db_path)
        except Error as e:
            print(e)
            return
        
        self.cursor = self.connection.cursor()
        
        self.create_table('invoices', [
            'id integer PRIMARY KEY',
            'date integer NOT NULL'
        ])

        self.create_table('billing_positions', [
            'id integer PRIMARY KEY',
            'date integer NOT NULL',
            'file text NOT NULL',
            'hourly_rate real',
            'billed_hours real',
            'billed_amount real',
            'earned_amount real NOT NULL',
            'invoiced_amount real',
            'invoice_id integer',
            'FOREIGN KEY(invoice_id) REFERENCES invoices(id)'
        ])

    def execute(self, sql: str, parameters: tuple = (), commit: bool = False) -> tuple[int | None, list]:
        self.cursor.execute(sql, parameters)
        if commit:
            self.connection.commit()
        self.last_row_id = self.cursor.lastrowid
        self.row_values = self.cursor.fetchall()
        if self.cursor.description is not None:
            self.row_keys = [d[0] for d in self.cursor.description]
        else:
            self.row_keys = None

    def backup(self) -> bool:
        if DB.last_backup is not None and DB.last_backup + 1800 > round(datetime.timestamp(datetime.now())):
            return False
        
        DB.last_backup = round(datetime.timestamp(datetime.now()))
        shutil.copyfile(self.db_path, f"{self.db_path}.backup-{DB.last_backup}")
        return True

    def create_table(self, table_name: str, columns: list[str]) -> None:
        column_placeholders = ', '.join(columns)
        sql = f'CREATE TABLE IF NOT EXISTS {table_name} ({column_placeholders});'

        try:
            self.execute(sql, commit=True)
        except Error as e:
            print(e)

    def get_statistics(self) -> list | None:
        sql = '''
            SELECT
                NULL AS year,
                count(id) AS count_positions,
                IFNULL(sum(billed_amount), 0) AS total_billed,
                IFNULL(sum(earned_amount), 0) AS total_earned,
                IFNULL(sum(invoiced_amount), 0) AS total_invoiced
            FROM billing_positions
            UNION
            SELECT
                date / 10000 AS year,
                count(id) AS count_positions,
                IFNULL(sum(billed_amount), 0) AS total_billed,
                IFNULL(sum(earned_amount), 0) AS total_earned,
                IFNULL(sum(invoiced_amount), 0) AS total_invoiced
            FROM billing_positions
            GROUP BY year
            ORDER BY year;
        '''
        _, rows = self.execute(sql)

        statistics = []
        try:
            for row in rows:
                statistics.append({
                    'year': row[0],
                    'count_positions': row[1],
                    'total_billed': round(row[2], 2),
                    'total_earned': round(row[3], 2),
                    'total_invoiced': round(row[4], 2)
                })
        except:
            return None
        
        return statistics

    # BILLABLE POSITIONS

    @staticmethod
    def format_billing_position(**kwargs) -> dict:
        formatted_billing_position = {}
        for key, value in kwargs.items():
            match key:
                case 'id':
                    formatted_billing_position[key] = int(value)
                case 'date':
                    formatted_billing_position[key] = utils.int_to_date(value)
                case 'file':
                    formatted_billing_position[key] = str(value)
                case 'hourly_rate':
                    formatted_billing_position[key] = utils.optional_float(value)
                case 'billed_hours':
                    formatted_billing_position[key] = utils.optional_float(value)
                case 'billed_amount':
                    formatted_billing_position[key] = utils.optional_float(value)
                case 'earned_amount':
                    formatted_billing_position[key] = float(value)
                case 'invoiced_amount':
                    formatted_billing_position[key] = utils.optional_int(value)
                case 'invoice_id':
                    formatted_billing_position[key] = utils.optional_int(value)
        return formatted_billing_position
        
    def add_billing_position(self,
        date: datetime,
        file: str,
        hourly_rate: float,
        billed_hours: float,
        billed_amount: float,
        earned_amount: float,
        ) -> int:

        sql = '''
            INSERT INTO billing_positions (date, file, hourly_rate, billed_hours, billed_amount, earned_amount)
            VALUES (?, ?, ?, ?, ?, ?);
        '''
        self.execute(sql, (utils.date_to_int(date), file, hourly_rate, billed_hours, billed_amount, earned_amount), commit=True)
        return self.last_row_id

    def remove_billing_position(self, id: int):
        sql = '''
            DELETE FROM billing_positions
            WHERE id = ?
        '''

        self.execute(sql, (id, ), commit=True)
    
    def update_billing_position(self,
        id: int,
        date: datetime,
        file: str,
        hourly_rate: float,
        billed_hours: float,
        billed_amount: float,
        earned_amount: float
        ) -> None:
        sql = '''
            UPDATE billing_positions
            SET date = ?, file = ?, hourly_rate = ?, billed_hours = ?, billed_amount = ?, earned_amount = ?
            WHERE id = ?;
        '''

        self.execute(sql, (utils.date_to_int(date), file, hourly_rate, billed_hours, billed_amount, earned_amount, id), commit=True)

    def get_billing_position(self, id: int) -> dict | None:
        sql = '''
            SELECT *
            FROM billing_positions
            WHERE id = ?
            ORDER BY date;
        '''
        self.execute(sql, (id, ))
        
        if len(self.row_values) != 1:
            return None
        
        billing_position = dict(zip(self.row_keys, self.row_values[0]))
        return self.format_billing_position(**billing_position)

    def get_all_billing_positions(self) -> list:
        sql = '''
            SELECT *
            FROM billing_positions
            ORDER BY date;
            '''
        self.execute(sql)

        billing_positions = [dict(zip(self.row_keys, row_value)) for row_value in self.row_values]
        billing_positions = [self.format_billing_position(**b) for b in billing_positions]
        return billing_positions
    
    def get_open_billing_positions(self, file: str) -> list:

        sql = '''
            SELECT *
            FROM billing_positions
            WHERE invoice_id IS NULL AND file = ?
            ORDER BY date;
        '''
        self.execute(sql, (file, ))

        billing_positions = [dict(zip(self.row_keys, row_value)) for row_value in self.row_values]
        billing_positions = [self.format_billing_position(**b) for b in billing_positions]
        return billing_positions

    def get_invoiced_billing_positions(self, invoice_id: int) -> list:
        
        sql = '''
            SELECT *
            FROM billing_positions
            WHERE invoice_id = ?
            ORDER BY file, date;
        '''
        self.execute(sql, (invoice_id, ))

        billing_positions = [dict(zip(self.row_keys, row_value)) for row_value in self.row_values]
        billing_positions = [self.format_billing_position(**b) for b in billing_positions]
        return billing_positions

    def invoice_billing_position(self,
        id: int, 
        invoiced_amount: float,
        invoice_id: int
        ) -> None:

        sql = '''
            UPDATE billing_positions
            SET invoiced_amount = ?, invoice_id = ?
            WHERE id = ?;
        '''

        self.execute(sql, (invoiced_amount, invoice_id, id), commit=True)
    

    # INVOICES

    @staticmethod
    def format_invoice(**kwargs) -> dict:
        invoice = {}
        for key, value in kwargs.items():
            match key:
                case 'id':
                    invoice[key] = int(value)
                case 'date':
                    invoice[key] = utils.int_to_date(value)
                case 'total':
                    invoice[key] = float(value)
        return invoice

    def add_invoice(self, date: datetime) -> int:
        sql = 'INSERT INTO invoices (date) VALUES (?);'
        self.execute(sql, (date.date().strftime('%Y%m%d'), ), commit=True)
        return self.last_row_id
    
    def remove_invoice(self, id: int) -> None:
        sql = '''
            UPDATE billing_positions
            SET invoiced_amount = NULL, invoice_id = NULL
            WHERE invoice_id = ?;
        '''
    
        self.execute(sql, (id, ))

        sql = '''
            DELETE FROM invoices
            WHERE id = ?
        '''

        self.execute(sql, (id, ), commit=True)

    def get_all_invoices(self) -> list:
        sql = '''
            SELECT invoices.id, invoices.date, IFNULL(sum(billing_positions.invoiced_amount), 0) AS total
            FROM invoices
            LEFT OUTER JOIN billing_positions ON invoices.id = billing_positions.invoice_id
            GROUP BY invoices.id
            ORDER BY invoices.date;
        '''
        self.execute(sql)
        
        invoices = [dict(zip(self.row_keys, row_value)) for row_value in self.row_values]
        return invoices
    
    def get_invoice(self, id: int) -> dict | None:
        sql = '''
            SELECT invoices.id, invoices.date, sum(billing_positions.invoiced_amount) AS total
            FROM invoices
            LEFT OUTER JOIN billing_positions ON invoices.id = billing_positions.invoice_id
            WHERE invoices.id = ?
            GROUP BY invoices.id;
        '''
        self.execute(sql, (id, ))
        
        if len(self.row_values) != 1:
            return None
        
        invoice = dict(zip(self.row_keys, self.row_values[0]))
        return self.format_invoice(**invoice)
