from flask import Flask, render_template, request, redirect, session
import pymysql
import secrets
import string
import traceback # 에러 검증 용도


# Flask secret key 무작위 생성
def generate_secret_key(length=24):
    alphabet = string.ascii_letters + string.digits + '-_'
    secret_key = ''.join(secrets.choice(alphabet) for _ in range(length))
    return secret_key


app = Flask(__name__)
app.secret_key = generate_secret_key()

# MySQL 연결 설정
def connect_to_mysql():
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password=''
        )

        with conn.cursor() as cursor:
            # matchmaking_system 데이터베이스가 존재하지 않는 경우 생성
            create_database_query = "CREATE DATABASE IF NOT EXISTS matchmaking_system"
            cursor.execute(create_database_query)
            conn.commit()

        # matchmaking_system 데이터베이스에 연결
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='',
            database='matchmaking_system',
            cursorclass=pymysql.cursors.DictCursor
        )

        return conn

    except Exception as e:
        print(f"MySQL 연결 오류: {str(e)}")
        return None

# MySQL 연결
conn = connect_to_mysql()
if conn:
    try:
        with conn.cursor() as cursor:

            # users 테이블 생성
            create_users_table = '''
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY, 
                username VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL
            )
            '''
            cursor.execute(create_users_table)
            conn.commit()

            # competitions 테이블 생성
            create_competitions_table = '''
            CREATE TABLE IF NOT EXISTS competitions (
                competition_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                start_date DATE,
                end_date DATE,
                status VARCHAR(255),
                checked TINYINT(1) DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            '''
            cursor.execute(create_competitions_table)
            conn.commit()

            # userskills 테이블 생성
            create_userskills_table = '''
            CREATE TABLE IF NOT EXISTS userskills (
                user_id INT,
                skill_name VARCHAR(255),
                skill_level INT,
                PRIMARY KEY (user_id, skill_name),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            '''
            cursor.execute(create_userskills_table)
            conn.commit()

            # messages 테이블 생성
            create_messages_table = '''
            CREATE TABLE IF NOT EXISTS messages (
                message_id INT AUTO_INCREMENT PRIMARY KEY,
                sender_id INT,
                receiver_id INT,
                message_content TEXT,
                sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(user_id),
                FOREIGN KEY (receiver_id) REFERENCES users(user_id)
            )
            '''
            cursor.execute(create_messages_table)
            conn.commit()

            # matchings 테이블 생성
            create_matchings_table = '''
            CREATE TABLE IF NOT EXISTS matchings (
                matching_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                competition_id INT,
                is_matched TINYINT(1),
                matching_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (competition_id) REFERENCES competitions(competition_id)
            )
            '''
            cursor.execute(create_matchings_table)
            conn.commit()


    except Exception as e:
        print(f"테이블 생성 중 오류 발생: {str(e)}")

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        entered_username = request.form['username']
        entered_password = request.form['password']

        # MySQL 쿼리를 사용하여 사용자 인증 검사
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (entered_username, entered_password))
        user = cursor.fetchone()

        if user:
            # 로그인 성공시 세션에 사용자 정보 저장
            session['user'] = user['username']
            return redirect('main.html')
        else:
            # 로그인 실패시 에러 메시지 표시
            error_message = "Invalid username or password"
            return render_template('login.html', error_message=error_message)

    # GET 요청인 경우 로그인 페이지 표시
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':

        # 회원가입 폼에서 전송된 데이터 받기
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        # MySQL 쿼리를 사용하여 사용자 추가
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password, email) VALUES (%s, %s, %s)", (username, password, email))
        conn.commit()

        # 회원가입 성공 후 로그인 페이지로 리디렉션
        return redirect('/')

    # GET 요청인 경우 회원가입 페이지 표시
    return render_template('signup.html')


@app.route('/main', methods=['GET', 'POST'])
def main():
    if 'user' in session and session['user'] == username:
        return render_template('main.html')
    else:
        return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
