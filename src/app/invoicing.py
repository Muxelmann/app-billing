from datetime import datetime
from flask import Flask, Blueprint, render_template, current_app, request, url_for, redirect, flash, abort
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

        if request.method == 'GET':
            return render_template(
                'invoicing/invoice.html.jinja2',
                invoice_id=invoice_id
            )
        
        file = request.form.get('file')
        database = DB(current_app)
        if file is not None:
            open_billing_positions = database.get_open_billing_positions(file.replace(' ', ''))
            return render_template(
                'invoicing/invoice.html.jinja2',
                invoice_id=invoice_id,
                open_billing_positions=open_billing_positions
            )

        invoice_amount = optional_float(request.form.get('invoice_amount'))

        if invoice_amount is None:
            flash(('error', f'Amount for invoice not valid.'))
            redirect(url_for('.invoice', invoice_id=invoice_id))

        billing_position_ids_to_invoice = [int(id) for id in request.form.getlist('billing_position_id[]')]
        for index, billing_position_id in enumerate(billing_position_ids_to_invoice):
            if index < len(billing_position_ids_to_invoice) - 1:
                database.invoice_billing_position(billing_position_id, 0.0, invoice_id)
            else:
                database.invoice_billing_position(billing_position_id, invoice_amount, invoice_id)
                flash(('info', f'Successfully invoiced an amount of {invoice_amount}.'))
        return redirect(url_for('.invoice', invoice_id=invoice_id))

    @bp.route('/remove/<int:invoice_id>', methods=['GET', 'POST'])
    def remove(invoice_id: int):
        database = DB(current_app)

        if request.method == 'GET':
            return render_template(
                'invoicing/remove.html.jinja2',
                invoice=database.get_invoice(invoice_id)
            )
    
        if request.form.get('confirmation') != 'yes':
            flash(('error', 'Removing not confirmed properly'))
            return redirect(url_for('.remove', invoice_id=invoice_id))
        
        database.remove_invoice(invoice_id)
        flash(('info', 'Successfully removed invoice'))
        return redirect(url_for('.home'))

    @bp.route('/edit/<int:invoice_id>', methods=['GET', 'POST'])
    def edit(invoice_id: int):

        database = DB(current_app)

        if request.method == 'GET':
            invoice = database.get_invoice(invoice_id)
            return render_template(
                'invoicing/edit.html.jinja2',
                invoice=invoice,
                invoiced_billing_positions=database.get_invoiced_billing_positions(invoice_id)
            )
        
        date = request.form.get('date')

        try:
            date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError as e: 
            flash(('error', f'The date of {date} is incorrect'))
            return redirect(url_for('.add'))

        billing_position_ids = request.form.getlist('billing_position_ids[]')
        billing_position_invoiced_amounts = request.form.getlist('billing_position_invoiced_amounts[]')

        for billing_position_id, billing_position_invoiced_amount in zip(billing_position_ids, billing_position_invoiced_amounts):
            database.invoice_billing_position(billing_position_id, billing_position_invoiced_amount, invoice_id)

        flash(('info', f'Successfully edited invoice {invoice_id}'))
        return redirect(url_for('.home'))
    
    app.register_blueprint(bp)