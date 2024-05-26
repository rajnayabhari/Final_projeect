import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import hashlib
import os 
import psycopg2
import re
from functools import wraps
from flask import Flask, request, render_template, redirect, session,url_for,abort

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database Connection
def get_db_connection():
    return psycopg2.connect(
        database="credential",
        user="postgres",
        password="@hybesty123",
        host="127.0.0.1",
        port=5432
    )

# Regular expressions
regex_email = re.compile(r'^[a-zA-Z0-9._%+-]+@gmail\.com$')
regex_pass = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')


# Hashing of password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    return stored_password == hash_password(provided_password)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def root():
    email='raj@gmail.com'       
    password='admin'
    username='raj'
    hashed_password = hash_password(password)

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS LOGIN(
                USER_ID SERIAL PRIMARY KEY NOT NULL,
                USERNAME VARCHAR(20) NOT NULL,
                EMAIL VARCHAR(100) NOT NULL UNIQUE,
                PASSWORD VARCHAR(64) NOT NULL,
                ROLE VARCHAR(20) NOT NULL
                );
                INSERT INTO LOGIN (username, password, email, role)
                SELECT %s, %s, %s, %s
                WHERE NOT EXISTS (
                    SELECT 1 FROM LOGIN WHERE email = %s
                );
                """, (username, hashed_password, email, 'admin', email)); 
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS Detail (
                Id_no SERIAL PRIMARY KEY NOT NULL,
                Certificate_no VARCHAR(20) NOT NULL,
                fullname VARCHAR(60) NOT NULL,
                mothername VARCHAR(60) NOT NULL,
                fathername VARCHAR(60) NOT NULL,
                grandfathername VARCHAR(60) NOT NULL,
                dob VARCHAR(20) NOT NULL,
                gender VARCHAR(10) NOT NULL,
                issueddate VARCHAR(20) NOT NULL,
                education VARCHAR(40) NOT NULL,
                employeed VARCHAR(40) NOT NULL,
                abroad VARCHAR(40) NOT NULL,
                reason_for_unemployment VARCHAR(100) DEFAULT '0',
                reason_for_uneducated VARCHAR(100) DEFAULT '0',
                reason_for_abroad VARCHAR(100) DEFAULT '0',
                USER_ID INT NOT NULL,
                FOREIGN KEY (USER_ID) REFERENCES LOGIN (USER_ID)
                );
                """)
                
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS message(
                subject varchar(250) not null,
                message varchar(250) not null,
                username varchar(250)not null,   
                USER_ID INT NOT NULL,
                FOREIGN KEY (USER_ID) REFERENCES LOGIN (USER_ID)
                    );
                """)
                
            conn.commit()
    except Exception as e:
        return render_template('error.html', info=str(e))
    return render_template("signin.html")


@app.route('/signup', methods=['POST'])
def register():
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confpass = request.form.get('confirm_password')

        if not (username and email and password and confpass):
            raise ValueError("All fields are required")

        if not re.match(regex_email, email):
            raise ValueError("Invalid email address")

        if not re.match(regex_pass, password):
            raise ValueError("Password must contain at least 1 uppercase, 1 lowercase, 1 digit, 1 special character, and be at least 8 characters long")

        if password != confpass:
            raise ValueError("Password and confirm password don't match")
                
        hashed_password = hash_password(password)
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM LOGIN WHERE EMAIL = %s", (email,))
                if cursor.fetchone():
                    raise ValueError("Email already registered")
                cursor.execute("INSERT INTO LOGIN(USERNAME, EMAIL, PASSWORD,Role) VALUES (%s, %s, %s,%s)", (username, email, hashed_password,'user'))
                conn.commit()
        return render_template('signin.html')
        
    except Exception as e:
        return render_template('signin.html', info=str(e))     
    
@app.route('/signin', methods=['POST'])
def login():

    email = request.form.get('email')
    password = request.form.get('password')
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM LOGIN WHERE EMAIL = %s", (email,))
                user = cursor.fetchone()
                if user and verify_password(user[3], password):
                    session['user_id'] = user[0]
                    session['role'] = user[4]
                    session['username']=user[1]
                    return redirect('/home')
    except Exception as e:
        return render_template('signin.html', info="Error occurred during login process")

    return render_template('signin.html', info="Invalid email or password")


def generate_certificate_number(prefix="DRF-"):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT MAX(Certificate_no) FROM detail")
                max_certificate_number = cursor.fetchone()[0]
                if max_certificate_number is None:
                    return prefix + "1"
                else:
                    numeric_part = int(max_certificate_number.split("-")[-1])
                    new_certificate_no = numeric_part + 1
                    return f"{prefix}{new_certificate_no}"
    except Exception as e:
        raise e

@app.route('/search', methods=['GET'])
@login_required
def search():
    if 'role' not in session:
        return redirect(url_for('signin'))
    
    try:
        query = request.args.get('query')
        if query is None:
            return render_template("error.html", info="No search query provided.")

        wildcard_query = f"%{query.lower()}%"

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Corrected SQL query with matching parameter count
                cursor.execute("""
                    SELECT id_no, fullname, gender, issueddate, employeed, education, abroad
                    FROM Detail
                    WHERE lower(fullname) LIKE %s
                       OR lower(education) LIKE %s
                       OR lower(abroad) LIKE %s
                       OR lower(employeed) = %s
                       OR lower(gender) = %s
                """, (wildcard_query, wildcard_query, wildcard_query, query.lower(), query.lower()))
                
                data = cursor.fetchall()

                # Corrected count query to match the search criteria
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM Detail
                    WHERE lower(fullname) LIKE %s
                       OR lower(education) LIKE %s
                       OR lower(abroad) LIKE %s
                       OR lower(employeed) = %s
                       OR lower(gender) = %s
                """, (wildcard_query, wildcard_query, wildcard_query, query.lower(), query.lower()))
                
                total = cursor.fetchone()[0]
                role=session['role']

                if data:
                    if session['role'] == 'admin':
                        return render_template('admin.html', items=data, total=total,role=role)
                    else:
                        return render_template('collector_data_view.html', items=data, total=total,role=role)

                else:
                    return render_template("error.html", info="Certificate not found!!")

    except Exception as e:
        return render_template('error.html', info=str(e))

   
    
    
@app.route('/home')
@login_required
def home():
    if 'role' in session:
        role = session['role']
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    name=session['username']
            return render_template('homepage.html', role=role,name=name.capitalize())
        except Exception as e:
            return render_template('signin.html', info=str(e))
    else:
        return redirect('/')
        




@app.route("/dataform")
@login_required
def dataform():
    role=session['role']
    return render_template("dataform.html" ,role=role)

@app.route("/registerdataform" , methods=['POST'])
@login_required
def registerdataform():
    try:    
        name=request.form.get('name')
        fathername=request.form.get('fathername')
        mothername=request.form.get('mothername')
        grandfathername=request.form.get('grandfathername')
        gender=request.form.get('gender')
        dob=request.form.get('dob')
        education=request.form.get('education')
        employeed=request.form.get('employed')
        abroad=request.form.get('abroad')
        issueddate=request.form.get('formdate')
        userid=session['user_id']
        if employeed=='Unemployed':
            reason_for_unemployment=request.form.get('reason_for_unemployment')
        else:
            reason_for_unemployment=0
        if education=='Illiterate':
            reason_for_uneducated=request.form.get('reason_for_uneducation')
        else:
            reason_for_uneducated=0
        if abroad=='Yes':
            reason_for_abroad=request.form.get('reason_for_abroad')
        else:
            reason_for_abroad=0

        # Generate a unique certificate number
        certificate_no = generate_certificate_number()

        # Insert data into the Detail table along with the generated certificate number
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO Detail(
                            Certificate_no,
                            fullname, 
                            fathername, 
                            mothername, 
                            grandfathername, 
                            dob, 
                            gender, 
                            education, 
                            employeed, 
                            abroad, 
                            issueddate,
                            reason_for_unemployment,
                            reason_for_uneducated,
                            reason_for_abroad,
                            user_id    
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s,%s)""", 
                        (certificate_no,name, fathername, mothername, grandfathername, dob, gender, education, employeed,abroad,
                        issueddate,reason_for_unemployment,reason_for_uneducated,reason_for_abroad ,userid
                        ))
                    conn.commit()
                    return redirect('/dataform')
        except Exception as e:
            conn.rollback()
            return str(e)
                    
    except Exception as e:
        return str(e)
    
    
    
@app.route('/userlist', methods=['GET'])
@login_required
def userlist():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT username, email,role FROM login")
                items=cursor.fetchall()
                role=session['role']
                
        return render_template('Userlist.html', items=items,role=role)
    except Exception as e:
            return render_template('error.html',info= f"An error occurred: {str(e)}")
            

@app.route('/admin', methods=['GET'])
@login_required
def admin():
    if session['role']=='admin':
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id_no,fullname,gender,issueddate,employeed,education,abroad  FROM detail order by id_no desc")
                    items=cursor.fetchall()
                    cursor.execute("SELECT COUNT(id_no) from detail")
                    total=cursor.fetchone()[0]
                    role=session['role']
            return render_template('admin.html', items=items,total=total,role=role)
        except Exception as e:
            return render_template('error.html',info= f"An error occurred: {str(e)}")
        
    else:
        return render_template('error.html',info="You dont have enought permission")    
    

@app.route('/updateuserrole/<string:item_id>', methods=['GET', 'POST'])
@login_required
def updateuserrole(item_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('signin'))

    if request.method == 'POST':
        new_role = request.form['role']
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE LOGIN SET role = %s WHERE email = %s", (new_role, item_id))
                conn.commit()
        return redirect(url_for('userlist'))
    role=session['role']
    return render_template('updateuserrole.html',role=role, email=item_id)

# Route to delete a user
@app.route('/deleteuser/<string:item_id>', methods=['GET','POST'])
@login_required
def deleteuser(item_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('signin'))
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM LOGIN WHERE email = %s", (item_id,))
                conn.commit()
    
    except Exception as e:
        return render_template('error.html',info= f"User cannot be deleted first delete data{str(e)}")
    return redirect(url_for('userlist'))     
    
@app.route('/data', methods=['GET'])
@login_required
def view_collector():
    try:
        userid=session['user_id']
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id_no, fullname, gender, issueddate, employeed, education, abroad
                    FROM detail
                    WHERE user_id = %s
                    ORDER BY id_no DESC
                    """,
                    (userid,)
                )                
                items=cursor.fetchall()
                role=session['role']
                cursor.execute("SELECT COUNT(id_no) from detail")
                total=cursor.fetchone()[0]
                if items==[]:
                    return render_template('error.html',info="please fill the form first")
                else:
                    return render_template('collector_data_view.html', items=items,role=role,total=total)
    except Exception as e:
        return render_template('error.html',info= f"An error occurred: {str(e)}")

    
    
    
# @app.route('/user', methods=['GET'])
# def guest():
#     if session['role'] == 'user':
#         try:
#             with get_db_connection() as conn:
#                 with conn.cursor() as cursor:
#                     cursor.execute("SELECT id_no,fullname,gender,issueddate,employeed,education,abroad  FROM detail ORDER BY id_no DESC")
#                     items = cursor.fetchall()
#                     cursor.execute("SELECT COUNT(id_no) FROM detail")
#                     total = cursor.fetchone()[0]
#             return render_template('user_data_view.html', items=items, total=total)
#         except Exception as e:
#             return render_template('error.html',info= f"An error occurred: {str(e)}")
        
        
@app.route('/update/<int:item_id>', methods=['GET', 'POST'])
@login_required
def update(item_id):
    # Ensure the user is authenticated and has a valid role in the session
    if 'role' not in session:
        return redirect(url_for('signin'))

    if request.method == 'POST':
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Get form data
                    fullname=request.form.get('name')
                    fathername=request.form.get('fathername')
                    mothername=request.form.get('mothername')
                    grandfathername=request.form.get('grandfathername')
                    gender=request.form.get('gender')
                    dob=request.form.get('dob')
                    education=request.form.get('education')
                    employeed=request.form.get('employed')
                    abroad=request.form.get('abroad')
                    issueddate=request.form.get('formdate')
                    if employeed=='Unemployed':
                        reason_for_unemployment=request.form.get('reason_for_unemployment')
                    else:
                        reason_for_unemployment=0
                    if education=='Illiterate':
                        reason_for_uneducated=request.form.get('reason_for_uneducation')
                    else:
                        reason_for_uneducated=0
                    if abroad=='Yes':
                        reason_for_abroad=request.form.get('reason_for_abroad')
                    else:
                        reason_for_abroad=0
                    # Construct and execute the SQL update query
                    cursor.execute("""
                        UPDATE Detail
                        SET fullname = %s, mothername = %s, fathername = %s, 
                            grandfathername = %s, dob = %s, gender = %s, 
                            issueddate = %s, education = %s, employeed = %s, 
                            abroad = %s,reason_for_unemployment=%s ,
                            reason_for_uneducated=%s ,
                            reason_for_abroad=%s
                            WHERE Id_no = %s
                            """, (fullname, mothername, fathername, 
                            grandfathername, dob, gender, 
                            issueddate, education, employeed, abroad, reason_for_unemployment, reason_for_uneducated, reason_for_abroad ,item_id))
                    conn.commit()
            # Redirect based on role
            if session['role'] == 'admin':
                return redirect(url_for('admin'))
            elif session['role'] == 'user':
                return redirect(url_for('view_collector'))
            else:
                return abort(403)  # Forbidden if the role is neither admin nor collector
        except Exception as e:
            # Render error template with relevant error message
            return render_template('error.html', info=f"Update error: {e}")
    else:
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Fetch item details from database
                    cursor.execute("SELECT * FROM Detail WHERE Id_no = %s", (item_id,))
                    item = cursor.fetchone()
                    print(item)
            if item:
                role=session['role']
                # Render update template with item details
                return render_template('update.html',role=role, item=item)
            else:
                # Render error template if item not found
                return render_template('error.html', info="Certificate not found"), 404
        except Exception as e:
            # Render error template with relevant error message
            return render_template('error.html', info=f"Update page loading error: {e}")


@app.route('/delete/<int:item_id>', methods=['GET'])
@login_required
def delete(item_id):
    if session['role'] == 'admin':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM detail WHERE id_no = %s', (item_id,))
            conn.commit()
            conn.close()
            return redirect(url_for('admin'))
        except Exception as e:
            return render_template('error,html',info=f"An error occurred: {str(e)}")
        

@app.route('/piechart')
@login_required
def generate_pie_chart():
    def fetch_data():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT education FROM detail")
        data = cursor.fetchall()
        cursor.execute("SELECT employeed FROM detail")
        data1 = cursor.fetchall()
        cursor.execute("SELECT abroad FROM detail")
        data2 = cursor.fetchall()
        cursor.close()
        conn.close()
        return data, data1, data2

    data, data1, data2 = fetch_data()
    
    def generate_chart(data, filename):
        counts = {}
        for row in data:
            key = row[0]
            counts[key] = counts.get(key, 0) + 1

        labels = counts.keys()
        sizes = counts.values()

        plt.figure(figsize=(8, 6))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
        plt.axis('equal')
        plt.savefig(f'static/{filename}')
        plt.close()

    generate_chart(data, 'pie_chart.png')
    generate_chart(data1, 'pie_chart1.png')
    generate_chart(data2, 'pie_chart2.png')
    role=session['role']

    return render_template('piechart.html',role=role)

@app.route('/reasonpiechart')
@login_required
def generate_reason_pie_chart():
    def fetch_data():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT reason_for_uneducated FROM detail where reason_for_uneducated <> '0' ")
        data = cursor.fetchall()
        cursor.execute("SELECT reason_for_unemployment from detail where reason_for_unemployment <> '0'")
        data1 = cursor.fetchall()
        cursor.execute("SELECT reason_for_abroad from detail where reason_for_abroad <> '0'")
        data2 = cursor.fetchall()
        cursor.close()
        conn.close()
        return data, data1, data2

    data, data1, data2 = fetch_data()
    
    def generate_chart(data, filename):
        counts = {}
        for row in data:
            key = row[0]
            counts[key] = counts.get(key, 0) + 1

        labels = counts.keys()
        sizes = counts.values()

        plt.figure(figsize=(8, 6))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
        plt.axis('equal')
        plt.savefig(f'static/{filename}')
        plt.close()

    generate_chart(data, 'pie_chart3.png')
    generate_chart(data1, 'pie_chart4.png')
    generate_chart(data2, 'pie_chart5.png')
    role=session['role']

    return render_template('reasonpiechart.html',role=role)

@app.route('/message', methods=['GET','POST'])
@login_required
def meesage():
    role=session['role']
    return render_template('message.html',role=role)

@app.route('/messagesubmit', methods=['GET','POST'])
@login_required
def meesagesubmit():
    subject=request.form.get('subject')
    message=request.form.get('message')
    userid=session['user_id']
    username=session['username']
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""INSERT INTO message(subject, message, user_id,username)
                               VALUES (%s, %s, %s, %s)"""
                               , (subject, message, userid,username))
                conn.commit()
        return redirect('/home')
        
    except Exception as e:
        return render_template('error.html', info=str(e)) 

@app.route('/datasummary')
@login_required
def datasummary():
    try:
        role=session['role']
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM detail WHERE abroad='Yes'")
                abroad = cursor.fetchone()[0]
                cursor.execute("SELECT count(id_no) FROM detail")
                total=cursor.fetchone()[0]
                cursor.execute("SELECT count(*) FROM detail WHERE employeed='Unemployed'")
                unemployeed = cursor.fetchone()[0]
                cursor.execute("SELECT count(*) FROM detail WHERE education='Illiterate'")
                uneducated = cursor.fetchone()[0]
                literacy=100-((uneducated/total)*100)

                return render_template('datasummary.html',total=total,abroad=abroad,unemployeed=unemployeed,uneducated=uneducated,literacy=literacy,role=role)
    except Exception as e:
        return render_template("error.html" ,info=str(e))
    
@app.route('/messageview',methods=['Get','POST'])
@login_required
def messagedview():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("Select * from message")
                items=cursor.fetchall()
                role=session['role']
        return render_template('messageview.html',items=items,role=role)
                
    except Exception as e:
        return render_template("error.html" ,info=str(e))
    
    
    
@app.route('/reasonbargraph', methods=['POST','GET'])
@login_required
def generate_reason_bar_graph():
    criteria1=request.form.get('criteria1')
    criteria2=request.form.get('criteria2')
    print(criteria1,criteria2)
    def fetch_data():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT {criteria1}, {criteria2} FROM detail")
        data=cursor.fetchall()
        cursor.close()
        conn.close()
        return data

    data = fetch_data()
    
    
    def generate_chart(data, filename, x, y):
        df = pd.DataFrame(data, columns=[x,y])
        print(df)

        plt.figure(figsize=(10, 6))
        sns.countplot(x=x,hue=y,data=df)

        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(f'static/{filename}')
        plt.close()

    generate_chart(data, 'bar_chart1.png', criteria1, criteria2)
    
    role = session['role']

    return render_template('bargraph.html', role=role,criteria1=criteria1.upper(),criteria2=criteria2.upper())



@app.route('/intro')
@login_required
def intro():
    role=session['role']
    return render_template('intro.html',role=role)

@app.route("/logout",methods=['POST'])
@login_required
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host='0.0.0.0',debug=True, port=5000)
