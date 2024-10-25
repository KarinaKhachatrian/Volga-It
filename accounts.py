from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt, create_refresh_token, get_jwt_identity
from models import User, TokenBlackList, Doctor
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

def check_token_blacklist(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    return TokenBlackList.query.filter_by(jti=jti, revoked=True).first() is not None


@app.route('/api/Authentication/SignUp', methods=['POST'])
def register():
    data = request.get_json()

    if not data or not all(key in data for key in ['lastName', 'firstName', 'username', 'password']):
        return jsonify({'error': 'Missing data'}), 400


    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'User already exists'}), 400

    new_user = User(
        lastName=data['lastName'],
        firstName=data['firstName'],
        username=data['username']
    )
    new_user.set_password(data['password'])

    try:
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({'message': 'User created successfully'}), 201

@app.route('/api/Authentication/SignIn', methods=['POST'])
def login():
    data = request.get_json()

    if not data or not all(key in data for key in ['username', 'password']):
        return jsonify({'error': 'Missing data'}), 400

    user = User.query.filter_by(username=data['username']).first()

    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid username or password'}), 401


    access_token = create_access_token(identity=user.username)
    return jsonify({'access_token': access_token}), 200

@app.route('/api/Authentication/SignOut', methods=['PUT'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']
    blacklisted_token = TokenBlackList(jti=jti)

    db.session.add(blacklisted_token)
    db.session.commit()

    return jsonify({'message': 'User logged out successfully'}), 200

@app.route('/api/Authentication/Validate', methods=['GET'])
@jwt_required()
def validate_token():
    jwt_data = get_jwt()
    return jsonify({
        'message': 'Token is valid',
        'token_data': jwt_data
    }), 200

@app.route('/api/Authentication/Refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    new_refresh_token = create_refresh_token(identity=current_user)

    return jsonify({
        'access_token': new_access_token,
        'refresh_token': new_refresh_token
    }), 200


@app.route('/api/Accounts/Me', methods=['GET'])
@jwt_required()
def get_current_account():
    current_username = get_jwt_identity()

    user = User.query.filter_by(username=current_username).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'lastName': user.lastName,
        'firstName': user.firstName,
        'username': user.username
    }), 200

@app.route('/api/Accounts/Update', methods=['PUT'])
@jwt_required()
def update_account():
    current_username = get_jwt_identity()
    user = User.query.filter_by(username=current_username).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'lastName' in data and data['lastName']:
        user.lastName = data['lastName']

    if 'firstName' in data and data['firstName']:
        user.firstName = data['firstName']

    if 'password' in data and data['password']:
        user.set_password(data['password'])

    try:
        db.session.commit()
    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({'message': 'Account updated successfully'}), 200

@app.route('/api/Accounts', methods=['GET'])
@jwt_required()
def get_all_accounts():
    current_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_username).first()

    if not current_user or not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403

    from_index = request.args.get('from', default=0, type=int)
    count = request.args.get('count', default=10, type=int)

    users = User.query.offset(from_index).limit(count).all()

    users_data = [
        {
            'id': user.id,
            'lastName': user.lastName,
            'firstName': user.firstName,
            'username': user.username,
            'is_admin': user.is_admin
        } for user in users
    ]

    return jsonify(users_data), 200

@app.route('/api/Accounts', methods=['POST'])
@jwt_required()
def create_account():
    current_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_username).first()

    if not current_user or not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403

    data = request.get_json()

    if not data or not all(key in data for key in ['lastName', 'firstName', 'username', 'password', 'roles']):
        return jsonify({'error': 'Missing data'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'User already exists'}), 400

    new_user = User(
        lastName=data['lastName'],
        firstName=data['firstName'],
        username=data['username'],
        is_admin='admin' in data['roles']
    )
    new_user.set_password(data['password'])

    try:
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({'message': 'Account created successfully'}), 201

@app.route('/api/Accounts/<int:id>', methods=['PUT'])
@jwt_required()
def update_account_by_admin(id):
    current_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_username).first()

    if not current_user or not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403

    user = User.query.get(id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'lastName' in data and data['lastName']:
        user.lastName = data['lastName']

    if 'firstName' in data and data['firstName']:
        user.firstName = data['firstName']

    if 'username' in data and data['username']:

        if User.query.filter_by(username=data['username']).first() and user.username != data['username']:
            return jsonify({'error': 'Username already exists'}), 400
        user.username = data['username']

    if 'password' in data and data['password']:
        user.set_password(data['password'])

    if 'roles' in data and isinstance(data['roles'], list):
        user.is_admin = 'admin' in data['roles']

    try:
        db.session.commit()
    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({'message': 'Account updated successfully'}), 200

@app.route('/api/Accounts/<int:id>', methods=['DELETE'])
@jwt_required()
def soft_delete_account(id):
    current_username = get_jwt_identity()
    current_user = User.query.filter_by(username=current_username).first()

    if not current_user or not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403

    user = User.query.get(id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if not user.is_active:
        return jsonify({'error': 'User is already deleted'}), 400

    user.is_active = False

    try:
        db.session.commit()
    except Exception as e:
        return jsonify({'error': 'Database error', 'details': str(e)}), 500

    return jsonify({'message': 'Account soft deleted successfully'}), 200

@app.route('/api/Doctors', methods=['GET'])
@jwt_required()
def get_doctors():
    name_filter = request.args.get('nameFilter', '')
    from_param = request.args.get('from', default=0, type=int)
    count_param = request.args.get('count', default=10, type=int)

    doctors_query = Doctor.query.filter(Doctor.fullName.ilike(f'%{name_filter}%'))

    doctors = doctors_query.offset(from_param).limit(count_param).all()

    doctor_list = [{'id': doctor.id, 'fullName': doctor.fullName} for doctor in doctors]

    return jsonify({'doctors': doctor_list}), 200

@app.route('/api/Doctors/<int:id>', methods=['GET'])
@jwt_required()
def get_doctor_by_id(id):
    doctor = Doctor.query.get(id)

    if not doctor:
        return jsonify({'error': 'Doctor not found'}), 404

    doctor_data = {
        'id': doctor.id,
        'fullName': doctor.fullName,
        'specialization': doctor.specialization,
        'phone': doctor.phone
    }

    return jsonify({'doctor': doctor_data}), 200

if __name__ == '__main__':
    app.run(debug=True)