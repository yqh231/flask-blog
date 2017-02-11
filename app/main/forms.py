from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, \
    SelectField
from wtforms.validators import Required, Length, Email, Regexp
from flask_pagedown.fields import PageDownField
from wtforms import ValidationError
from ..models import Role, User


class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[Required()])
    submit = SubmitField('Submit')

class EditProfileForm(FlaskForm):
    name = StringField('Real name', validators = [Length(0,64)])
    location = StringField('Location', validators = [Length(0,64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

class EditProfileAdminForm(FlaskForm):
    email = StringField('Email', validator = [Required(), Length(1,64)])

    username = StringField('Username', validator = [Required(), Length(1, 64), Regexp('^[A-Za-z0-9_.]*$',0,
                                                                                      'user must have only letters,'
                                                                                      'numbers, dot or undersorces')])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce = int)
    name = StringField('Real name', validators = [Length(0,64)])
    location = StringField('Location', validators = [Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(self, user, *args, **kwargs)
        self.role.choices = [(str(role.id), role.name)
                             for role in Role.objects]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
            User.objects(email = field.data).first():

            raise ValidationError('Email already registerd.')

    def valildate_username(self, field):
        if field.data != self.user.username and \
            User.objects(username = field.data).first():

            raise ValidationError('Username already in use')

class PostForm(FlaskForm):
    body = PageDownField('what\'s on your mind', validators = [Required()])
    submit = SubmitField('Submit')


