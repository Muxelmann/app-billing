from datetime import datetime
from flask import Flask, Blueprint, render_template, request, redirect, url_for, flash, current_app
from .db import DB
from .utils import optional_float

def register(app: Flask) -> None:

    bp = Blueprint('billing', __name__, url_prefix='/billing')

    @bp.route('/')
    def home():
        database = DB(current_app)

        return render_template(
            'billing/home.html.jinja2',
            billing_positions = database.get_all_billing_positions()
            )

    @bp.route('/edit/<int:billing_position_id>', methods=['GET', 'POST'])
    def edit(billing_position_id: int):
        database = DB(current_app)

        if request.method == 'GET':
            return render_template(
                'billing/edit.html.jinja2',
                billing_position=database.get_billing_position(billing_position_id)
            )
        
        date = request.form.get('date')

        try:
            date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError as e: 
            flash(('error', f'The date of {date} is incorrect'))
            return redirect(url_for('.edit'))

        file = request.form.get('file').replace(' ', '')
        hourly_rate = optional_float(request.form.get('hourly_rate'))
        billed_hours = optional_float(request.form.get('billed_hours'))
        billed_amount = None
        earned_percentage = optional_float(request.form.get('earned_percentage'))
        earned_amount = optional_float(request.form.get('earned_amount'))
        invoiced_amount = optional_float(request.form.get('invoiced_amount'))

        if not isinstance(earned_amount, float):
            if not all([v is not None for v in (hourly_rate, billed_hours, earned_percentage)]):
                flash(('error', 'The entry contains errors. Please provice either an Earned Amount or the combination of Rate, Hours and Percentage.'))
                return redirect(url_for('.edit', billing_position_id=billing_position_id))
            
            billed_amount = hourly_rate * billed_hours
            earned_amount = billed_amount * earned_percentage / 100.0

        database = DB(current_app)
        database.update_billing_position(billing_position_id, date, file, hourly_rate, billed_hours, billed_amount, earned_amount, invoiced_amount)

        flash(('info', f'Sucessfully edited billing position for file {file}.'))
        return redirect(url_for('.edit', billing_position_id=billing_position_id))

    @bp.route('/remove/<int:billing_position_id>', methods=['GET', 'POST'])
    def remove(billing_position_id: int):
        database = DB(current_app)
        
        if request.method == 'GET':
            return render_template(
                'billing/remove.html.jinja2',
                billing_position=database.get_billing_position(billing_position_id)
            )
        
        if request.form.get('confirmation') != 'yes':
            flash(('error', 'Removing not confirmed properly'))
            return redirect(url_for('.remove', billing_position_id=billing_position_id))

        database.remove_billable_position(billing_position_id)
        flash(('info', 'Successfully removed billing position'))
        return redirect(url_for('.home'))

    @bp.route('/add', methods=['GET', 'POST'])
    def add():
        if request.method == 'GET':
            return render_template('billing/add.html.jinja2')
        
        date = request.form.get('date')

        try:
            date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError as e: 
            flash(('error', f'The date of {date} is incorrect'))
            return redirect(url_for('.add'))

        file = request.form.get('file').replace(' ', '')
        hourly_rate = optional_float(request.form.get('hourly_rate'))
        billed_hours = optional_float(request.form.get('billed_hours'))
        billed_amount = None
        earned_percentage = optional_float(request.form.get('earned_percentage'))
        earned_amount = optional_float(request.form.get('earned_amount'))

        if not isinstance(earned_amount, float):

            if not all([v is not None for v in (hourly_rate, billed_hours, earned_percentage)]):
                flash(('error', 'The entry contains errors. Please provice either an Earned Amount or the combination of Rate, Hours and Percentage.'))
                return redirect(url_for('.add'))
            
            billed_amount = hourly_rate * billed_hours
            earned_amount = billed_amount * earned_percentage / 100.0

        database = DB(current_app)
        database.add_billing_position(date, file, hourly_rate, billed_hours, billed_amount, earned_amount)

        flash(('info', f'Sucessfully billed for file {file}.'))
        return redirect(url_for('.add'))
    
    app.register_blueprint(bp)
