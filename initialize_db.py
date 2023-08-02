from models import db
from __init__ import createApp


def createDB():
    app = createApp()
    with app.app_context():
        db.create_all()

