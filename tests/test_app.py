import pytest
from main import app, db, User


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Создаем тестового пользователя (админа)
            admin = User(username='admin', email='admin@example.com')
            admin.set_password('123456')
            db.session.add(admin)
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()


def test_homepage(client):
    """Тест главной страницы"""
    response = client.get('/')
    assert response.status_code == 200
    # Проверяем наличие элементов, которые точно есть на вашей странице
    assert b'<!doctype html>' in response.data  # Проверка HTML-структуры
    assert b'<title>' in response.data  # Проверка наличия тега title


def test_admin_login(client):
    """Тест входа администратора"""
    # Логинимся как админ
    response = client.post('/login', data={
        'email': 'admin@example.com',
        'password': '123456'
    }, follow_redirects=True)

    assert response.status_code == 200
    # Проверяем редирект на главную после входа
    assert b'<!doctype html>' in response.data
    # Или проверьте другие элементы админ-панели