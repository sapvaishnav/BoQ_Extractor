from flask import Flask
from routes.boq_routes import boq_bp
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Register Blueprint
app.register_blueprint(boq_bp)

if __name__ == '__main__':
    app.run(debug=True, port=5050)
