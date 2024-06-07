import sqlite3
from flask import Flask,redirect, url_for, render_template,request,session, jsonify
import json

app = Flask(__name__)
app.secret_key = '1234'

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def loginpage():
    with sqlite3.connect('photo_album.db') as con:
        cur = con.cursor()

        cur.execute('''select user_nickname from user_table''')
        signupuserlist = cur.fetchall()

    return render_template('login_page.html',signupuserlist=signupuserlist)

#회원가입 페이지로 렌더링
@app.route('/signup_page')
def signup_page():
    return render_template('signup_page.html')

#회원가입
@app.route('/signup',methods = ['POST','GET'])
def create_user():
    if request.method=='POST':
        try:
            nickname= request.form['nickname']
            email = request.form['email']
            password=request.form['password']

            with sqlite3.connect('photo_album.db') as con:
                cur = con.cursor()
                cur.execute("INSERT INTO user_table(user_nickname,user_ID,user_PW) VALUES (?,?,?)" ,(nickname,email,password))
                con.commit()
        except:
            con.rollback()
        finally:
            if con:
                con.close()

    return render_template("login_page.html")

#로그인 구현
@app.route('/login',methods=['POST','GET'])
def check_user():
    if request.method=='POST':
            email=request.form['email']
            password= request.form['password']

            with sqlite3.connect('photo_album.db') as con:
                cur = con.cursor()
                cur.execute("SELECT * FROM user_table WHERE user_ID = ? AND user_PW = ?", (email, password))
                user = cur.fetchone()

                if user:
                    session['user_id'] =user[0]
                    session['user_nickname'] = user[1]
                    return redirect(url_for('mainpage'))
                else:
                    return render_template("loginpage.html")

#사진 디테일 페이지로 리다이렉트
@app.route('/photo_detail/<int:item_id>')
def photo_detail(item_id):
    with sqlite3.connect('photo_album.db') as con:
        cur = con.cursor()

        cur.execute('''
            SELECT photo_table.photo_img, user_table.user_nickname, GROUP_CONCAT(photo_keyword_table.keyword), photo_table.photo_describ
            FROM photo_table
            JOIN user_table ON photo_table.user_ID = user_table.ID
            LEFT JOIN photo_keyword_table ON photo_table.photo_ID = photo_keyword_table.photo_ID
            WHERE photo_table.photo_ID = ?
            GROUP BY photo_table.photo_ID
        ''', (item_id,))
        photo = cur.fetchone()

        cur.execute('''
            SELECT DM_table.DM_ID, DM_table.DM_msg, user_table.user_nickname, DM_table.user_ID
            FROM DM_table
            JOIN user_table ON DM_table.user_ID = user_table.ID
            WHERE DM_table.photo_ID = ?
        ''', (item_id,))
        dms = cur.fetchall()

    item = {
        'id': item_id,
        'author': photo[1],
        'keywords': ' '.join([f'#{kw}' for kw in photo[2].split(',')]),
        'description': photo[3],
        'img_src': photo[0]
    }

    return render_template('photo_detail.html', item=item, dms=dms)

# DM 메시지 저장
@app.route('/msg_send', methods=['POST'])
def msg_send():
    if 'user_id' not in session:
        return redirect(url_for('loginpage'))

    user_id = session['user_id']
    dm_msg = request.form['msg']
    photo_id = request.form['photo_id']

    with sqlite3.connect('photo_album.db') as con:
        cur = con.cursor()
        cur.execute('''
            INSERT INTO DM_table (user_ID, photo_ID, DM_msg) VALUES (?, ?, ?)
        ''', (user_id, photo_id, dm_msg))
        con.commit()

    return redirect(url_for('photo_detail', item_id=photo_id))

# DM 삭제
@app.route('/delete_dm/<int:dm_id>', methods=['POST'])
def delete_dm(dm_id):
    if 'user_id' not in session:
        return redirect(url_for('loginpage'))

    user_id = session['user_id']
    photo_id = request.form['photo_id']

    with sqlite3.connect('photo_album.db') as con:
        cur = con.cursor()
        cur.execute('DELETE FROM DM_table WHERE DM_ID = ? AND user_ID = ?', (dm_id, user_id))
        con.commit()

    return redirect(url_for('photo_detail', item_id=photo_id))

#업로드 페이지로 렌더링
@app.route('/upload')
def photo_upload():
    user_nickname = session['user_nickname']
    return render_template('photo_upload.html', user_nickname=user_nickname)

@app.route('/mainpage', methods=['GET', 'POST'])
def mainpage():
    keyword = request.form.get('keyword', '')

    with sqlite3.connect('photo_album.db') as con:
        cur = con.cursor()
        if keyword:
            cur.execute('''
                SELECT photo_table.photo_ID, photo_table.photo_img, user_table.user_nickname, 
                    GROUP_CONCAT(photo_keyword_table.keyword), photo_table.photo_describ
                FROM photo_table
                JOIN user_table ON photo_table.user_ID = user_table.ID
                LEFT JOIN photo_keyword_table ON photo_table.photo_ID = photo_keyword_table.photo_ID
                GROUP BY photo_table.photo_ID
                HAVING GROUP_CONCAT(photo_keyword_table.keyword) LIKE ?
            ''', ('%' + keyword + '%',))
        else:
            cur.execute('''
                SELECT photo_table.photo_ID, photo_table.photo_img, user_table.user_nickname, 
                    GROUP_CONCAT(photo_keyword_table.keyword), photo_table.photo_describ
                FROM photo_table
                JOIN user_table ON photo_table.user_ID = user_table.ID
                LEFT JOIN photo_keyword_table ON photo_table.photo_ID = photo_keyword_table.photo_ID
                GROUP BY photo_table.photo_ID
            ''')
        photos = cur.fetchall()

        cur.execute('''select user_nickname from user_table''')
        signupuserlist = cur.fetchall()

    # 검색된 키워드 강조 처리
    highlighted_photos = []
    for photo in photos:
        keywords = photo[3].split(',')
        highlighted_keywords = ', '.join(
            [f'<span class="highlight">{kw}</span>' if keyword and keyword in kw else kw for kw in keywords]
        )
        highlighted_photos.append((photo[0], photo[1], photo[2], highlighted_keywords, photo[4]))

    return render_template('mainpage.html', photos=highlighted_photos, keyword=keyword, signupuserlist=signupuserlist)

@app.route('/upload_page', methods=['POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('loginpage'))

    user_id = session['user_id']
    photo = request.files['photo']
    keywords = request.form['keywords']
    description = request.form['description']

    keywords = json.loads(keywords)  # Convert JSON string back to list

    photo_path = f'static/uploads/{photo.filename}'
    photo.save(photo_path)
    photo_path = f'uploads/{photo.filename}'
    
    with sqlite3.connect('photo_album.db') as con:
        cur = con.cursor()

        # Insert into photo_table
        cur.execute('''
            INSERT INTO photo_table (user_ID, photo_img, photo_describ)
            VALUES (?, ?, ?)
        ''', (user_id, photo_path, description))

        photo_id = cur.lastrowid

        # Insert into photo_keyword_table
        for keyword in keywords:
            cur.execute('''
                INSERT INTO photo_keyword_table (photo_ID, keyword)
                VALUES (?, ?)
            ''', (photo_id, keyword))

        con.commit()

    return jsonify({'success': True})

#사진수정하기
@app.route('/photo_modify/<int:photo_id>', methods=['GET', 'POST'])
def modify_page(photo_id):
    if request.method == 'POST':
        # Get the form data from the request
        description = request.form['description']
        keywords = json.loads(request.form['keywords'])
        photo_file = request.files.get('photo')

        with sqlite3.connect('photo_album.db') as con:
            cur = con.cursor()

            # Update photo description
            cur.execute('''
                UPDATE photo_table
                SET photo_describ = ?
                WHERE photo_ID = ?
            ''', (description, photo_id))

            # Update photo image if a new image is uploaded
            if photo_file:
                photo_path = f'uploads/{photo_file.filename}'
                photo_file.save(f'static/{photo_path}')
                cur.execute('''
                    UPDATE photo_table
                    SET photo_img = ?
                    WHERE photo_ID = ?
                ''', (photo_path, photo_id))

            # Delete existing keywords
            cur.execute('''
                DELETE FROM photo_keyword_table
                WHERE photo_ID = ?
            ''', (photo_id,))

            # Insert new keywords
            for keyword in keywords:
                cur.execute('''
                    INSERT INTO photo_keyword_table (photo_ID, keyword)
                    VALUES (?, ?)
                ''', (photo_id, keyword))

            con.commit()

        return jsonify(success=True)

    else:
        with sqlite3.connect('photo_album.db') as con:
            cur = con.cursor()

            # 사진 정보 가져오기
            cur.execute('''
                SELECT photo_img, photo_describ 
                FROM photo_table 
                WHERE photo_ID = ?
            ''', (photo_id,))
            photo = cur.fetchone()

            # 키워드 정보 가져오기
            cur.execute('''
                SELECT keyword 
                FROM photo_keyword_table 
                WHERE photo_ID = ?
            ''', (photo_id,))
            keywords = cur.fetchall()

        # 키워드 리스트 만들기
        keywords = [keyword[0] for keyword in keywords]

        # 템플릿 렌더링
        return render_template('photo_modify.html', 
                            photo_id=photo_id,
                            photo_img=photo[0], 
                            description=photo[1], 
                            keywords=keywords)

#dm_list 불러오기
@app.route('/dm_list')
def dm_list():
    user_nickname = session['user_nickname']
    
    with sqlite3.connect('photo_album.db') as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        # 최신 DM 정보만 선택 및 로그인한 사용자의 게시물만 선택
        cur.execute('''
            WITH LatestDM AS (
                SELECT 
                    photo_ID, 
                    MAX(DM_ID) AS MaxDMID
                FROM 
                    DM_table
                GROUP BY 
                    photo_ID
            )
            SELECT 
                p.photo_ID, 
                p.photo_img, 
                u.user_nickname, 
                dm_sender.user_nickname || ':' || d.DM_msg AS dm_info
            FROM 
                photo_table p
            JOIN 
                user_table u ON p.user_ID = u.ID
            LEFT JOIN 
                LatestDM ldm ON p.photo_ID = ldm.photo_ID
            LEFT JOIN 
                DM_table d ON ldm.MaxDMID = d.DM_ID
            LEFT JOIN 
                user_table dm_sender ON d.user_ID = dm_sender.ID
            WHERE 
                u.user_nickname = ?
            ORDER BY 
                d.DM_ID DESC
        ''', (user_nickname,))
        lists = cur.fetchall()

        cur.execute('''select user_nickname from user_table''')
        signupuserlist = cur.fetchall()

    return render_template('dm_list.html', user_nickname=user_nickname, lists=lists, signupuserlist=signupuserlist)



if __name__ == '__main__':
    app.run(debug=True)