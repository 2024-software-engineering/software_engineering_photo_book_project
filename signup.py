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

    return redirect(url_for('loginpage'))

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
            SELECT photo_table.photo_img, user_table.user_nickname, GROUP_CONCAT(photo_keyword_table.keyword), photo_table.photo_describ, photo_table.user_ID
            FROM photo_table
            JOIN user_table ON photo_table.user_ID = user_table.ID
            LEFT JOIN photo_keyword_table ON photo_table.photo_ID = photo_keyword_table.photo_ID
            WHERE photo_table.photo_ID = ?
            GROUP BY photo_table.photo_ID
        ''', (item_id,))
        photo = cur.fetchone()

        cur.execute('''
            SELECT DM_table.DM_ID, DM_table.DM_msg, user_table.user_nickname, DM_table.user_ID, DM_table.parent_ID
            FROM DM_table
            JOIN user_table ON DM_table.user_ID = user_table.ID
            WHERE DM_table.photo_ID = ?
            ORDER BY DM_table.DM_ID ASC
        ''', (item_id,))
        dms = cur.fetchall()

        is_user = 'user_id' in session and session['user_id'] == photo[4]

    keywords = photo[2] if photo[2] is not None else ''
    keywords_list = keywords.split(',')
    formatted_keywords = ' '.join([f'# {kw.strip()}' for kw in keywords_list])

    dms_with_parent = []
    for dm in dms:
        parent_user_name = None
        if dm[4]:  # parent_ID가 있는 경우
            cur.execute('SELECT user_nickname FROM user_table WHERE ID = (SELECT user_ID FROM DM_table WHERE DM_ID = ?)', (dm[4],))
            parent_user_name_result = cur.fetchone()
            if parent_user_name_result:
                parent_user_name = parent_user_name_result[0]
        dms_with_parent.append((dm[0], dm[1], dm[2], dm[3], dm[4], parent_user_name))


    item = {
    'id': item_id,
    'author': photo[1],
    'keywords': formatted_keywords,
    'description': photo[3],
    'img_src': photo[0],
    'is_user': is_user
    }

    return render_template('photo_detail.html', item=item, dms=dms_with_parent)


# DM 메시지 저장
@app.route('/msg_send', methods=['POST'])
def msg_send():
    if 'user_id' not in session:
        return redirect(url_for('loginpage'))

    user_id = session['user_id']
    dm_msg = request.form['msg']
    photo_id = request.form['photo_id']
    parent_id = request.form.get('parent_id')

    with sqlite3.connect('photo_album.db') as con:
        cur = con.cursor()
        
        # 부모 메시지의 사용자 이름을 찾습니다.
        parent_user_name = None
        if parent_id:
            cur.execute('SELECT user_ID FROM DM_table WHERE DM_ID = ?', (parent_id,))
            parent_user_result = cur.fetchone()
            if parent_user_result:
                parent_user_id = parent_user_result[0]
                cur.execute('SELECT user_nickname FROM user_table WHERE ID = ?', (parent_user_id,))
                parent_user_name_result = cur.fetchone()
                if parent_user_name_result:
                    parent_user_name = parent_user_name_result[0]

        cur.execute('''
            INSERT INTO DM_table (user_ID, photo_ID, DM_msg, parent_ID) VALUES (?, ?, ?, ?)
        ''', (user_id, photo_id, dm_msg, parent_id))
        con.commit()

    return redirect(url_for('photo_detail', item_id=photo_id, parent_user_name=parent_user_name))

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
        keywords = photo[3].split(',') if photo[3] is not None else []
        keywords = [kw.strip() for kw in keywords]
        highlighted_keywords = ', '.join([
            f'<span class="highlight"># {kw}</span>' if keyword and keyword in kw else f'# {kw}'
            for kw in keywords
        ])
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

    keywords = json.loads(keywords) 

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

@app.route('/photo_modify/<int:photo_id>', methods=['GET', 'POST'])
def modify_page(photo_id):
    if request.method == 'POST':

        # 키워드와 설명을 폼 데이터에서 정확히 추출
        description = request.form.get('description')
        keywords = json.loads(request.form.get('keywords'))
        photo_file = request.files.get('photo')

        with sqlite3.connect('photo_album.db') as con:
            cur = con.cursor()

            # 사진 설명 업데이트
            cur.execute('''
                UPDATE photo_table
                SET photo_describ = ?
                WHERE photo_ID = ?
            ''', (description, photo_id))

            # 새로운 사진이 업로드된 경우 사진 경로 업데이트
            if photo_file:
                photo_path = f'uploads/{photo_file.filename}'
                photo_file.save(f'static/{photo_path}')
                cur.execute('''
                    UPDATE photo_table
                    SET photo_img = ?
                    WHERE photo_ID = ?
                ''', (photo_path, photo_id))

            # 기존 키워드 삭제
            cur.execute('''
                DELETE FROM photo_keyword_table
                WHERE photo_ID = ?
            ''', (photo_id,))

            # 새로운 키워드 삽입
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

            # Fetch photo information
            cur.execute('''
                SELECT photo_img, photo_describ 
                FROM photo_table 
                WHERE photo_ID = ?
            ''', (photo_id,))
            photo = cur.fetchone()

            # Fetch keywords information
            cur.execute('''
                SELECT keyword 
                FROM photo_keyword_table 
                WHERE photo_ID = ?
            ''', (photo_id,))
            keywords = cur.fetchall()

        # Convert keywords to a list
        keywords = [keyword[0] for keyword in keywords]

        # Render template
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