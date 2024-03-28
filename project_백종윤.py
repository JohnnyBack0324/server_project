import sys
import pymysql # MySQL DB 상호작용 모듈
import datetime # 오늘 날짜 지정
# PyQt5 UI
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QGridLayout, QWidget, QPushButton, QMessageBox, QDialog, QVBoxLayout, QDateEdit, QTextEdit
from PyQt5.QtGui import QColor, QTextCharFormat, QPixmap
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import QCalendarWidget, QDialogButtonBox, QListWidget, QListWidgetItem, QHBoxLayout, QVBoxLayout
import traceback # 에러 검증 용도


# MySQL 연결 설정
def connect_to_mysql():
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password=''
        )

        with conn.cursor() as cursor:
            # employee 데이터베이스가 존재하지 않는 경우 생성
            create_database_query = "CREATE DATABASE IF NOT EXISTS employee"
            cursor.execute(create_database_query)
            conn.commit()

        # employee 데이터베이스에 연결
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='',
            database='employee',
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

            # member 테이블 생성
            create_member_table = '''
            CREATE TABLE IF NOT EXISTS member (
                user_id VARCHAR(255) PRIMARY KEY, 
                user_password VARCHAR(255) NOT NULL
            )
            '''

            cursor.execute(create_member_table)
            conn.commit()

            # vacation_applications 테이블 생성
            create_vacation_applications_table = '''
            CREATE TABLE IF NOT EXISTS vacation_applications (
                user_id VARCHAR(255) PRIMARY KEY,
                start_date DATE,
                end_date DATE,
                status VARCHAR(20),
                checked TINYINT(1) DEFAULT NULL,
                rejection_reason VARCHAR(255) DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES member(user_id)
            )
            '''
            cursor.execute(create_vacation_applications_table)
            conn.commit()

    except Exception as e:
        print(f"테이블 생성 중 오류 발생: {str(e)}")


class DateRangeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 날짜 선택 레이아웃
        self.setWindowTitle("날짜 선택")
        self.layout = QVBoxLayout(self)

        self.start_date_label = QLabel("시작일:")
        self.layout.addWidget(self.start_date_label)

        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate())
        self.layout.addWidget(self.start_date_edit)

        self.end_date_label = QLabel("종료일:")
        self.layout.addWidget(self.end_date_label)

        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        self.layout.addWidget(self.end_date_edit)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    # 휴가 시작일, 종료일 반환
    def get_selected_dates(self):
        start_date = self.start_date_edit.date().toString(Qt.ISODate)
        end_date = self.end_date_edit.date().toString(Qt.ISODate)
        return start_date, end_date

class RejectReasonDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 반려 사유 레이아웃
        self.setWindowTitle("반려 사유 입력")
        self.reason_label = QLabel("반려 사유:")
        self.reason_textbox = QLineEdit()
        self.confirm_button = QPushButton("확인")
        self.confirm_button.clicked.connect(self.accept)

        layout = QVBoxLayout()
        layout.addWidget(self.reason_label)
        layout.addWidget(self.reason_textbox)
        layout.addWidget(self.confirm_button)
        self.setLayout(layout)

    # 반려 사유 반환
    def get_reason(self):
        return self.reason_textbox.text()

class ManagePageWindow(QMainWindow):
    def __init__(self, user_id):
        super().__init__()

        # 휴가 관리 페이지 레이아웃
        self.setWindowTitle("휴가 관리 페이지")
        self.setGeometry(100, 100, 500, 300)
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.user_id = user_id
        self.checked_false = False

        # 휴가 신청 인원 목록을 표시할 QListWidget
        self.applications_list = QListWidget()
        self.layout.addWidget(self.applications_list)

        # 아이템을 더블클릭할 때 호출되는 슬롯 연결
        self.applications_list.itemDoubleClicked.connect(self.show_rejection_reason)

        # 승인 및 반려 버튼을 담을 QHBoxLayout
        self.buttons_layout = QHBoxLayout()
        self.layout.addLayout(self.buttons_layout)

        # 승인 버튼
        self.approve_button = QPushButton("승인")
        self.approve_button.clicked.connect(self.approve_application_list)
        self.buttons_layout.addWidget(self.approve_button)
        self.set_checked_false()

        # 반려 버튼
        self.reject_button = QPushButton("반려")
        self.reject_button.clicked.connect(self.reject_application_list)
        self.buttons_layout.addWidget(self.reject_button)
        self.set_checked_false()

        # 삭제 버튼
        self.delete_button= QPushButton("삭제")
        self.delete_button.clicked.connect(self.delete_application_list)
        self.buttons_layout.addWidget(self.delete_button)

        # 사용자별 버튼 가시성 설정
        self.set_button_visibility()

    # 현재 사용자의 ID가 'admin'일 경우 승인/반려 버튼을 표시, 그 외 사용자는 삭제 버튼 표시
    def set_button_visibility(self):   
        if self.user_id == "admin":
            self.approve_button.setVisible(True)
            self.reject_button.setVisible(True)
            self.delete_button.setVisible(True)
        else:
            self.approve_button.setVisible(False)
            self.reject_button.setVisible(False)
            self.delete_button.setVisible(True)

    # 목록에 아이템 추가
    def add_application_item(self, user_id, start_date, end_date, status, checked):
        
        # 'X'일 경우 False, 'O'일 경우 True 대입
        checked = "X" if checked == 0 else "O"

        # 휴가 신청 인원 QListWidget에 아이템으로 추가
        item = QListWidgetItem(f"ID: {user_id}, 시작일: {start_date}, 종료일: {end_date}, 상태: {status}, 읽음: {checked}")

        # 사용자와 신청자가 일치하는 경우 아이템으로 추가
        if self.user_id == 'admin' or user_id == self.user_id:
            item = QListWidgetItem(item)
            self.applications_list.addItem(item)

    # 선택된 휴가 신청 인원 승인
    def approve_application_list(self):        
        selected_items = self.applications_list.selectedItems()
        for item in selected_items:
            user_id = self.get_user_id_from_item(item)
            self.update_application_status(user_id, "Approved")
            QMessageBox.information(self, "휴가 승인", f"ID: {user_id}의 휴가를 승인합니다.")

        self.refresh_application_list()

    # 선택된 휴가 신청 인원 반려
    def reject_application_list(self):
        selected_items = self.applications_list.selectedItems()
        for item in selected_items:
            user_id = self.get_user_id_from_item(item)

            # 반려 사유를 입력받는 다이얼로그 표시
            reject_dialog = RejectReasonDialog(self)
            if reject_dialog.exec_() == QDialog.Accepted:
                rejection_reason = reject_dialog.get_reason()

                # 휴가 신청 상태를 업데이트하고 리스트에서 제거하는 작업 수행
                self.update_application_status(user_id, "Rejected")

                # 휴가 신청 반려 사유를 데이터베이스에 추가
                self.add_rejected_reason(user_id, rejection_reason)

                # 휴가 신청 반려 팝업 및 메시지 표시
                QMessageBox.information(self, "휴가 반려", f"ID: {user_id}의 휴가를 반려합니다.\n사유: {rejection_reason}")

        self.refresh_application_list()

    # 읽음 False값 설정
    def set_checked_false(self):
        checked = self.checked_false

        try:
            with conn.cursor() as cursor:
                popup_sql = "UPDATE vacation_applications SET checked = %s"
                cursor.execute(popup_sql, (checked,))
                conn.commit()  
                                 
        except Exception as e:
            QMessageBox.critical(self, "에러", f"checked_to_False 전환 오류 발생: {str(e)}")

    # 선택된 휴가 신청 항목 삭제
    def delete_application_list(self):
        selected_items = self.applications_list.selectedItems()
        for item in selected_items:
            user_id = self.get_user_id_from_item(item)

            # mysql 테이블에서 항목 삭제
            if self.delete_application_from_mysql(user_id):
                QMessageBox.information(self, "항목 삭제", "항목이 삭제되었습니다.")
            else:
                QMessageBox.critical(self, "에러", "항목 삭제 중 오류가 발생했습니다.")

        self.refresh_application_list()

    # vacation_applications 테이블의 rejection_reason 열에 반려 사유 추가
    def add_rejected_reason(self, user_id, rejection_reason):
        try:
            with conn.cursor() as cursor:
                cursor = conn.cursor()
                reject_sql = "UPDATE vacation_applications SET rejection_reason = %s WHERE user_id = %s"
                cursor.execute(reject_sql, (rejection_reason, user_id))
                conn.commit()

        except Exception as e:
            QMessageBox.critical(self, "에러", f"반려 사유 업데이트 중 오류 발생: {str(e)}")

    # 반려 사유 보기
    def show_rejection_reason(self, item):
        # 더블 클릭시 user_id 반환
        user_id = self.get_user_id_from_item(item)
        # MySQL로부터 rejection_reason 반환
        rejection_reason = self.get_rejection_reason_from_mysql(user_id)

        # 반려 사유 팝업
        if rejection_reason:
            QMessageBox.information(self, "반려 사유", rejection_reason)
        else:
            QMessageBox.information(self, "진행중", "현재 승인을 진행중입니다.")

    # QListWidgetItem에서 user_id를 추출
    def get_user_id_from_item(self, item):
        text = item.text()
        user_id_start_index = text.index("ID: ") + 4
        user_id_end_index = text.index(",", user_id_start_index)
        user_id = text[user_id_start_index:user_id_end_index]
        return user_id

    # MySQL(vacation_applications table)로부터 반려 사유 가져오기
    def get_rejection_reason_from_mysql(self, user_id):
        try:
            with conn.cursor() as cursor:
                reject_query = "SELECT rejection_reason FROM vacation_applications WHERE user_id = %s"
                cursor.execute(reject_query, (user_id,))
                result = cursor.fetchone()

                if result is not None and 'rejection_reason' in result:
                    return result['rejection_reason']
                else:
                    return None

        except Exception as e:
            QMessageBox.critical(self, "에러", f"반려 사유 불러오기 중 오류 발생: {str(e)}")
            traceback.print_exc()

    # MySQL(vacation_applications table)에서 항목 삭제
    def delete_application_from_mysql(self, user_id):
        try:
            with conn.cursor() as cursor:
                delete_query = "DELETE FROM vacation_applications WHERE user_id = %s"
                cursor.execute(delete_query, (user_id,))
                conn.commit()
                return True

        except Exception as e:
            QMessageBox.critical(self, "에러", f"항목 삭제 중 오류 발생: {str(e)}")
            return False

    # 휴가 신청 상태 업데이트
    def update_application_status(self, user_id, status):        
        try:
            with conn.cursor() as cursor:
                sql = "UPDATE vacation_applications SET status = %s WHERE user_id = %s"
                cursor.execute(sql, (status, user_id))
                conn.commit()

        except Exception as e:
            QMessageBox.critical(self, "에러", f"휴가 신청 상태 업데이트 중 오류 발생: {str(e)}")

    # 휴가 신청 목록 새로고침
    def refresh_application_list(self):        
        self.applications_list.clear()

        try:
            with conn.cursor() as cursor:
                # admin 사용자의 경우 모든 휴가 신청 현황 조회
                if self.user_id == 'admin':
                    sql = "SELECT * FROM vacation_applications"
                    cursor.execute(sql)
                else:
                    sql = "SELECT * FROM vacation_applications WHERE user_id = %s"
                    cursor.execute(sql, (self.user_id))
                
                applications = cursor.fetchall()

                # 각 휴가 신청 인원을 ManagePageWindow에 추가
                for application in applications:
                    user_id = application['user_id']
                    start_date = application['start_date']
                    end_date = application['end_date']
                    status = application['status']
                    checked = application['checked']
                    self.add_application_item(user_id, start_date, end_date, status, checked)

        except Exception as e:
            QMessageBox.critical(self, "오류", f"휴가 신청 인원 조회 중 오류 발생: {str(e)}")


class DashboardWindow(QMainWindow):
    def __init__(self, user_id):
        super().__init__()

        # 대쉬보드 페이지 레이아웃
        self.setWindowTitle("대쉬보드")
        self.setGeometry(100, 100, 750, 500)
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QGridLayout(self.central_widget)

        self.user_id = user_id
        self.create_widgets()
        self.login_window = login_window
        self.checked_true = True

    # 대쉬보드 페이지 위젯
    def create_widgets(self):
    
        # 전체 그리드 레이아웃의 너비
        grid_geometry = self.layout.geometry()
        grid_width = grid_geometry.width()

        # 1열의 상대 너비 계산
        column_1_ratio = 1 / 10 
        column_1_width = grid_width * column_1_ratio

        # 2열의 너비는 1열의 너비의 9배로 설정
        column_2_width = column_1_width * 9

        # 오늘 날짜 가져오기
        current_date = datetime.date.today()

        # 오늘 날짜 QDate로 변환
        qdate = QDate(current_date.year, current_date.month, current_date.day)

        # 캘린더 위젯
        self.calendar_widget = QCalendarWidget()
        self.calendar_widget.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar_widget.clicked.connect(self.on_calendar_clicked)
        self.layout.addWidget(self.calendar_widget, 0, 1, 3, 1)
        # 오늘 날짜 하이라이트
        self.calendar_widget.setDateTextFormat(qdate, self.get_highlight_format())

        '''
        # 이미지 표시
        self.image_label = QLabel()
        image_path = "/Users/kcs/Desktop/VSC/project/기본이미지.png"
        pixmap = QPixmap(image_path)
        pixmap = pixmap.scaledToWidth(int(column_1_width))
        self.image_label.setPixmap(pixmap)
        self.layout.addWidget(self.image_label, 0, 0, 3, 1)
        '''

        # 사용자 정보 표시
        self.user_info_label = QLabel(f"사용자: {self.user_id}")
        # self.user_info_label = QLabel(f"권한: {self.}")
        self.user_info_label.setAlignment(Qt.AlignTop)
        self.layout.addWidget(self.user_info_label, 0, 0, Qt.AlignTop)

        # 휴가관리 페이지로 이동하는 버튼
        self.manage_page_button = QPushButton("휴가관리")
        self.manage_page_button.clicked.connect(self.open_manage_page)
        self.layout.addWidget(self.manage_page_button, 1, 0)

        # 로그아웃 버튼
        self.login_button = QPushButton("로그아웃")
        self.login_button.clicked.connect(self.logout)
        self.layout.addWidget(self.login_button, 2, 0)

        self.layout.setColumnStretch(0, int(column_1_width))
        self.layout.setColumnStretch(1, int(column_2_width))

    # 캘린더 클릭 이벤트
    def on_calendar_clicked(self, date):
        if self.user_id == 'admin':
            return 

        selected_date = date.toString("yyyy-MM-dd")
        print(f"Selected Date: {selected_date}")
        self.show_date_range_dialog(selected_date, self.user_id)

    # 오늘 날짜 하이라이트
    def get_highlight_format(self):
        # 하이라이트할 날짜의 배경색과 텍스트색 설정
        background_color = Qt.yellow
        text_color = Qt.black

        # 하이라이트를 위한 텍스트 형식 생성
        text_format = self.calendar_widget.dateTextFormat(self.calendar_widget.selectedDate())
        text_format.setBackground(background_color)
        text_format.setForeground(text_color)

        return text_format

    # 휴가 기간 MySQl 데이터 삽입
    def show_date_range_dialog(self, selected_date, user_id):
        # 날짜 선택 팝업
        dialog = DateRangeDialog(self)

        # 날짜 기본값 설정
        dialog.start_date_edit.setDate(QDate.fromString(selected_date, Qt.ISODate))
        dialog.end_date_edit.setDate(QDate.fromString(selected_date, Qt.ISODate))

        # 시작일, 종료일 변수 대입
        if dialog.exec_() == QDialog.Accepted:
            start_date, end_date = dialog.get_selected_dates()
            
            # MySQL에 데이터 삽입
            try:
                with conn.cursor() as cursor:
                    # 사용자 아이디 조회
                    sql = "SELECT * FROM member WHERE user_id = %s"
                    cursor.execute(sql, (user_id,))
                    user = cursor.fetchone()

                    if user:
                        # 휴가 신청 내역 확인
                        check_sql = "SELECT * FROM vacation_applications WHERE user_id = %s AND start_date = %s AND end_date = %s"
                        cursor.execute(check_sql, (user_id, start_date, end_date))
                        existing_data = cursor.fetchone()
                        if existing_data:
                            QMessageBox.critical(self, "에러", "이미 해당 날짜 범위의 휴가 신청이 존재합니다.")
                        else:
                            # 데이터 삽입
                            insert_sql = "INSERT INTO vacation_applications (user_id, start_date, end_date, status, checked) VALUES (%s, %s, %s, %s, %s)"
                            cursor.execute(insert_sql, (user_id, start_date, end_date, "Pending", 0))
                            conn.commit()
                            QMessageBox.information(self, "휴가 신청", "휴가 신청이 완료되었습니다.")

                    else:
                        QMessageBox.critical(self, "에러", "사용자를 찾을 수 없습니다.")

            except Exception as e:
                QMessageBox.critical(self, "에러", f"데이터 삽입 중 오류 발생: {str(e)}")

    # 휴가 관리 페이지 전환
    def open_manage_page(self):
        self.manage_page = ManagePageWindow(self.user_id)

        # MySQL에서 휴가 신청 인원 가져오기
        try:
            with conn.cursor() as cursor:

                # 휴가 신청 상태 조회
                sql = "SELECT status, checked FROM vacation_applications WHERE user_id = %s"
                cursor.execute(sql, (self.user_id,))
                result = cursor.fetchone()     
                
                if result and result['checked'] == False:
                    if result['status'] == "Approved" or result['status'] == "Rejected":
                        self.set_checked_true()

                # 휴가 신청 인원 조회
                sql = "SELECT * FROM vacation_applications"
                cursor.execute(sql)
                applications = cursor.fetchall()

                # 각 휴가 신청 인원을 ManagePageWindow에 추가
                for application in applications:
                    user_id = application['user_id']
                    start_date = application['start_date']
                    end_date = application['end_date']
                    status = application['status']
                    checked = application['checked']
                    self.manage_page.add_application_item(user_id, start_date, end_date, status, checked)

        except Exception as e:
            QMessageBox.critical(self, "오류", f"휴가 신청 인원 조회 중 오류 발생: {str(e)}")        

        self.manage_page.show()

    def set_checked_true(self):
        # 읽음 True값 변경
        checked = self.checked_true

        try:
            with conn.cursor() as cursor:
                popup_sql = "UPDATE vacation_applications SET checked = %s WHERE checked = %s"
                cursor.execute(popup_sql, (checked, 0))
                conn.commit()

        except Exception as e:
            print(f"오류 발생: {str(e)}")

    # 로그아웃 기능
    def logout(self):
        self.login_window = LoginWindow()
        self.login_window.show()
        self.close()

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 로그인 페이지 레이아웃
        self.setWindowTitle("로그인")
        self.setGeometry(100, 100, 300, 200)
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QGridLayout(self.central_widget)
        self.create_widgets()

    # 로그인 페이지 위젯
    def create_widgets(self):
        self.user_id_label = QLabel("아이디: ")
        self.layout.addWidget(self.user_id_label, 0, 0)

        self.user_id_input = QLineEdit()
        self.layout.addWidget(self.user_id_input, 0, 1)

        self.user_password_label = QLabel("비밀번호: ")
        self.layout.addWidget(self.user_password_label, 1, 0)

        self.user_password_input = QLineEdit()
        self.user_password_input.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.user_password_input, 1, 1)

        self.login_button = QPushButton("로그인")
        self.login_button.clicked.connect(self.login)
        self.layout.addWidget(self.login_button, 2, 0, 1, 2)

        self.register_button = QPushButton("회원가입")
        self.register_button.clicked.connect(self.register)
        self.layout.addWidget(self.register_button, 3, 0, 1, 2)

    # 로그인 기능 구현
    def login(self):
        user_id = self.user_id_input.text()
        user_password = self.user_password_input.text()

        try:
            with conn.cursor() as cursor:
                # 사용자 조회
                sql = "SELECT * FROM member WHERE user_id = %s AND user_password = %s"
                cursor.execute(sql, (user_id, user_password))
                user = cursor.fetchone()

                if user:
                    # 로그인 성공
                    self.open_dashboard(user_id)
                    self.check_vacation_status(user_id)
                    self.close()

                else:
                    QMessageBox.critical(self, "로그인 실패", "사용자 이름 또는 비밀번호가 잘못되었습니다.")

        except Exception as e:
            QMessageBox.critical(self, "로그인 실패", f"에러 발생: {str(e)}")

    # 회원가입 기능 구현
    def register(self):    
        user_id = self.user_id_input.text()
        user_password = self.user_password_input.text()

        try:
            with conn.cursor() as cursor:
                # 사용자 아이디 중복 검사
                sql = "SELECT * FROM member WHERE user_id = %s"
                cursor.execute(sql, (user_id,))
                existing_user = cursor.fetchone()

                if existing_user:
                    QMessageBox.critical(self, "회원가입 실패", "이미 존재하는 사용자입니다.")
                else:
                    # 사용자 등록
                    insert_sql = "INSERT INTO member (user_id, user_password) VALUES (%s, %s)"
                    cursor.execute(insert_sql, (user_id, user_password))
                    conn.commit()
                    QMessageBox.information(self, "회원가입 완료", "회원가입이 완료되었습니다.")

        except Exception as e:
            QMessageBox.critical(self, "회원가입 실패", f"에러 발생: {str(e)}")

    # 대쉬 보드 페이지 전환
    def open_dashboard(self, user_id):
        self.dashboard_window = DashboardWindow(user_id)
        self.dashboard_window.show()
        self.close()

    # 휴가 결과 팝업
    def check_vacation_status(self, user_id):
        try:
            with conn.cursor() as cursor:
                # 휴가 신청 상태 조회
                sql = "SELECT status, checked FROM vacation_applications WHERE user_id = %s"
                cursor.execute(sql, (user_id,))
                result = cursor.fetchone()                

                if result and result['checked'] == False:
                    if result['status'] == "Approved":
                        QMessageBox.information(self, "휴가 승인", "휴가 신청이 승인되었습니다.")

                    elif result['status'] == "Rejected":
                        QMessageBox.information(self, "휴가 반려", "휴가 신청이 반려되었습니다. 사유를 확인하세요.")

        except Exception as e:
            QMessageBox.critical(self, "에러", f"휴가 신청 상태 조회 중 오류 발생: {str(e)}")

# 메인 실행
if __name__ == "__main__":
    app = QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec_())
