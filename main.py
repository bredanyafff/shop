import os
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)

# Создаем папку для загрузок, если ее нет
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


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


@app.route('/login')
def login():
    return render_template('login.html')


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


if __name__ == "__main__":
    app.run(debug=True)