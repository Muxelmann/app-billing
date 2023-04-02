import os
from app import make_app

secret_key = os.environ.get("FLASK_SECRET", "_DEFAULT_SECRET_")
app = make_app(secret_key)

if __name__ == "__main__":
    app.run(debug=True)
