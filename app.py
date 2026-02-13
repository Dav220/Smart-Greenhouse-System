# Using flask to make an api
# import necessary libraries and functions
from flask import Flask, jsonify, request, render_template, session, redirect, copy_current_request_context
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select
from flask_restful import Api, reqparse, marshal_with, abort, Resource, fields
from flask_socketio import SocketIO, send, emit
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, apology
from datetime import datetime
import serial
import threading
from dataclasses import dataclass




# creating a Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensor_database.db'
# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
API_KEY = "..." # Write API key here
db = SQLAlchemy(app)
api = Api(app)
# Currently using * for development. For production, change it to the page of the frontend.
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True) 

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

# Handling Websocket Layer connections and disconnections
@socketio.on("connect")
def on_connect():
    print("A client connected")

@socketio.on("disconnect")
def on_disconnect():
    print("A client disconnected")



@dataclass
class ReadingModel(db.Model):
    id:int = db.Column(db.Integer, primary_key=True)
    temp:float = db.Column(db.Float)
    hum:float = db.Column(db.Float)
    moist:int = db.Column(db.Integer)
    time:datetime = db.Column(db.DateTime)
    user:str = db.Column(db.String)


@dataclass
class Users(db.Model):
    
    id:int = db.Column(db.Integer, primary_key=True)
    username:str = db.Column(db.String, unique=True, nullable=False)
    email:str = db.Column(db.String, unique=True, nullable=False)
    hash:str = db.Column(db.String, unique=True, nullable=False)


with app.app_context():
    db.create_all()

sensor_args = reqparse.RequestParser()
sensor_args.add_argument('temp', type = float, required = True)
sensor_args.add_argument('hum', type = float, required = True)
sensor_args.add_argument('moist', type = int, required = True)

sensorFields = {
    'id': fields.Integer,
    'temp': fields.Float,
    'hum': fields.Float,
    'moist': fields.Integer,
    'time': fields.DateTime,
    'user': fields.String
}



class Readings(Resource):
    @login_required
    def get(self):
        if "user_id" in session and "username" in session:
            user = db.session.execute(select(Users).where(Users.username == session["username"])).scalars().first()
            readings = ReadingModel.query.filter_by(user=session["username"]).all()
            return jsonify(readings)
        
        return apology("No users yet", 403)
        
    
    @login_required
    def post(self):
        key = request.headers.get('x-api-key')
        if key != API_KEY:
            abort(403)  # Forbidden
        
        args = sensor_args.parse_args()

        # Query database for username
        user_id = session["user_id"]
        

        reading = ReadingModel(temp=args["temp"], hum=args["hum"], moist=args["moist"], time=args["time"], user=args["user"])
        db.session.add(reading)
        db.session.commit()
        
        socketio.emit("readings_update",args)
        readings = ReadingModel.query.all()

        return readings, 201


    
api.add_resource(Readings, "/readings")
    


# arduino board that would feed sensor data to database and client
arduino = serial.Serial('...', 9600) # Defining the arduino board connection. Find it using the Arduino IDE

user_threads = {} #Grants us access to the threads for users

    






def readData(arduino,username, stop_event, db):
        #with app.test_request_context():
        with app.app_context():
            while not stop_event.is_set():
                if arduino.readable():
                    # Reads from the sensor
                    temp = float(arduino.readline())
                    hum = float(arduino.readline())
                    moist = int(arduino.readline())
                    date = datetime.now()
                    data = {'temp':temp, 'hum':hum, 'moist':moist, 'time':date.isoformat()}
                    print(f"Temperature: {temp}, Humidity: {hum}, Moisture Level: {moist}, Date and time: {date.ctime()}")
                                
                    # Adds a new reading to the database
                    reading = ReadingModel(temp=temp, hum=hum, moist=moist, time=date, user=username)
                    socketio.emit("readings_update",data)

                    @socketio.on("confirmation")
                    def handle_confirmation(return_data):
                        with app.app_context():
                            if (return_data['add_to_db']):
                                db.session.add(reading)
                                db.session.commit()
                            
                                    
                else:
                    print("No data avaialble")

@socketio.on('watering')
def handle_watering(data):
    status = 0
    if data['status']:
        status = '1'
    else:
        status = '0'

    arduino.write((status + '\n').encode())
    print("Watering data sent!")


@app.route('/', methods = ['GET', 'POST'])
@login_required
def home():
    
    if request.method == 'GET':
        return render_template("index.html")
    




        
    
    
@app.route('/register', methods = ['GET', 'POST'])
def register():
    if (request.method == 'GET'):
        return render_template("register.html")
    
    elif request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")
        confirmation = request.form.get("confirmation")

        # Making sure username and password are both submitted
        if not username or not password or not confirmation or not email:
            return apology("Must enter username, email, and password", 403)
        
        if (password != confirmation):
            return apology("Passwords don't match", 403)
        
        
        # Query database for username
        rows = db.session.execute(select(Users).where(Users.username == username)).scalars().first()

        if rows != None:
            return apology("Username already taken!", 403)
        password_hash = generate_password_hash(password)

        rows_email = db.session.execute(select(Users).where(Users.email == email)).scalars().first()

        if rows_email != None:
            return apology("Emai; already taken!", 403)
        
        new_user = Users(username=username, email=email, hash=password_hash)
        db.session.add(new_user)
        db.session.commit()
        user = db.session.execute(select(Users).where(Users.username == username)).scalars().first()

        session.clear()
        
        # session["user_id"] = user.id
        # session["username"] = username
        return redirect("/")
    
@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    
    elif request.method == 'POST':
         #Logging the user in
        # if session["username"] in user_threads:
        #     thread, stop_event = user_threads.pop(session["username"])
        #     stop_event.set()
        #     thread.join()

        session.clear() # forgetting any user_id
        

        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return apology("Must enter username and password!", 403)
        
        # Query database for username
        rows = db.session.execute(select(Users).where(Users.username == username)).scalars().first()
        #rows = db.session.execute(text("SELECT * FROM users WHERE"))
        # Ensure username exists and password is correct
        if rows == None or not check_password_hash(rows.hash, password):
            return apology("invald username and/or password", 403)
        
        else:
            session["user_id"] = rows.id
            session["username"] = username
            
            if session["user_id"]:
                stop_event = threading.Event() # Allows thread to stop running
                thread = threading.Thread(target=readData, args=(arduino,session["username"], stop_event,db,)) # Creates the thread
                thread.daemon = True  # allows program to exit even if thread is running
                thread.start()
                user_threads[session["username"]] = (thread,stop_event)
                            
            else:
                print("Error: no session username")
                exit              
        
        return redirect("/")

@app.route('/logout')
def logout():
        if session["username"] in user_threads:
            thread, stop_event = user_threads.pop(session["username"])
            stop_event.set()
            thread.join()

        session.clear()
        
        return redirect("/")
    


# driver function
if __name__ == '__main__':
    # app.run(debug = True)
    socketio.run(app, debug=True)
