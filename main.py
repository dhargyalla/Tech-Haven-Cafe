from functools import wraps
from flask import Flask, render_template, jsonify, redirect,url_for, flash, abort
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column,relationship
from sqlalchemy import Integer, String, Boolean
from forms import CreateCafe, RegisterForm, LoginForm
from sqlalchemy.exc import IntegrityError
import os
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from decimal import Decimal


# TODO 1: CREATE INSTANCE OF FLASK
app = Flask(__name__)
bootstrap = Bootstrap5(app)

# Set a secret key for CSRF protection
app.config['SECRET_KEY'] = os.urandom(24)  # or use a fixed string for development

class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///cafes.db"
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# TODO: Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User,user_id)

# Define a Model Corresponding to the Existing Table
class Cafe(db.Model):
    __tablename__ = 'cafe'  # Ensure the table name matches your existing table name
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Primary key
    name: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)  # Unique cafe name
    map_url: Mapped[str] = mapped_column(String(500), nullable=False)  # URL for cafe location
    img_url: Mapped[str] = mapped_column(String(500), nullable=False)  # Image URL for the cafe
    location: Mapped[str] = mapped_column(String(250), nullable=False)  # Physical location
    has_sockets: Mapped[bool] = mapped_column(Boolean, nullable=False)  # Socket availability
    has_toilet: Mapped[bool] = mapped_column(Boolean, nullable=False)  # Toilet availability
    has_wifi: Mapped[bool] = mapped_column(Boolean, nullable=False)  # Wi-Fi availability
    can_take_calls: Mapped[bool] = mapped_column(Boolean, nullable=False)  # Phone call availability
    seats: Mapped[str] = mapped_column(String(250), nullable=False)  # Seating information
    coffee_price: Mapped[str] = mapped_column(String(250), nullable=True)  # Price of coffee, optional field

    # Define the relationship with the User model
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"), nullable=True)  # Foreign key
    author: Mapped["User"] = relationship("User", back_populates="cafes")  # Relationship back to User

class User(UserMixin, db.Model):
    __tablename__ = "users"  # Table name for users
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Primary key
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)  # User's email
    password: Mapped[str] = mapped_column(String(100))  # User's password
    name: Mapped[str] = mapped_column(String(250))  # User's name

    # Define the relationship with the Cafe model
    cafes: Mapped[list["Cafe"]] = relationship("Cafe", back_populates="author")  # One-to-many relationship


with app.app_context():
    db.create_all()

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if the current user is an admin
        if current_user.id == 1:
            return f(*args, **kwargs)  # Admin can access the function

        # Check if the action is to add a cafe (you can pass an action argument)
        action = kwargs.get('action', None)
        if action == 'add_cafe':
            return f(*args, **kwargs)  # Other users can add a cafe

        # For all other actions, deny access
        return abort(403)  # Forbidden

    return decorated_function


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/all_cafes')
def get_cafes():
    query = db.session.execute(db.select(Cafe)).scalars().all()
    # Fetch the column names dynamically from the Cafe model
    column_names = [column.name for column in Cafe.__table__.columns]

    return render_template('cafes.html', cafes=query, column_names=column_names, getattr=getattr)

@app.route('/add_cafe', methods=["GET", "POST"])
def create_cafe():
    form = CreateCafe()
    error_message = None
    if current_user.is_authenticated:
        if form.validate_on_submit():
            # Convert Decimal field to float or string
            #coffee_price = float(form.coffee_price.data) if isinstance(form.coffee_price.data,Decimal) else form.coffee_price.data
            new_cafe = Cafe(
                name = form.name.data,
                location = form.location.data,
                map_url = form.map_url.data,
                img_url = form.img_url.data,
                has_sockets = form.has_sockets.data,
                has_toilet = form.has_toilet.data,
                has_wifi = form.has_wifi.data,
                can_take_calls = form.can_take_calls.data,
                seats = form.seats.data,
                coffee_price = f"£{form.coffee_price.data}"
            )
            try:
                db.session.add(new_cafe)
                db.session.commit()
                # Flash a success message
                flash(f"Cafe {new_cafe.name} added successfully!", "success")
                return redirect(url_for("get_cafes"))
            except IntegrityError:
                db.session.rollback()
                error_message = f"A cafe with the title '{form.name.data}' already exists."
    else:
        return redirect('login')
    return render_template("add_cafe.html", form=form, error_message=error_message, current_user=current_user)


# Edit the existing cafe data
@app.route('/edit-cafe/<int:cafe_id>', methods=['GET', 'POST'])
@admin_only
def edit_cafe(cafe_id):
    cafe_to_edit = db.get_or_404(Cafe, cafe_id)

    # Properly handling coffee_price for float or Decimal type
    #coffee_price = float(cafe_to_edit.coffee_price) if isinstance(cafe_to_edit.coffee_price,Decimal) else cafe_to_edit.coffee_price

    # Pre-populating the form with existing cafe data
    form = CreateCafe(
        id=cafe_id,
        name=cafe_to_edit.name,
        location=cafe_to_edit.location,
        map_url=cafe_to_edit.map_url,
        img_url=cafe_to_edit.img_url,
        has_sockets=cafe_to_edit.has_sockets,
        has_toilet=cafe_to_edit.has_toilet,
        has_wifi=cafe_to_edit.has_wifi,
        can_take_calls=cafe_to_edit.can_take_calls,
        seats=cafe_to_edit.seats,
        coffee_price=cafe_to_edit.coffee_price
    )

    error_message = None

    if form.validate_on_submit():
        # Check if the new name already exists in another cafe (excluding the current cafe being edited)
        existing_cafe = db.session.query(Cafe).filter_by(name=form.name.data).first()
        if existing_cafe and existing_cafe.id != cafe_id:
            error_message = f"A cafe with the name '{form.name.data}' already exists."
        else:
            # Update cafe fields with form data
            cafe_to_edit.name = form.name.data
            cafe_to_edit.location = form.location.data
            cafe_to_edit.map_url = form.map_url.data
            cafe_to_edit.img_url = form.img_url.data
            cafe_to_edit.has_sockets = form.has_sockets.data
            cafe_to_edit.has_toilet = form.has_toilet.data
            cafe_to_edit.has_wifi = form.has_wifi.data
            cafe_to_edit.can_take_calls = form.can_take_calls.data
            cafe_to_edit.seats = form.seats.data
            cafe_to_edit.coffee_price = f"£{form.coffee_price.data}"

            try:
                db.session.commit()
                flash(f"Cafe {form.name.data} edited successfully!", "success")
                return redirect(url_for("get_cafes"))
            except IntegrityError:
                db.session.rollback()
                error_message = f"An error occurred while updating the cafe '{form.name.data}'."

    return render_template("add_cafe.html", form=form, is_edit=True, error_message=error_message)

# Delete a cafe
@app.route('/delete/<int:cafe_id>')
@admin_only
def delete(cafe_id):
    cafe = db.get_or_404(Cafe, cafe_id)
    db.session.delete(cafe)
    db.session.commit()
    flash(f"Cafe {cafe.name} successfully deleted!", "success")
    return redirect(url_for('manage'))
# Manage Cafe Data
@app.route('/cafe_manager')
def manage():
    query = db.session.execute(db.select(Cafe)).scalars().all()
    # Fetch the column names dynamically from the Cafe model
    column_names = [column.name for column in Cafe.__table__.columns]

    return render_template('cafe_manager.html', cafes=query, column_names=column_names, getattr=getattr)

# Register user
@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        hash_and_salted = generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8)
        newUser = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted
        )

        if user:
            flash("You've already signed up with that email, log in instead!", "danger")
            return redirect(url_for('login'))
        else:
            try:
                db.session.add(newUser)
                db.session.commit()
                flash("Register successfully, now login", "success")
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                raise e
            return redirect(url_for('login'))
    return render_template('register.html',form=form, current_user=current_user)

# Login Form
@app.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if not user:
            flash('The user does not exit, try again', 'danger')
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Incorrect password, try again', 'danger')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_cafes'))
    return render_template("login.html", form=form, current_user=current_user)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)



