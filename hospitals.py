from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity

from models import Hospital, Room
from db import db, init_app
from dotenv import load_dotenv
import os

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

@app.route('/api/Hospitals', methods=['GET'])
@jwt_required()
def get_hospitals():
    from_param = request.args.get('from', default=0, type=int)
    count_param = request.args.get('count', default=10, type=int)

    hospitals_query = Hospital.query.offset(from_param).limit(count_param)
    hospitals = hospitals_query.all()

    hospital_list = [{'id': hospital.id, 'name': hospital.name} for hospital in hospitals]

    return jsonify({'hospitals': hospital_list}), 200

@app.route('/api/Hospitals/<int:id>', methods=['GET'])
@jwt_required()
def get_hospital_by_id(id):
    hospital = Hospital.query.get(id)

    if not hospital:
        return jsonify({'error': 'Hospital not found'}), 404

    hospital_data = {
        'id': hospital.id,
        'name': hospital.name
    }

    return jsonify({'hospital': hospital_data}), 200

@app.route('/api/Hospitals/<int:id>/Rooms', methods=['GET'])
@jwt_required()
def get_rooms_by_hospital_id(id):

    hospital = Hospital.query.get(id)

    if not hospital:
        return jsonify({'error': 'Hospital not found'}), 404

    rooms = Room.query.filter_by(hospital_id=id).all()

    room_list = [{'id': room.id, 'number': room.number, 'type': room.type} for room in rooms]

    return jsonify({'rooms': room_list}), 200

@app.route('/api/Hospitals', methods=['POST'])
@jwt_required()
def create_hospital():
    current_user = get_jwt_identity()

    if not current_user.is_admin:
        return jsonify({'error': 'Access forbidden: Admins only'}), 403

    data = request.get_json()

    if not data or not all(key in data for key in ['name', 'address', 'contactPhone', 'rooms']):
        return jsonify({'error': 'Missing data'}), 400

    new_hospital = Hospital(
        name=data['name'],
        address=data['address'],
        contactPhone=data['contactPhone']
    )

    try:
        db.session.add(new_hospital)
        db.session.commit()

        for room_name in data['rooms']:
            new_room = Room(number=room_name, type='General', hospital_id=new_hospital.id)
            db.session.add(new_room)

        db.session.commit()

    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({'message': 'Hospital created successfully', 'id': new_hospital.id}), 201

@app.route('/api/Hospitals/<int:id>', methods=['PUT'])
@jwt_required()
def update_hospital(id):
    current_user = get_jwt_identity()

    if not current_user.is_admin:
        return jsonify({'error': 'Access forbidden: Admins only'}), 403

    hospital = Hospital.query.get(id)

    if not hospital:
        return jsonify({'error': 'Hospital not found'}), 404

    data = request.get_json()


    if not data or not all(key in data for key in ['name', 'address', 'contactPhone', 'rooms']):
        return jsonify({'error': 'Missing data'}), 400

    hospital.name = data['name']
    hospital.address = data['address']
    hospital.contactPhone = data['contactPhone']

    try:
        db.session.commit()

        Room.query.filter_by(hospital_id=hospital.id).delete()

        for room_name in data['rooms']:
            new_room = Room(number=room_name, type='General', hospital_id=hospital.id)  # Предполагаем, что все кабинеты общего типа
            db.session.add(new_room)

        db.session.commit()

    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({'message': 'Hospital updated successfully'}), 200

@app.route('/api/Hospitals/<int:id>', methods=['DELETE'])
@jwt_required()
def soft_delete_hospital(id):
    current_user = get_jwt_identity()

    if not current_user.is_admin:
        return jsonify({'error': 'Access forbidden: Admins only'}), 403

    hospital = Hospital.query.get(id)

    if not hospital:
        return jsonify({'error': 'Hospital not found'}), 404

    try:

        hospital.is_deleted = True
        db.session.commit()
    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({'message': 'Hospital soft deleted successfully'}), 200



if __name__ == '__main__':
    app.run(debug=True)