from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from models import TimeTables, Appointment
from db import db, init_app
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from sqlalchemy import or_

load_dotenv()

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['JWT_SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access']
jwt = JWTManager(app)

init_app(app)
with app.app_context():
    db.create_all()

@app.route('/api/Timetable', methods=['POST'])
@jwt_required()
def create_timetable_entry():
    current_user = get_jwt_identity()

    if not current_user.is_admin or not current_user.is_manager:
        return jsonify({'error': 'Access forbidden: Admins and Managers only'}), 403

    data = request.get_json()

    if not data or not all(key in data for key in ['hospitalId', 'doctorId', 'from', 'to', 'room']):
        return jsonify({'error': 'Missing data'}), 400

    try:
        from_time = datetime.fromisoformat(data['from'].replace('Z', '+00:00'))
        to_time = datetime.fromisoformat(data['to'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use ISO8601 format.'}), 400

    if to_time <= from_time:
        return jsonify({'error': '{to} must be greater than {from}'}), 400

    if (to_time - from_time).total_seconds() > 12 * 3600:
        return jsonify({'error': 'The time difference cannot exceed 12 hours'}), 400

    if from_time.minute % 30 != 0 or to_time.minute % 30 != 0:
        return jsonify({'error': '{from} and {to} must be multiples of 30 minutes'}), 400

    new_entry = TimeTables(
        hospital_id=data['hospitalId'],
        doctor_id=data['doctorId'],
        from_time=from_time,
        to_time=to_time,
        room=data['room']
    )

    try:
        db.session.add(new_entry)
        db.session.commit()
    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({'message': 'Timetable entry created successfully'}), 201

@app.route('/api/Timetable<int:id>', methods=['PUT'])
@jwt_required()
def update_timetable_entry(id):
    current_user = get_jwt_identity()

    if not current_user.is_admin or not current_user.is_manager:
        return jsonify({'error': 'Access forbidden: Admins and Managers only'}), 403

    data = request.get_json()

    if not data or not all(key in data for key in ['hospitalId', 'doctorId', 'from', 'to', 'room']):
        return jsonify({'error': 'Missing data'}), 400

    try:
        from_time = datetime.fromisoformat(data['from'].replace('Z', '+00:00'))
        to_time = datetime.fromisoformat(data['to'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use ISO8601 format.'}), 400

    if to_time <= from_time:
        return jsonify({'error': '{to} must be greater than {from}'}), 400

    if (to_time - from_time).total_seconds() > 12 * 3600:  # 12 часов в секундах
        return jsonify({'error': 'The time difference cannot exceed 12 hours'}), 400

    if from_time.minute % 30 != 0 or to_time.minute % 30 != 0:
        return jsonify({'error': '{from} and {to} must be multiples of 30 minutes'}), 400

    timetable_entry = TimeTables.query.get(id)
    if not timetable_entry:
        return jsonify({'error': 'Timetable entry not found'}), 404

    conflicting_entries = TimeTables.query.filter(
        TimeTables.doctorId == timetable_entry.doctorId,
        TimeTables.hospitalId == timetable_entry.hospitalId,
        or_(
            (TimeTables.from_time < to_time) & (TimeTables.to_time > from_time)
        )
    ).all()

    if conflicting_entries:
        return jsonify({'error': 'Cannot update: There are existing appointments during this time.'}), 400

    timetable_entry.hospitalId = data['hospitalId']
    timetable_entry.doctorId = data['doctorId']
    timetable_entry.from_time = from_time
    timetable_entry.to_time = to_time
    timetable_entry.room = data['room']

    try:
        db.session.commit()
    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({'message': 'Timetable entry updated successfully'}), 200


@app.route('/api/Timetable/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_timetable_entry(id):
    current_user = get_jwt_identity()
    if not current_user.is_admin or not current_user.is_manager:
        return jsonify({'error': 'Access forbidden: Admins and Managers only'}), 403

    timetable_entry = TimeTables.query.get(id)
    if not timetable_entry:
        return jsonify({'error': 'Timetable entry not found'}), 404

    db.session.delete(timetable_entry)
    db.session.commit()

    return jsonify({'message': 'Timetable entry deleted successfully'}), 204


@app.route('/api/Timetable/Doctor/<int:doctor_id>', methods=['DELETE'])
@jwt_required()
def delete_timetable_for_doctor(doctor_id):
    current_user = get_jwt_identity()
    if not current_user.is_admin or not current_user.is_manager:
        return jsonify({'error': 'Access forbidden: Admins and Managers only'}), 403

    deleted_entries = TimeTables.query.filter_by(doctorId=doctor_id).all()
    if not deleted_entries:
        return jsonify({'error': 'No timetable entries found for this doctor'}), 404

    for entry in deleted_entries:
        db.session.delete(entry)

    db.session.commit()

    return jsonify({'message': 'Timetable entries for doctor deleted successfully'}), 204

@app.route('/api/Timetable/Hospital/<int:hospital_id>', methods=['DELETE'])
@jwt_required()
def delete_timetable_for_hospital(hospital_id):
    current_user = get_jwt_identity()
    if not current_user.is_admin or not current_user.is_manager:
        return jsonify({'error': 'Access forbidden: Admins and Managers only'}), 403

    deleted_entries = TimeTables.query.filter_by(hospitalId=hospital_id).all()
    if not deleted_entries:
        return jsonify({'error': 'No timetable entries found for this hospital'}), 404

    for entry in deleted_entries:
        db.session.delete(entry)

    db.session.commit()

    return jsonify({'message': 'Timetable entries for hospital deleted successfully'}), 204

@app.route('/api/Timetable/Hospital/<int:hospital_id>', methods=['GET'])
@jwt_required()
def get_hospital_timetable(hospital_id):
    current_user = get_jwt_identity()

    from_time = request.args.get('from')
    to_time = request.args.get('to')

    if not from_time or not to_time:
        return jsonify({'error': 'Missing from or to parameters'}), 400

    try:
        from_time = datetime.fromisoformat(from_time.replace('Z', '+00:00'))
        to_time = datetime.fromisoformat(to_time.replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use ISO8601 format.'}), 400

    timetable_entries = TimeTables.query.filter(
        TimeTables.hospitalId == hospital_id,
        TimeTables.from_time >= from_time,
        TimeTables.to_time <= to_time
    ).all()

    return jsonify([entry.to_dict() for entry in timetable_entries]), 200

@app.route('/api/Timetable/Doctor/<int:doctor_id>', methods=['GET'])
@jwt_required()
def get_doctor_timetable(doctor_id):
    current_user = get_jwt_identity()

    from_time = request.args.get('from')
    to_time = request.args.get('to')

    if not from_time or not to_time:
        return jsonify({'error': 'Missing from or to parameters'}), 400

    try:
        from_time = datetime.fromisoformat(from_time.replace('Z', '+00:00'))
        to_time = datetime.fromisoformat(to_time.replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use ISO8601 format.'}), 400

    timetable_entries = TimeTables.query.filter(
        TimeTables.doctorId == doctor_id,
        TimeTables.from_time >= from_time,
        TimeTables.to_time <= to_time
    ).all()

    return jsonify([entry.to_dict() for entry in timetable_entries]), 200

@app.route('/api/Timetable/Hospital/<int:hospital_id>/Room/<string:room>', methods=['GET'])
@jwt_required()
def get_hospital_room_timetable(hospital_id, room):
    current_user = get_jwt_identity()

    if not current_user.is_admin or not current_user.is_manager:
        return jsonify({'error': 'Access forbidden: Admins, Managers, and Doctors only'}), 403

    from_time = request.args.get('from')
    to_time = request.args.get('to')

    if not from_time or not to_time:
        return jsonify({'error': 'Missing from or to parameters'}), 400

    try:
        from_time = datetime.fromisoformat(from_time.replace('Z', '+00:00'))
        to_time = datetime.fromisoformat(to_time.replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use ISO8601 format.'}), 400

    timetable_entries = TimeTables.query.filter(
        TimeTables.hospitalId == hospital_id,
        TimeTables.room == room,
        TimeTables.from_time >= from_time,
        TimeTables.to_time <= to_time
    ).all()

    return jsonify([entry.to_dict() for entry in timetable_entries]), 200

@app.route('/api/Timetable/<int:id>/Appointments', methods=['GET'])
@jwt_required()
def get_free_appointments(id):
    current_user = get_jwt_identity()

    timetable_entry = TimeTables.query.get(id)
    if not timetable_entry:
        return jsonify({'error': 'Timetable entry not found'}), 404

    available_times = []
    current_time = timetable_entry.from_time

    while current_time < timetable_entry.to_time:
        available_times.append(current_time.isoformat() + 'Z')
        current_time += timedelta(minutes=30)

    return jsonify(available_times), 200

@app.route('/api/Timetable/<int:id>/Appointments', methods=['POST'])
@jwt_required()
def book_appointment(id):
    current_user = get_jwt_identity()
    user_id = current_user['id']

    data = request.get_json()
    if not data or 'time' not in data:
        return jsonify({'error': 'Missing time parameter'}), 400

    try:
        appointment_time = datetime.fromisoformat(data['time'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use ISO8601 format.'}), 400

    timetable_entry = TimeTables.query.get(id)
    if not timetable_entry:
        return jsonify({'error': 'Timetable entry not found'}), 404

    existing_appointment = Appointment.query.filter_by(timetable_id=id, time=appointment_time).first()
    if existing_appointment:
        return jsonify({'error': 'This appointment time is already booked'}), 409

    new_appointment = Appointment(
        timetable_id=id,
        user_id=user_id,
        time=appointment_time
    )

    try:
        db.session.add(new_appointment)
        db.session.commit()
    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({'message': 'Appointment booked successfully', 'appointment_id': new_appointment.id}), 201

@app.route('/api/Appointment/<int:id>', methods=['DELETE'])
@jwt_required()
def cancel_appointment(id):
    current_user = get_jwt_identity()
    user_id = current_user['id']

    appointment = Appointment.query.get(id)
    if not appointment:
        return jsonify({'error': 'Appointment not found'}), 404

    if appointment.user_id != user_id and not current_user.is_admin or not current_user.is_manager:
        return jsonify({'error': 'Access forbidden: You can only cancel your own appointments'}), 403

    try:
        db.session.delete(appointment)
        db.session.commit()
    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({'message': 'Appointment canceled successfully'}), 204


if __name__ == '__main__':
    app.run(debug=True)