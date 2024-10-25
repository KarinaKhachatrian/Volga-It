from datetime import datetime

from flask import Flask, request
from flask_restx import Api, Resource, fields
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from models import *
from db import db, init_app
import os

app = Flask(__name__)
api = Api(app, doc='/docs')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['JWT_SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access']
jwt = JWTManager(app)

user_model = api.model('User', {
    'id': fields.Integer(readOnly=True, description='Уникальный идентификатор пользователя'),
    'lastName': fields.String(required=True, description='Фамилия пользователя'),
    'firstName': fields.String(required=True, description='Имя пользователя'),
    'username': fields.String(required=True, description='Логин пользователя'),
    'is_admin': fields.Boolean(description='Администраторский доступ'),
})


@api.route('/api/Authentication/SignUp')
class Register(Resource):
    @api.expect(user_model, validate=True)
    @api.doc('register_user')
    def post(self):
        """Регистрация нового пользователя"""
        data = request.get_json()
        if not data or not all(key in data for key in ['lastName', 'firstName', 'username', 'password']):
            api.abort(400, "Отсутствуют обязательные данные")

        if User.query.filter_by(username=data['username']).first():
            api.abort(400, "Пользователь уже существует")

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
            api.abort(500, f"Ошибка базы данных: {str(e)}")

        return {"message": "Пользователь успешно создан"}, 201


@api.route('/api/Authentication/SignIn')
class Login(Resource):
    @api.doc('login_user')
    def post(self):
        """Авторизация пользователя"""
        data = request.get_json()
        if not data or not all(key in data for key in ['username', 'password']):
            api.abort(400, "Отсутствуют обязательные данные")

        user = User.query.filter_by(username=data['username']).first()
        if not user or not user.check_password(data['password']):
            api.abort(401, "Неверный логин или пароль")

        access_token = create_access_token(identity=user.username)
        return {"access_token": access_token}, 200

history_model = api.model('History', {
    'id': fields.Integer(readOnly=True, description='Уникальный идентификатор записи'),
    'date': fields.DateTime(required=True, description='Дата истории'),
    'hospitalId': fields.Integer(required=True, description='ID больницы'),
    'doctorId': fields.Integer(required=True, description='ID доктора'),
    'room': fields.String(required=True, description='Кабинет'),
    'data': fields.String(required=True, description='Данные истории'),
})


@api.route('/api/History/Account/<int:id>')
class AccountHistory(Resource):
    @api.marshal_list_with(history_model)
    @jwt_required()
    def get(self, id):
        """Получение истории по ID пациента"""
        current_user = get_jwt_identity()
        if 'doctor' not in current_user['roles'] and current_user['id'] != id:
            api.abort(403, "Доступ запрещен: только врачи или владелец учетной записи могут получить историю")

        history_records = History.query.filter_by(pacient_id=id).all()
        return history_records, 200

hospital_model = api.model('Hospital', {
    'id': fields.Integer(readOnly=True, description='Уникальный идентификатор больницы'),
    'name': fields.String(required=True, description='Название больницы'),
})

room_model = api.model('Room', {
    'id': fields.Integer(readOnly=True, description='Уникальный идентификатор комнаты'),
    'number': fields.String(required=True, description='Номер комнаты'),
    'type': fields.String(description='Тип комнаты'),
})

@api.route('/api/Hospitals')
class HospitalList(Resource):
    @api.marshal_list_with(hospital_model)
    @jwt_required()
    def get(self):
        """Получение списка больниц"""
        from_param = request.args.get('from', default=0, type=int)
        count_param = request.args.get('count', default=10, type=int)
        hospitals = Hospital.query.offset(from_param).limit(count_param).all()
        return hospitals, 200

@api.route('/api/Hospitals')
class CreateHospital(Resource):
    @api.expect(hospital_model)
    @jwt_required()
    def post(self):
        """Создание новой больницы"""
        current_user = get_jwt_identity()

        if not current_user.is_admin:
            api.abort(403, "Доступ запрещен: только администраторы")

        data = request.get_json()

        if not data or not all(key in data for key in ['name', 'address', 'contactPhone', 'rooms']):
            api.abort(400, "Отсутствуют обязательные данные")

        new_hospital = Hospital(
            name=data['name'],
            address=data['address'],
            contactPhone=data['contactPhone']
        )

        try:
            db.session.add(new_hospital)
            db.session.commit()
        except Exception as e:
            api.abort(500, f"Ошибка базы данных: {str(e)}")

        return {"message": "Больница успешно создана", "id": new_hospital.id}, 201

timetable_model = api.model('Timetable', {
    'id': fields.Integer(readOnly=True, description='Уникальный идентификатор расписания'),
    'hospital_id': fields.Integer(required=True, description='ID больницы'),
    'doctor_id': fields.Integer(required=True, description='ID доктора'),
    'from_time': fields.DateTime(required=True, description='Начало работы'),
    'to_time': fields.DateTime(required=True, description='Конец работы'),
    'room': fields.String(required=True, description='Комната'),
})

appointment_model = api.model('Appointment', {
    'id': fields.Integer(readOnly=True, description='Уникальный идентификатор записи'),
    'timetable_id': fields.Integer(required=True, description='ID расписания'),
    'user_id': fields.Integer(required=True, description='ID пользователя'),
    'time': fields.DateTime(required=True, description='Время записи'),
})

@api.route('/api/Timetable')
class CreateTimetable(Resource):
    @api.expect(timetable_model)
    @jwt_required()
    def post(self):
        """Создание новой записи в расписании"""
        current_user = get_jwt_identity()

        if not current_user.is_admin and not current_user.is_manager:
            api.abort(403, "Доступ запрещен: только администраторы и менеджеры")

        data = request.get_json()

        if not data or not all(key in data for key in ['hospital_id', 'doctor_id', 'from_time', 'to_time', 'room']):
            api.abort(400, "Отсутствуют обязательные данные")

        new_entry = TimeTables(
            hospital_id=data['hospital_id'],
            doctor_id=data['doctor_id'],
            from_time=datetime.fromisoformat(data['from_time']),
            to_time=datetime.fromisoformat(data['to_time']),
            room=data['room']
        )

        try:
            db.session.add(new_entry)
            db.session.commit()
        except Exception as e:
            api.abort(500, f"Ошибка базы данных: {str(e)}")

        return {"message": "Запись в расписании создана успешно"}, 201

@api.route('/api/Timetable/Hospital/<int:hospital_id>')
class GetHospitalTimetable(Resource):
    @api.marshal_list_with(timetable_model)
    @jwt_required()
    def get(self, hospital_id):
        """Получение расписания для конкретной больницы"""
        timetable_entries = TimeTables.query.filter_by(hospital_id=hospital_id).all()
        return timetable_entries, 200


init_app(app)
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)