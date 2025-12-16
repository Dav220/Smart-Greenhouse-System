from api import app, db

def new_func():
    with app.app_context():
        db.create_all()

new_func()
