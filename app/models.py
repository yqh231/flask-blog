from datetime import datetime
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request
from flask_login import UserMixin, AnonymousUserMixin
from . import db, login_manager


class Permission:
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0X04
    MODERATE_COMMENTS = 0X08
    ADMINISTER = 0x80

class Role(db.Document):
    __tablename__ = 'roles'
    #id = db.Column(db.Integer, primary_key=True)
    name = db.StringField(max_length = 64, unique=True)
    default = db.BooleanField(default = False)
    permissions = db.IntField()
    #users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'User' : (Permission.FOLLOW |
                      Permission.COMMENT |
                      Permission.WRITE_ARTICLES, True),

            'Moderator' : (Permission.FOLLOW |
                           Permission.COMMENT |
                           Permission.WRITE_ARTICLES |
                           Permission.MODERATE_COMMENTS, False),

            'Administrator' : (0xff, False)
        }

        for r in roles:
            role = Role.objects(name = r).first()
            if role is None:
                role = Role(name = r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            role.save()

    def __repr__(self):
        return '<Role %r>' % self.name


class User(UserMixin, db.Document):
    __tablename__ = 'users'
    #_id = db.StringField()
    email = db.StringField(max_length = 64, unique = True)
    username = db.StringField(max_length = 64, unique = True)
    #role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.StringField(max_length = 128)
    confirmed = db.BooleanField(default = False)
    role = db.ReferenceField(Role)
    location = db.StringField(max_length = 64)
    avatar_hash = db.StringField(max_length = 64)
    last_seen = DateTimeField()

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.objects(permissions = 0xff).first()
            if self.role is None:
                self.role = Role.objects(default = True).first()

        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()


    def get_id(self):
        try:
            return unicode(self.id)
        except AttributeError:
            raise NotImplementedError('No `id` attribute - override `get_id`')

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration = 3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': str(self.id)})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != str(self.id):
            return False
        self.confirmed = True
        self.save()
        return True

    def generate_reset_token(self, expiration = 3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': str(self.id)})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != str(self.id):
            return False
        self.password = new_password
        self.save()
        return True

    def generate_email_change_token(self, new_email, expiration = 3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': str(self.id), 'new_email': new_email})

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != str(self.id):
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.objects(email = new_email) is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()

        self.save()
        return True

    def can(self, permissions):
        return self.role is not None and \
               (self.role.permissions & permissions) == permissions
    def is_administrator(self):
        return self.can(Permission.ADMINISTER)

    def ping(self):
        self.last_seen = datetime.utcnow()
        self.save()

    def gravatar(self, size = 100, default = 'idention', rating = 'g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'

        hash = self.avatar_hash or hashlib.md5(
            self.email.encode('utf-8')
        ).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def __repr__(self):
        return '<User %r>' % self.username

class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    return User.objects(id = user_id).first()
