import os
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user

'''
admin
admin@example.com
123456
КОРЗИНА ОЧИЩЕНА И КОРЗИНА УЖЕ ПУСТА ДОЛЖНЫ ОТОБРАЖАТЬСЯ НА СТРАНИЦЕ КОРЗИНЫ А НЕ НА ГЛАВНОЙ СТР
'''

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

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    user = db.relationship('User', backref=db.backref('cart_items', lazy=True))
    item = db.relationship('Item', backref=db.backref('cart_items', lazy=True))


@app.route('/')
def homepage():
    items = Item.query.filter_by(isActive=True).order_by(Item.price).all()

    # Получаем количество товаров в корзине текущего пользователя
    cart_items_count = 0
    if current_user.is_authenticated:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        cart_items_count = sum(item.quantity for item in cart_items)

    return render_template('homepage.html', data=items, cart_items_count=cart_items_count)


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    # Простая проверка на админа (в реальном проекте лучше использовать роли)
    if current_user.username != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('homepage'))

    # Обработка добавления товара
    if request.method == 'POST' and 'title' in request.form:
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
            flash('Товар успешно добавлен', 'success')
            return redirect(url_for('admin'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении товара: {str(e)}', 'danger')
            return redirect(url_for('admin'))

    # Получаем списки товаров и пользователей
    items = Item.query.order_by(Item.id).all()
    users = User.query.order_by(User.id).all()

    return render_template('admin.html', items=items, users=users)


@app.route('/admin/delete_item/<int:item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    if current_user.username != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('homepage'))

    item = Item.query.get_or_404(item_id)

    try:
        # Удаляем файл изображения, если он существует
        if item.photo_path:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], item.photo_path.replace('uploads/', ''))
            if os.path.exists(file_path):
                os.remove(file_path)

        db.session.delete(item)
        db.session.commit()
        flash('Товар успешно удален', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении товара: {str(e)}', 'danger')

    return redirect(url_for('admin'))


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.username != 'admin':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('homepage'))

    if current_user.id == user_id:
        flash('Вы не можете удалить себя', 'danger')
        return redirect(url_for('admin'))

    user = User.query.get_or_404(user_id)

    try:
        db.session.delete(user)
        db.session.commit()
        flash('Пользователь успешно удален', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении пользователя: {str(e)}', 'danger')

    return redirect(url_for('admin'))


@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    item_id = request.form.get('item_id')
    item = Item.query.get_or_404(item_id)
    user_id = current_user.id

    # Проверяем, есть ли уже такой товар в корзине пользователя
    cart_item = CartItem.query.filter_by(user_id=user_id, item_id=item_id).first()

    if cart_item:
        # Если товар уже есть в корзине, увеличиваем количество
        cart_item.quantity += 1
    else:
        # Если товара нет в корзине, добавляем его
        cart_item = CartItem(user_id=user_id, item_id=item_id, quantity=1)
        db.session.add(cart_item)

    db.session.commit()
    return redirect(url_for('homepage'))

@app.route('/update_cart', methods=['POST'])
@login_required
def update_cart():
    item_id = request.form.get('item_id')
    action = request.form.get('action')
    user_id = current_user.id

    cart_item = CartItem.query.filter_by(user_id=user_id, item_id=item_id).first()

    if not cart_item:
        return redirect(url_for('cart'))

    if action == 'increase':
        cart_item.quantity += 1
    elif action == 'decrease':
        cart_item.quantity -= 1
        if cart_item.quantity <= 0:
            db.session.delete(cart_item)

    db.session.commit()
    return redirect(url_for('cart'))

@app.route('/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    item_id = request.form.get('item_id')
    user_id = current_user.id

    cart_item = CartItem.query.filter_by(user_id=user_id, item_id=item_id).first()

    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()

    return redirect(url_for('cart'))

@app.route('/cart')
@login_required
def cart():
    user_id = current_user.id
    cart_items = CartItem.query.filter_by(user_id=user_id).all()
    total_price = 0
    total_items = 0

    items = []
    for cart_item in cart_items:
        item = Item.query.get(cart_item.item_id)
        if item:
            item.quantity = cart_item.quantity
            item.total_price = item.price * cart_item.quantity
            items.append(item)
            total_price += item.total_price
            total_items += cart_item.quantity

    return render_template('cart.html', cart_items=items, total_price=total_price, total_items=total_items, cart_items_count=total_items)


@app.route('/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    user_id = current_user.id
    cart_items = CartItem.query.filter_by(user_id=user_id).all()

    for cart_item in cart_items:
        db.session.delete(cart_item)

    db.session.commit()
    flash('Корзина успешно очищена', 'success')
    return redirect(url_for('cart'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('homepage'))

    cart_items_count = 0
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

    return render_template('register.html', cart_items_count=cart_items_count)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('homepage'))

    cart_items_count = 0
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

    return render_template('login.html', cart_items_count=cart_items_count)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('homepage'))

if __name__ == "__main__":
    app.run(debug=True)