from flask_wtf import FlaskForm
from wtforms import HiddenField, StringField, BooleanField, IntegerField, DecimalField,SubmitField,PasswordField
from wtforms.validators import DataRequired, URL, Email
from flask_ckeditor import CKEditorField

class CreateCafe(FlaskForm):
    id = HiddenField()
    name= StringField(label="Name", validators=[DataRequired()])
    location= StringField(label="location", validators=[DataRequired()])
    img_url = StringField(label="Image url", validators=[URL()])
    map_url = StringField(label="Map url", validators=[URL()])
    has_sockets = BooleanField(label="Has sockets")
    has_toilet = BooleanField(label="Has toilet")
    has_wifi = BooleanField(label="Has wifi")
    can_take_calls = BooleanField(label="Can take calls")
    seats = StringField(label="Seats", validators=[DataRequired()])
    coffee_price = StringField(label="coffee price", validators=[DataRequired()])
    submit = SubmitField(label="Submit")

# TODO: Create a RegisterForm to register new users
class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(),Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    submit = SubmitField('Register')

# TODO: Create a LoginForm to login existing users
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators= [DataRequired()])
    submit = SubmitField('Login')
