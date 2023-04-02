from datetime import datetime
from flask import Flask, Blueprint, render_template, current_app, request, url_for, redirect, flash
from .db import DB
from .utils import optional_float

def register(app: Flask) -> Blueprint:
    bp = Blueprint('invoicing', __name__, url_prefix='/invoicing')

    @bp.route('/')
    def home():
        database = DB(current_app)

        return render_template(
            'invoicing/home.html.jinja2',
            invoices = database.get_all_invoices()
        )

    @bp.route('/add', methods=['GET', 'POST'])
    def add():
        database = DB(current_app)

        if request.method == 'GET':
            return render_template('invoicing/add.html.jinja2')
        
        date = request.form.get('date')

        try:
            date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError as e: 
            flash(('error', f'The date of {date} is incorrect'))
            return redirect(url_for('.add'))
        
        invoice_id = database.add_invoice(date)
        return redirect(url_for('.invoice', invoice_id=invoice_id))

    @bp.route('/invoice/<int:invoice_id>', methods=['GET', 'POST'])
    def invoice(invoice_id: int):
        database = DB(current_app)

        if request.method == 'GET':
            return render_template(
                'invoicing/invoice.html.jinja2',
                invoice_id=invoice_id
            )
        
        file = request.form.get('file').replace(' ', '')
        invoice_amount = optional_float(request.form.get('invoice_amount'))

        if invoice_amount is None:
            flash(('error', f'Amount for invoice not valid.'))
            redirect(url_for('.invoice', invoice_id=invoice_id))

        database.invoice_billing_positions(file, invoice_amount, invoice_id)
        flash(('info', f'Successfully invoiced for file {file}.'))
        return redirect(url_for('.invoice', invoice_id=invoice_id))

    app.register_blueprint(bp)