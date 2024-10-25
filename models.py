from db import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    lastName = db.Column(db.String(100), nullable=False)
    firstName = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_manager = db.Column(db.Boolean, default = False)
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class TokenBlackList(db.Model):
    __tablename__ = 'token_black_list'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), unique=True, nullable=False)
    revoked = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self, jti):
        self.jti = jti
        self.revoked = True

class Doctor(db.Model):
    __tablename__ = 'doctors'

    id = db.Column(db.Integer, primary_key=True)
    fullName = db.Column(db.String(200), nullable=False)
    specialization = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(15), nullable=True)

    def __init__(self, fullName, specialization=None, phone=None):
        self.fullName = fullName
        self.specialization = specialization
        self.phone = phone

class Hospital(db.Model):
    __tablename__ = 'hospitals'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(100), nullable=False)
    contactPhone = db.Column(db.String(15), nullable=False)
    rooms_description = db.Column(db.String(100), nullable=False)
    is_deleted = db.Column(db.Boolean, default=False)

    def __init__(self, name, address, contactPhone, rooms_description, is_deleted):
        self.name = name
        self.address = address
        self.contactPhone = contactPhone
        self.rooms_description = rooms_description
        self.is_deleted = is_deleted

class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(10), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    hospitalId = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)

    hospital = db.relationship('Hospital', backref=db.backref('rooms', lazy=True))

    def __init__(self, number, type, hospital_id):
        self.number = number
        self.type = type
        self.hospital_id = hospital_id

class TimeTables(db.Model):
    __tablename__ = 'timetables'
    id = db.Column(db.Integer, primary_key=True)
    hospitalId = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    doctorId = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    from_time = db.Column(db.DateTime, nullable=False)
    to_time = db.Column(db.DateTime, nullable=False)
    room = db.Column(db.String(100), nullable=False)

    hospital = db.relationship('Hospital', backref='timetables')
    doctor = db.relationship('Doctor', backref='timetables')

    def __init__(self, hospital_id, doctor_id, from_time, to_time, room):
        self.hospital_id = hospital_id
        self.doctor_id = doctor_id
        self.from_time = from_time
        self.to_time = to_time
        self.room = room

    def __repr__(self):
        return f'<TimeTable {self.id}: {self.doctor_id} at {self.hospital_id} from {self.from_time} to {self.to_time}>'

class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetables.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    time = db.Column(db.DateTime, nullable=False)

    timetable = db.relationship('TimeTables', backref='appointments')
    user = db.relationship('User', backref='appointments')

    def __init__(self, timetable_id, user_id, time):
        self.timetable_id = timetable_id
        self.user_id = user_id
        self.time = time

    def __repr__(self):
        return f'<Appointment {self.id} for User {self.user_id} at {self.time}>'

class History(db.Model):
    __tablename__ = 'history'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    pacient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    room = db.Column(db.String(100), nullable=False)
    data = db.Column(db.String, nullable=False)

    pacient = db.relationship('User', backref='history')
    hospital = db.relationship('Hospital', backref='history')
    doctor = db.relationship('Doctor', backref='history')

    def __init__(self, date, pacient_id, hospital_id, doctor_id, room, data):
        self.date = date
        self.pacient_id = pacient_id
        self.hospital_id = hospital_id
        self.doctor_id = doctor_id
        self.room = room
        self.data = data

    def __repr__(self):
        return f'<History {self.id}: {self.pacient_id} on {self.date}>'
