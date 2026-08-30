from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename
import requests
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.header import Header
app = Flask(__name__)
app.secret_key = 'secret_key'
conn = sqlite3.connect('users.db', check_same_thread=False)
cur = conn.cursor()
cur.execute('''
CREATE TABLE IF NOT EXISTS user(
       id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            password TEXT
            status TEXT DEFAULT 'user'
            )
''')
try:
    cur.execute("ALTER TABLE user ADD COLUMN status TEXT DEFAULT 'user'")
    conn.commit()
except:
    pass

conn.commit()

cur.execute('''
CREATE TABLE IF NOT EXISTS posts(
       id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            content TEXT,
            author_name TEXT
            file TEXT
            )
''')

try:
    cur.execute("ALTER TABLE posts ADD COLUMN file TEXT")
    conn.commit()
except:
    pass

conn.commit()


cur.execute("""
CREATE TABLE IF NOT EXISTS portfolio(
    id INTEGER  PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    description TEXT,
    image TEXT
)
""")
conn.commit()

UPLOAD_FOLDER = 'app_dir/static/images'
import os
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

import os

@app.route('/add_portfolio', methods=['POST'])
def add_portfolio():
    if session.get('status') != 'admin':
        return "Доступ запрещен", 403
    
    title = request.form.get('title')
    description = request.form.get('description')
    file = request.files.get('image')
    
    if file and file.filename:
        filename = file.filename
        # Сохраняем картинку в папку static/images/
        file.save(os.path.join('app_dir', 'static', 'images', filename))
        
        conn = sqlite3.connect('app_dir/user.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO portfolio (title, description, image) VALUES (?, ?, ?)",
            (title, description, filename)
        )
        conn.commit()
        conn.close()
        
    return redirect(url_for('admin_panel'))

@app.route('/upload_document', methods=['POST'])
def upload_document():
    if session.get('status') != 'admin':
        return "Доступ запрещен", 403
  
    post_id = request.form.get('post_id')
    file = request.files.get('document')
    
    if file and file.filename:
        filename = secure_filename(file.filename)
        # Сохраняем файл в папку static/images
        file.save(os.path.join('app_dir', 'static', 'images', filename))
        
        # Обновляем базу данных (используем правильный путь к базе user.db)
        conn = sqlite3.connect('app_dir/user.db')
        cur = conn.cursor()
        cur.execute("UPDATE posts SET file = ? WHERE id = ?", (filename, post_id))
        conn.commit()
        conn.close()
        
    return redirect(url_for('admin_panel'))


@app.route('/delete_portfolio/<int:id>', methods=['POST', 'GET'])
def delete_portfolio(id):
    if session.get('status') != 'admin':
        return "Доступ запрещен", 403
        
    conn = sqlite3.connect('app_dir/user.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin_panel'))

 
@app.route('/admin/')
def admin_panel():
    # 1. Проверяем, вошел ли пользователь и является ли он админом
    if session.get('status') != 'admin':
        return "Доступ запрещен! Вы не администратор.", 403
    
    conn = sqlite3.connect('app_dir/user.db')
    cursor = conn.cursor()
    
    # 2. Считаем реальную статистику для верхних блоков
    # Всего клиентов (всего пользователей в базе, кроме админа или вообще всех)
    cursor.execute("SELECT COUNT(*) FROM user")
    total_clients = cursor.fetchone()[0]
    
    # Новых заявок сегодня (если у вас есть колонка с датой в заявках/постах)
    # Для примера берем общее число постов/заявок, либо считаем из таблицы заявок
    cursor.execute("SELECT COUNT(*) FROM posts")
    total_orders = cursor.fetchone()[0]
    
    # Достаем список пользователей для таблицы
    cursor.execute("SELECT id, name, email, status FROM user")
    users = cursor.fetchall()
    
    # Достаем последние заявки/посты для нижней таблицы
    cursor.execute("SELECT id, name, content, author_name FROM posts ORDER BY id DESC LIMIT 5")
    posts = cursor.fetchall()

    portfolio_items = cursor.execute("SELECT id, title, description, image FROM portfolio").fetchall()

    conn.close()

    # 3. Передаем всё в шаблон admin.html
    return render_template(
        'admin.html',
        users=users,
        posts=posts,
        total_clients=total_clients,
        total_orders=total_orders,
        portfolio_items=portfolio_items
    )

@app.route('/admin/delete/<int:user_id>')
def delete_user(user_id):
    if session.get('status') != 'admin':
        return "Доступ запрещен!", 403

    conn = sqlite3.connect('app_dir/user.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

    return redirect('/admin/')
def get_all_posts():
    cur.execute("SELECT * FROM posts ORDER BY id DESC")
    return cur.fetchall()

def delete_post_by_id(post_id):
    cur.execute("DELETE FROM posts WHERE id = ?", [post_id])
    conn.commit()


def get_user_by_id(user_id):
    cur.execute(f'SELECT * FROM user WHERE id = {user_id} ')
    return cur.fetchone()

def get_user_by_email(email):
    cur.execute('SELECT * FROM user WHERE email = ?',[email] )
    return cur.fetchone()

def add_user(name, email, password):
    cur.execute('INSERT INTO user (name, email, password) VALUES (?, ?, ?)', (name, email, password))
    conn.commit()

@app.route('/')
def main():
    posts = cur.execute('SELECT * FROM posts').fetchall()
    # Убираем принудительную передачу user_name, чтобы шапка сама читала сессию чисто
    return render_template('main.html', posts=posts)

@app.route('/register/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        # 1. Проверяем, есть ли уже такой email в базе
        existing_user = get_user_by_email(email)

        if existing_user:
            return render_template('register.html', message='Пользователь с таким Email уже существует!')
        
        
        
        cur.execute('INSERT INTO user (name, email, password, status) VALUES (?, ?, ?, ?)', 
                   (name, email, password, 'user'))
        conn.commit()

        return redirect('/login/')

    return render_template('register.html')

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = get_user_by_email(email)

        print("--- ДЕБАГ ВХОДА ---")
        print("Введен email:", email)
        print("Введен password:", password)
        print("Данные из базы (user):", user)

        if user is None:
            return render_template('login.html', message='Аккаунта с такой почтой нету')
        elif str(user[3]) == str(password):
            session['user_name'] = user[1]
            session['email'] = user[2]
            session['status'] = user[4]

            # Если вошел админ — перенаправляем в админку
            if user[4] == 'admin' or user[2] == 'admin@gmail.com':
                session['status'] = 'admin'
                return redirect('/admin/')

            return redirect('/profile/')

        else:
            return render_template('login.html', message='Пароль неправильный')

    return render_template('login.html')


@app.route('/profile/')
def profile():
    if 'user_name' not in session:
        return redirect('/login/')
    
    # Получаем актуальные данные пользователя из базы данных user.db по его email из сессии
    user = get_user_by_email(session.get('email'))
    
    # Если пользователь нашелся в базе, берем имя из базы (user[1]), иначе из сессии
    current_name = user[1] if user else session.get('user_name')
    
    # Достаем заявки этого пользователя из базы данных
    conn = sqlite3.connect('app_dir/user.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, content, author_name, file FROM posts WHERE author_name = ?", (current_name,))
    user_projects = cursor.fetchall()
    conn.close()
    
    return render_template('profile.html', user=user, user_projects=user_projects)

@app.route('/logout/')
def logout():
    session.clear()  # Очищает все данные текущего пользователя
    return redirect('/login/')

@app.route('/delete_account', methods = [' GET','POST'])
def delete_account():
    name = session.get('user_name')
    cur.execute('delete FROM posts WHERE author_name = ?',[name])
    cur.execute('delete FROM posts WHERE name = ?',[name])
    conn.commit()
    session.clear()
    return redirect ('/')

@app.route('/o_nas/')
def o_nas():
 return  render_template('o_nas.html')

@app.route('/Uslugi/')
def Uslugi():
 return  render_template('Uslugi.html')

@app.route('/Contacts/', methods=['GET','POST'])
def Contacts():
 if request.method == 'POST':
             name = request.form.get('name')
             email = request.form.get('email')
             message = request.form.get('message')
 
             smtp_server = "smtp.mail.ru"
             smtp_port = 465
             your_email = "makhdi.r@mail.ru"
             app_password = "m0Gb3tqObo0adPSMjqW1"
             message_text = f"Новое сообщение с формы контактов:\n\nИмя: {name}\nEmail: {email}\nТекст: {message}"
            
             msg = MIMEText(message_text, 'plain', 'utf-8')
             msg['Subject'] = Header('Новая заявка с сайта', 'utf-8')
             msg['From'] = your_email
             msg['To'] = your_email
 
             try:
                 with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                     server.login(your_email, app_password)
                     server.sendmail(your_email, your_email, msg.as_string())
                     print(f"Письмо успешно отправлено!")
             except Exception as e:
               print(f"Ошибка при отправке: {e}")
 return  render_template('Contacts.html')



TELEGRAM_BOT_TOKEN = '8963953816:AAHEKFag8kj9chpwhwMesfSPGb-EjFdCpLI'
TELEGRAM_CHAT_ID = '7020387985'

@app.route('/order/', methods=['GET', 'POST'])
@app.route('/order', methods=['GET', 'POST'])
def order():
    if request.method == 'POST':
        service = request.form.get('service', 'Не указано')
        name = request.form.get('name', 'Не указано')
        phone = request.form.get('phone', 'Не указано')
        email = request.form.get('email', 'Не указано')
        comment = request.form.get('comment', 'Нет комментария')

        # Сохранение заявки в базу данных для админки
        try:
            conn = sqlite3.connect('app_dir/user.db')
            cursor = conn.cursor()
           # Берем имя авторизованного пользователя из сессии
            current_user_name = session.get('user_name', name)
            cursor.execute(
            "INSERT INTO posts (name, content, author_name) VALUES (?, ?, ?)",
            (service, f"Тел: {phone}, Email: {email}, Коммент: {comment}", current_user_name)
        )
            conn.commit()
            conn.close()
        except Exception as e:
            print("Ошибка сохранения в базу:", e)

        # Текст сообщения через .format()
        message = (
            "🚨 <b>Новая заявка на сайте!</b>\n\n"
            "🛠️ <b>Услуга:</b> {}\n"
            "👤 <b>Имя:</b> {}\n"
            "📞 <b>Телефон:</b> {}\n"
            "📧 <b>Email:</b> {}\n"
            "💬 <b>Комментарий:</b> {}"
        ).format(service, name, phone, email, comment)

        # Отправка в Telegram
        try:
            url = "https://api.telegram.org/bot{}/sendMessage".format(TELEGRAM_BOT_TOKEN)
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            }
            requests.post(url, data=payload)
        except Exception as e:
            print("Ошибка отправки в Telegram:", e)

        return render_template('order.html', success=True)

    return render_template('order.html')

@app.route('/posts/', methods=['GET', 'POST'])
def posts():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        author = session.get('user_name', 'Аноним')

        if title and content:
            cur.execute('INSERT INTO posts (title, content, author_name) VALUES (?, ?, ?)', (title, content, author))
            conn.commit()
            return redirect(url_for('posts'))

    cur.execute('SELECT * FROM posts ORDER BY id DESC')
    all_posts = cur.fetchall()
    return render_template('posts.html', posts=all_posts)


@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    cur.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    conn.commit()
    return redirect(url_for('posts'))

@app.route('/portfolio')
def portfolio():
    conn = sqlite3.connect('user.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, description, image FROM portfolio")
    items = cursor.fetchall()
    conn.close()
    return render_template('portfolio.html', portfolio_items=items)


@app.route('/sovet/')
def sovet():
 return render_template('Sovet.html')
   

