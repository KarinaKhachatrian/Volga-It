from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from models import History
from db import db, init_app
from dotenv import load_dotenv
import os
from datetime import datetime

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

@app.route('/api/History/Account/<int:id>', methods=['GET'])
@jwt_required()
def get_account_history(id):
    current_user = get_jwt_identity()
    if 'doctor' not in current_user['roles'] and current_user['id'] != id:
        return jsonify({'error': 'Access forbidden: Only doctors or the account owner can access this history'}), 403

    history_records = History.query.filter_by(pacient_id=id).all()
    return jsonify([{
        'id': record.id,
        'date': record.date.isoformat(),
        'hospitalId': record.hospital_id,
        'doctorId': record.doctor_id,
        'room': record.room,
        'data': record.data
    } for record in history_records]), 200

@app.route('/api/History/<int:id>', methods=['GET'])
@jwt_required()
def get_history_detail(id):
    current_user = get_jwt_identity()
    history_record = History.query.get(id)

    if not history_record:
        return jsonify({'error': 'History record not found'}), 404

    if 'doctor' not in current_user['roles'] and current_user['id'] != history_record.pacient_id:
        return jsonify({'error': 'Access forbidden: Only doctors or the account owner can access this history'}), 403

    return jsonify({
        'id': history_record.id,
        'date': history_record.date.isoformat(),
        'pacientId': history_record.pacient_id,
        'hospitalId': history_record.hospital_id,
        'doctorId': history_record.doctor_id,
        'room': history_record.room,
        'data': history_record.data
    }), 200

@app.route('/api/History', methods=['POST'])
@jwt_required()
def create_history():
    current_user = get_jwt_identity()

    if 'admin' not in current_user['roles'] and 'manager' not in current_user['roles'] and 'doctor' not in current_user['roles']:
        return jsonify({'error': 'Access forbidden: Only admins, managers, or doctors can create history records'}), 403

    data = request.get_json()

    if not data or not all(key in data for key in ['date', 'pacientId', 'hospitalId', 'doctorId', 'room', 'data']):
        return jsonify({'error': 'Missing data'}), 400

    try:
        date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use ISO8601 format.'}), 400

    new_history = History(
        date=date,
        pacient_id=data['pacientId'],
        hospital_id=data['hospitalId'],
        doctor_id=data['doctorId'],
        room=data['room'],
        data=data['data']
    )

    try:
        db.session.add(new_history)
        db.session.commit()
    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({'message': 'History record created successfully', 'history_id': new_history.id}), 201

@app.route('/api/History/<int:id>', methods=['PUT'])
@jwt_required()
def update_history(id):
    current_user = get_jwt_identity()
    history_record = History.query.get(id)

    if not history_record:
        return jsonify({'error': 'History record not found'}), 404

    if 'admin' not in current_user['roles'] and 'manager' not in current_user['roles'] and 'doctor' not in current_user['roles']:
        return jsonify({'error': 'Access forbidden: Only admins, managers, or doctors can update history records'}), 403

    data = request.get_json()

    if not data or not all(key in data for key in ['date', 'pacientId', 'hospitalId', 'doctorId', 'room', 'data']):
        return jsonify({'error': 'Missing data'}), 400

    try:
        date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use ISO8601 format.'}), 400

    history_record.date = date
    history_record.pacient_id = data['pacientId']
    history_record.hospital_id = data['hospitalId']
    history_record.doctor_id = data['doctorId']
    history_record.room = data['room']
    history_record.data = data['data']

    try:
        db.session.commit()
    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({'message': 'History record updated successfully'}), 200

if __name__ == '__main__':
    app.run(debug=True)