import os
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SECRET_KEY'] = '123'
db = SQLAlchemy(app)

# Создаем папку для загрузок, если ее нет
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)



# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    photo_path = db.Column(db.String)
    text = db.Column(db.Text)
    isActive = db.Column(db.Boolean, default=True)


@app.route('/')
def homepage():
    items = Item.query.order_by(Item.price).all()
    return render_template('homepage.html', data=items)


# @app.route('/login')
# def login():
#     return render_template('login.html')


@app.route('/admin', methods=['GET', 'POST'])
def addItem():
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            price = int(request.form.get('price'))
            text = request.form.get('text')
            isActive = True if request.form.get('isActive') == 'on' else False

            # Обработка загрузки изображения
            photo_path = None
            photo = request.files.get('photo_path')
            if photo and photo.filename != '':
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                photo_path = f'uploads/{filename}'

            new_item = Item(
                title=title,
                price=price,
                text=text,
                photo_path=photo_path,
                isActive=isActive
            )

            db.session.add(new_item)
            db.session.commit()
            return redirect(url_for('homepage'))

        except Exception as e:
            db.session.rollback()
            print(f"Error: {str(e)}")  # Для отладки
            return f"Ошибка при добавлении товара: {str(e)}", 500

    return render_template('additem.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('homepage'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Валидация данных
        errors = []
        if not username or len(username) < 3:
            errors.append('Имя пользователя должно содержать минимум 3 символа')
        if not email or '@' not in email:
            errors.append('Введите корректный email')
        if not password or len(password) < 6:
            errors.append('Пароль должен содержать минимум 6 символов')
        if password != confirm_password:
            errors.append('Пароли не совпадают')

        # Проверка уникальности username и email
        if User.query.filter_by(username=username).first():
            errors.append('Это имя пользователя уже занято')
        if User.query.filter_by(email=email).first():
            errors.append('Этот email уже зарегистрирован')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('register'))

        # Создание нового пользователя
        try:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('homepage'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Неверный email или пароль', 'danger')
            return redirect(url_for('login'))

        login_user(user, remember=remember)
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('homepage'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('homepage'))


if __name__ == "__main__":
    app.run(debug=True)