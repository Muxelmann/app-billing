import os
from flask import Flask, render_template, current_app, request, redirect, url_for, flash
from .db import DB

def make_app(secret_key: str) -> Flask:

    app = Flask(__name__)
    app.secret_key = secret_key.encode('utf-8')

    if not os.path.exists(app.instance_path):
        os.mkdir(app.instance_path)

    from . import billing
    billing.register(app)

    from . import invoicing
    invoicing.register(app)

    @app.route('/')
    def home():
        database = DB(current_app)

        return render_template(
            'home.html.jinja2',
            statistics=database.get_statistics()
        )

    @app.route('/backup', methods=['GET', 'POST'])
    def backup():
        if request.method == 'POST':
            database = DB(current_app)
            if not database.backup():
                flash(('error', 'DB backup failed (you can only backup every 30 minutes).'))
        return redirect(url_for('home'))
        

    return app
