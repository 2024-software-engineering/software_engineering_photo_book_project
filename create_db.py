import sqlite3

# 데이터베이스 연결
conn = sqlite3.connect('photo_album.db')
cursor = conn.cursor()

# user_table 생성
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_table (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    user_nickname TEXT NOT NULL,
    user_ID TEXT NOT NULL UNIQUE,
    user_PW TEXT NOT NULL
);
''')

# photo_table 생성
cursor.execute('''
CREATE TABLE IF NOT EXISTS photo_table (
    photo_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    user_ID INTEGER NOT NULL,
    photo_img TEXT NOT NULL,
    photo_describ TEXT NOT NULL,
    FOREIGN KEY (user_ID) REFERENCES user_table(ID)
);
''')

# photo_keyword_table 생성
cursor.execute('''
CREATE TABLE IF NOT EXISTS photo_keyword_table (
    keyword_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    photo_ID INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    FOREIGN KEY (photo_ID) REFERENCES photo_table(photo_ID)
);
''')

# DM_table 생성
cursor.execute('''
CREATE TABLE IF NOT EXISTS DM_table (
    DM_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    user_ID INTEGER NOT NULL,
    photo_ID INTEGER NOT NULL,
    DM_msg TEXT NOT NULL,
    FOREIGN KEY (user_ID) REFERENCES user_table(ID),
    FOREIGN KEY (photo_ID) REFERENCES photo_table(photo_ID)
);
''')

# 변경사항 저장 및 연결 종료
conn.commit()
conn.close()

print("Tables created successfully.")
