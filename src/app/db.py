import os
import shutil
from datetime import datetime
import sqlite3
from sqlite3 import Error
from flask import Flask
from .utils import optional_float, optional_int

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

    def backup(self) -> bool:
        if DB.last_backup is not None and DB.last_backup + 1800 > round(datetime.timestamp(datetime.now())):
            return False
        
        DB.last_backup = round(datetime.timestamp(datetime.now()))
        shutil.copyfile(self.db_path, f"{self.db_path}.backup-{DB.last_backup}")
        return True

    def get_statistics(self) -> list | None:
        sql = '''
            SELECT
                NULL AS year,
                count(id) AS count_positions,
                sum(billed_amount) AS total_billed,
                sum(earned_amount) AS total_earned,
                sum(invoiced_amount) AS total_invoiced
            FROM billing_positions
            UNION
            SELECT
                date / 10000 AS year,
                count(id) AS count_positions,
                sum(billed_amount) AS total_billed,
                sum(earned_amount) AS total_earned,
                sum(invoiced_amount) AS total_invoiced
            FROM billing_positions
            GROUP BY year
            ORDER BY year;
        '''
        cursor = self.connection.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()

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

    def create_table(self, table_name: str, columns: list[str]) -> None:

        column_placeholders = ', '.join(columns)
        sql = f'CREATE TABLE IF NOT EXISTS {table_name} ({column_placeholders});'

        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
        except Error as e:
            print(e)

    def remove_billable_position(self, id: int):
        sql = '''
            DELETE FROM billing_positions
            WHERE id = ?
        '''

        cursor = self.connection.cursor()
        cursor.execute(sql, (id, ))
        self.connection.commit()

    def add_billing_position(self,
        date: datetime,
        file: str,
        hourly_rate: float,
        billed_hours: float,
        billed_amount: float,
        earned_amount: float,
        ) -> None:

        sql = '''
            INSERT INTO billing_positions (date, file, hourly_rate, billed_hours, billed_amount, earned_amount)
            VALUES (?, ?, ?, ?, ?, ?);
        '''
        cursor = self.connection.cursor()
        cursor.execute(sql, (date.date().strftime('%Y%m%d'), file, hourly_rate, billed_hours, billed_amount, earned_amount))
        self.connection.commit()
        # return cursor.lastrowid
    
    def update_billing_position(self,
        id: int,
        date: datetime,
        file: str,
        hourly_rate: float,
        billed_hours: float,
        billed_amount: float,
        earned_amount: float,
        invoiced_amount: float
        ) -> None:
        sql = '''
            UPDATE billing_positions
            SET date = ?, file = ?, hourly_rate = ?, billed_hours = ?, billed_amount = ?, earned_amount = ?, invoiced_amount = ?
            WHERE id = ?;
        '''

        cursor = self.connection.cursor()
        cursor.execute(sql, (date.date().strftime('%Y%m%d'), file, hourly_rate, billed_hours, billed_amount, earned_amount, invoiced_amount, id))
        self.connection.commit()

    def get_billing_position(self, id: int) -> dict | None:
        sql = '''
            SELECT id, date, file, hourly_rate, billed_hours, billed_amount, earned_amount, invoiced_amount, invoice_id
            FROM billing_positions
            WHERE id = ?
        '''
        cursor = self.connection.cursor()
        cursor.execute(sql, (id, ))
        rows = cursor.fetchall()

        if len(rows) != 1:
            return None
        
        return {
            'id': int(rows[0][0]),
            'date': datetime.strptime(str(rows[0][1]), '%Y%m%d').date(),
            'file': rows[0][2],
            'hourly_rate': optional_float(rows[0][3]),
            'billed_hours': optional_float(rows[0][4]),
            'billed_amount': optional_float(rows[0][5]),
            'earned_amount': optional_float(rows[0][6]),
            'invoiced_amount': optional_float(rows[0][7]),
            'invoice_id': optional_int(rows[0][8])
        }

    def get_all_billing_positions(self) -> list:
        sql = '''
            SELECT id, date, file
            FROM billing_positions
            '''
        cursor = self.connection.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()

        billing_positions = []
        for row in rows:
            billing_positions.append({
                "id": int(row[0]),
                "date": datetime.strptime(str(row[1]), '%Y%m%d').date(),
                "file": row[2]
            })

        return billing_positions
    
    def get_open_billing_positions(self, file: str = None) -> list:

        cursor = self.connection.cursor()

        if file is not None:
            sql = '''
                SELECT id, date, file, earned_amount
                FROM billing_positions
                WHERE invoice_id IS NULL AND file = ?
                ORDER BY date;
            '''
            cursor.execute(sql, (file, ))
        else:
            sql = '''
                SELECT id, date, file, earned_amount
                FROM billing_positions
                WHERE invoice_id IS NULL
                ORDER BY date;
            '''
            cursor.execute(sql,)

        rows = cursor.fetchall()

        open_billing_positions = []
        for row in rows:
            open_billing_positions.append({
                'id': row[0],
                'date': datetime.strptime(str(row[1]), '%Y%m%d').date(),
                'file': row[2],
                'earned_amount': row[3]
            })

        return open_billing_positions

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

        cursor = self.connection.cursor()
        cursor.execute(sql, (invoiced_amount, invoice_id, id))
        self.connection.commit()

    def add_invoice(self, date: datetime) -> int:
        sql = 'INSERT INTO invoices (date) VALUES (?);'
        cursor = self.connection.cursor()
        cursor.execute(sql, (date.date().strftime('%Y%m%d'), ))
        self.connection.commit()
        
        return cursor.lastrowid

    def get_all_invoices(self) -> list:
        sql = '''
            SELECT invoices.id, invoices.date, sum(billing_positions.invoiced_amount)
            FROM invoices
            LEFT OUTER JOIN billing_positions ON invoices.id = billing_positions.invoice_id
            GROUP BY invoices.id
            ORDER BY invoices.date;
        '''
        cursor = self.connection.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()

        invoices = []
        for row in rows:
            total = 0.0 if row[2] is None else row[2]
            invoices.append({
                'id': int(row[0]),
                'date': datetime.strptime(str(row[1]), '%Y%m%d').date(),
                'total': round(total, 2)
            })

        return invoices