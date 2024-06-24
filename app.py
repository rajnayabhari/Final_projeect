import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import hashlib
import os
import re
from psycopg2 import IntegrityError
from functools import wraps
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    session,
    url_for,
    abort,
    flash,
)
from database import get_db_connection, database
from werkzeug.utils import secure_filename
from datetime import datetime
import csv


# Get the current date and time
now = datetime.now()
date = now.strftime("%Y-%m-%d")

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["UPLOAD_FOLDER"] = "/home/raj/data_import_save"

# Database Connection
# def get_db_connection():
#     return psycopg2.connect(
#         database="credential",
#         user="postgres",
#         password="@hybesty123",
#         host="127.0.0.1",
#         port=5432
#     )

# Regular expressions
regex_email = re.compile(r"^[a-zA-Z0-9._%+-]+@gmail\.com$")
regex_pass = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
)
regex_phone=re.compile(r"98\d{8}|97\d{8}")



# Hashing of password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(stored_password, provided_password):
    return stored_password == hash_password(provided_password)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/")
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def root():
    try:
        database()
    except Exception as e:
        return render_template("error.html", info=str(e), role=session["role"])
    return render_template("signin.html")


@app.route("/signup", methods=["POST"])
def register():
    try:
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confpass = request.form.get("confirm_password")

        if not (username and email and password and confpass):
            raise ValueError("All fields are required")

        if not re.match(regex_email, email):
            raise ValueError("Invalid email address")

        if not re.match(regex_pass, password):
            raise ValueError(
                "Password must contain at least 1 uppercase, 1 lowercase, 1 digit, 1 special character, and be at least 8 characters long"
            )

        if password != confpass:
            raise ValueError("Password and confirm password don't match")

        hashed_password = hash_password(password)
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM login WHERE EMAIL = %s", (email,))
                if cursor.fetchone():
                    raise ValueError("Email already registered")
                cursor.execute(
                    "INSERT INTO login(USERNAME, EMAIL, PASSWORD,Role) VALUES (%s, %s, %s,%s)",
                    (username, email, hashed_password, "user"),
                )
                conn.commit()
        return render_template("signin.html")

    except Exception as e:
        return render_template("signin.html", info=str(e))


@app.route("/signin", methods=["POST"])
def login():

    email = request.form.get("email")
    password = request.form.get("password")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM login WHERE EMAIL = %s", (email,))
                user = cursor.fetchone()
                if user and verify_password(user[3], password):
                    session["user_id"] = user[0]
                    session["role"] = user[4]
                    session["username"] = user[1]
                    return redirect("/home")
    except Exception as e:
        return render_template("signin.html", info=str(e))

    return render_template("signin.html", info="Invalid email or password")


@app.route("/search", methods=["GET"])
@login_required
def search():
    if "role" not in session:
        return redirect(url_for("signin"))

    try:
        query = request.args.get("query")
        if query is None:
            return render_template("error.html", info="No search query provided.")

        wildcard_query = f"%{query.lower()}%"

        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Corrected SQL query with matching parameter count
                cursor.execute(
                    """
                    SELECT id_no, fullname, gender, issueddate, employeed, education, abroad
                    FROM detail
                    WHERE lower(fullname) LIKE %s
                       OR lower(education) LIKE %s
                       OR lower(abroad) LIKE %s
                       OR lower(employeed) = %s
                       OR lower(gender) = %s
                """,
                    (
                        wildcard_query,
                        wildcard_query,
                        wildcard_query,
                        query.lower(),
                        query.lower(),
                    ),
                )

                data = cursor.fetchall()

                # Corrected count query to match the search criteria
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM detail
                    WHERE lower(fullname) LIKE %s
                       OR lower(education) LIKE %s
                       OR lower(abroad) LIKE %s
                       OR lower(employeed) = %s
                       OR lower(gender) = %s
                """,
                    (
                        wildcard_query,
                        wildcard_query,
                        wildcard_query,
                        query.lower(),
                        query.lower(),
                    ),
                )

                total = cursor.fetchone()[0]
                role = session["role"]

                if data:
                    return render_template(
                        "admin.html", items=data, total=total, role=role
                    )

                else:
                    return render_template("admin.html", info="No coressponding data!!")

    except Exception as e:
        return render_template("error.html", info=str(e), role=session["role"])


@app.route("/home")
@login_required
def home():
    if "role" in session:
        role = session["role"]
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT count(*) FROM detail WHERE abroad='Yes'")
                    abroad = cursor.fetchone()[0]
                    cursor.execute("SELECT count(id_no) FROM detail")
                    total = cursor.fetchone()[0]
                    cursor.execute(
                        "SELECT count(*) FROM detail WHERE employeed='Unemployed'"
                    )
                    unemployeed = cursor.fetchone()[0]
                    cursor.execute(
                        "SELECT count(*) FROM detail WHERE education='Illiterate'"
                    )
                    uneducated = cursor.fetchone()[0]
                    if total == 0:
                        literacy = 0  # or any appropriate default value or error handling mechanism
                    else:
                        literacy = 100 - ((uneducated / total) * 100)
                    name = session["username"]
            return render_template(
                "homepage.html",
                role=role,
                name=name.capitalize(),
                total=total,
                abroad=abroad,
                unemployeed=unemployeed,
                uneducated=uneducated,
                literacy=literacy,
            )
        except Exception as e:
            return render_template("signin.html", info=str(e), role=session["role"])
    else:
        return redirect("/")


@app.route("/dataform")
@login_required
def dataform():
    role = session["role"]
    return render_template("dataform.html", role=role, date=date)


@app.route("/registerdataform", methods=["POST"])
@login_required
def registerdataform():
    try:
        name = request.form.get("name")
        fathername = request.form.get("fathername")
        mothername = request.form.get("mothername")
        grandfathername = request.form.get("grandfathername")
        gender = request.form.get("gender")
        dob = request.form.get("dob")
        dob_datetime = datetime.strptime(dob, '%Y-%m-%d')
        
        # Use datetime.now() to get the current datetime
        if dob_datetime.date() > datetime.now().date():
            raise ValueError('The date cannot be in the future.')
        
        education = request.form.get("education")
        employeed = request.form.get("employed")
        abroad = request.form.get("abroad")
        userid = session["user_id"]
        phone_no = request.form.get("phone_no")
        
        if not re.match(regex_phone, phone_no):
            raise ValueError("Invalid phone_no")
        
        if employeed == "Unemployed":
            reason_for_unemployment = request.form.get("reason_for_unemployment")
        else:
            reason_for_unemployment = None
        
        if education == "Illiterate":
            reason_for_uneducated = request.form.get("reason_for_uneducation")
        else:
            reason_for_uneducated = None
        
        if abroad == "Yes":
            reason_for_abroad = request.form.get("reason_for_abroad")
        else:
            reason_for_abroad = None

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO detail(
                            fullname, 
                            fathername, 
                            mothername, 
                            grandfathername, 
                            phone_no, 
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
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            name,
                            fathername,
                            mothername,
                            grandfathername,
                            phone_no,
                            dob,
                            gender,
                            education,
                            employeed,
                            abroad,
                            datetime.now().date(),  # issueddate should be the current date
                            reason_for_unemployment,
                            reason_for_uneducated,
                            reason_for_abroad,
                            userid,
                        ),
                    )
                    conn.commit()
                    return redirect("/dataform")
        except Exception as e:
            conn.rollback()
            return render_template(
                "error.html", info=f"An error occurred: {str(e)}", role=session["role"]
            )

    except Exception as e:
        return render_template(
            "error.html", info=f"An error occurred: {str(e)}", role=session["role"]
        )


@app.route("/userlist", methods=["GET"])
@login_required
def userlist():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT username, email,role FROM login")
                items = cursor.fetchall()
                role = session["role"]

        return render_template("Userlist.html", items=items, role=role)
    except Exception as e:
        return render_template(
            "error.html", info=f"An error occurred: {str(e)}", role=session["role"]
        )


@app.route("/admin", methods=["GET"])
@login_required
def admin():
    if session["role"] == "admin":
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                            SELECT d.id_no, d.fullname, l.username, d.gender, d.issueddate, d.education, d.employeed, d.abroad,d.phone_no
                            FROM detail d
                            INNER JOIN login l ON d.user_id = l.user_id
                        """)
                    items = cursor.fetchall()
                    cursor.execute("SELECT COUNT(id_no) from detail")
                    total = cursor.fetchone()[0]
                    role = session["role"]
            return render_template("admin.html", items=items, total=total, role=role)
        except Exception as e:
            return render_template("error.html", info=f"An error occurred: {str(e)}")

    else:
        return render_template("error.html", info="You dont have enought permission")


@app.route("/updateuserrole/<string:item_id>", methods=["GET", "POST"])
@login_required
def updateuserrole(item_id):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("signin"))

    if request.method == "POST":
        new_role = request.form["role"]
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE login SET role = %s WHERE email = %s", (new_role, item_id)
                )
                conn.commit()
        return redirect(url_for("userlist"))
    role = session["role"]
    return render_template("updateuserrole.html", role=role, email=item_id)


# Route to delete a user
@app.route("/deleteuser/<string:item_id>", methods=["GET", "POST"])
@login_required
def deleteuser(item_id):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("signin"))
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM login WHERE email = %s", (item_id,))
                conn.commit()

    except Exception as e:
        return render_template(
            "error.html",
            info=f"User cannot be deleted first delete data{str(e)}",
            role=session["role"],
        )
    return redirect(url_for("userlist"))


@app.route("/data", methods=["GET"])
@login_required
def view_collector():
    try:
        userid = session["user_id"]
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id_no, fullname, gender, issueddate, employeed, education, abroad
                    FROM detail
                    WHERE user_id = %s
                    ORDER BY id_no DESC
                    """,
                    (userid,),
                )
                items = cursor.fetchall()
                role = session["role"]
                cursor.execute("SELECT COUNT(id_no) from detail")
                total = cursor.fetchone()[0]
                if items == []:
                    return render_template(
                        "error.html", info="please fill the form first"
                    )
                else:
                    return render_template(
                        "collector_data_view.html", items=items, role=role, total=total
                    )
    except Exception as e:
        return render_template(
            "error.html", info=f"An error occurred: {str(e)}", role=session["role"]
        )


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


@app.route("/update/<int:item_id>", methods=["GET", "POST"])
@login_required
def update(item_id):
    if "role" not in session:
        return redirect(url_for("signin"))

    if request.method == "POST":
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    fullname = request.form.get("name")
                    fathername = request.form.get("fathername")
                    mothername = request.form.get("mothername")
                    grandfathername = request.form.get("grandfathername")
                    gender = request.form.get("gender")
                    dob = request.form.get("dob")
                    dob_datetime = datetime.strptime(dob, '%Y-%m-%d')
        
                    if dob_datetime.date() > datetime.now().date():
                        raise ValueError('The date cannot be in the future.')
                    education = request.form.get("education")
                    employeed = request.form.get("employed")
                    abroad = request.form.get("abroad")
                    phone_no = request.form.get("phone_no")
                    
                    if not re.match(regex_phone, phone_no):
                        raise ValueError("Invalid phone_no")
                    
                    if employeed == "Unemployed":
                        reason_for_unemployment = request.form.get(
                            "reason_for_unemployment"
                        )
                    else:
                        reason_for_unemployment = 0
                    if education == "Illiterate":
                        reason_for_uneducated = request.form.get(
                            "reason_for_uneducation"
                        )
                    else:
                        reason_for_uneducated = 0
                    if abroad == "Yes":
                        reason_for_abroad = request.form.get("reason_for_abroad")
                    else:
                        reason_for_abroad = 0
                    
                    cursor.execute(
                        """
                        UPDATE detail
                        SET fullname = %s, mothername = %s, fathername = %s, 
                            grandfathername = %s, dob = %s, gender = %s, 
                            education = %s, employeed = %s, 
                            abroad = %s, reason_for_unemployment = %s,
                            reason_for_uneducated = %s,
                            reason_for_abroad = %s,
                            phone_no = %s
                        WHERE Id_no = %s
                        """,
                        (
                            fullname,
                            mothername,
                            fathername,
                            grandfathername,
                            dob,
                            gender,
                            education,
                            employeed,
                            abroad,
                            reason_for_unemployment,
                            reason_for_uneducated,
                            reason_for_abroad,
                            phone_no,
                            item_id,
                        ),
                    )
                    conn.commit()
            if session["role"] == "admin":
                return redirect(url_for("admin"))
            elif session["role"] == "user":
                return redirect(url_for("view_collector"))
        except IntegrityError as e:
            return render_template(
                "error.html", info=f"Unique constraint error: {e}", role=session["role"]
            )
        except Exception as e:
            return render_template(
                "error.html", info=f"Update error: {e}", role=session["role"]
            )
    else:
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM detail WHERE Id_no = %s", (item_id,))
                    item = cursor.fetchone()
                    print(item)
            if item:
                role = session["role"]
                return render_template("update.html", role=role, item=item)
            else:
                return render_template("error.html", info="Certificate not found"), 404
        except Exception as e:
            return render_template(
                "error.html",
                info=f"Update page loading error: {e}",
                role=session["role"],
            )


@app.route("/delete/<int:item_id>", methods=["GET"])
@login_required
def delete(item_id):
    if session["role"] == "admin":
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM detail WHERE id_no = %s", (item_id,))
            conn.commit()
            conn.close()
            return redirect(url_for("admin"))
        except Exception as e:
            return render_template(
                "error,html", info=f"An error occurred: {str(e)}", role=session["role"]
            )


@app.route("/piechart")
def generate_pie_chart():
    try:
        chart_type = request.args.get("chart", "all")

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
            plt.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=140)
            plt.axis("equal")
            plt.savefig(f"static/{filename}")
            plt.close()

        generate_chart(data, "pie_chart.png")
        generate_chart(data1, "pie_chart1.png")
        generate_chart(data2, "pie_chart2.png")
        role = session["role"]

        return render_template("piechart.html", chart_type=chart_type, role=role)
    except Exception as e:
        return render_template(
            "error,html", info=f"An error occurred: {str(e)}", role=session["role"]
        )


@app.route("/reasonpiechart")
@login_required
def generate_reason_pie_chart():
    try:

        def fetch_data():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT reason_for_uneducated FROM detail where reason_for_uneducated <> '0' "
            )
            data = cursor.fetchall()
            cursor.execute(
                "SELECT reason_for_unemployment from detail where reason_for_unemployment <> '0'"
            )
            data1 = cursor.fetchall()
            cursor.execute(
                "SELECT reason_for_abroad from detail where reason_for_abroad <> '0'"
            )
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
            plt.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=140)
            plt.axis("equal")
            plt.savefig(f"static/{filename}")
            plt.close()

        generate_chart(data, "pie_chart3.png")
        generate_chart(data1, "pie_chart4.png")
        generate_chart(data2, "pie_chart5.png")
        role = session["role"]

        return render_template("reasonpiechart.html", role=role)
    except Exception as e:
        return render_template("error.html", info=str(e), role=session["role"])


@app.route("/message", methods=["GET", "POST"])
@login_required
def meesage():
    role = session["role"]
    return render_template("message.html", role=role)


@app.route("/messagesubmit", methods=["GET", "POST"])
@login_required
def meesagesubmit():
    subject = request.form.get("subject")
    message = request.form.get("message")
    userid = session["user_id"]
    username = session["username"]
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO message(subject, message, user_id,username)
                        VALUES (%s, %s, %s, %s)""",
                    (subject, message, userid, username),
                )
                conn.commit()
        return redirect("/home")

    except Exception as e:
        return render_template("error.html", info=str(e), role=session["role"])


@app.route("/messageview", methods=["Get", "POST"])
@login_required
def messagedview():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("Select * from message")
                items = cursor.fetchall()
                role = session["role"]
        return render_template("messageview.html", items=items, role=role)

    except Exception as e:
        return render_template("error.html", info=str(e), role=session["role"])


@app.route("/reasonbargraph", methods=["POST", "GET"])
@login_required
def generate_reason_bar_graph():
    role = session["role"]
    try:
        criteria1 = request.form.get("criteria1")
        criteria2 = request.form.get("criteria2")
        print(criteria1, criteria2)

        def fetch_data():
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT {criteria1}, {criteria2} FROM detail")
            data = cursor.fetchall()
            cursor.close()
            conn.close()
            return data

        data = fetch_data()

        def generate_chart(data, filename, x, y):
            df = pd.DataFrame(data, columns=[x, y])
            print(df)

            plt.figure(figsize=(10, 6))
            sns.countplot(x=x, hue=y, data=df)

            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(f"static/{filename}")
            plt.close()

        generate_chart(data, "bar_chart1.png", criteria1, criteria2)

        return render_template(
            "bargraph.html",
            role=role,
            criteria1=criteria1.upper(),
            criteria2=criteria2.upper(),
        )
    except Exception as e:
        return render_template("error.html", info=str(e), role=role)


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload_file():
    role = session["role"]

    if request.method == "POST":
        # Check if the POST request has the file part
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files["file"]
        # If the user does not select a file, the browser submits an empty file without a filename
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        if file:
            # Save the file to a temporary location on the server
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            # Process the CSV file and insert data into the database
            process_csv_file(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            return render_template(
                "import.html", role=role, e="Data Imported successfully"
            )

    return render_template("import.html")


def process_csv_file(file_path):
    # Open and read the CSV file
    with open(file_path, "r") as csvfile:
        csvreader = csv.reader(csvfile)
        # Skip the header row if it exists
        next(csvreader)
        # Iterate over each row in the CSV file
        for row in csvreader:
            # Extract data from the row
            name = row[0]
            mothername = row[1]
            fathername = row[2]
            grandfathername = row[3]
            dob = row[4]
            gender = row[5]
            education = row[7]
            employeed = row[8]
            abroad = row[9]
            date = row[6]
            reason_for_unemployment = row[10]
            reason_for_uneducated = row[11]
            reason_for_abroad = row[12]
            userid = row[13]
            # Extract other fields and insert into the database using SQL INSERT statements
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            INSERT INTO detail(
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
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s)""",
                            (
                                name,
                                fathername,
                                mothername,
                                grandfathername,
                                dob,
                                gender,
                                education,
                                employeed,
                                abroad,
                                date,
                                reason_for_unemployment,
                                reason_for_uneducated,
                                reason_for_abroad,
                                userid,
                            ),
                        )
                        conn.commit()
            except Exception as e:
                conn.rollback()
                return str(e)

    # Open and read the CSV file
    with open(file_path, "r") as csvfile:
        csvreader = csv.reader(csvfile)
        # Skip the header row if it exists
        next(csvreader)
        # Iterate over each row in the CSV file
        for row in csvreader:
            # Extract data from the row
            name = row[0]
            mothername = row[1]
            fathername = row[2]
            grandfathername = row[3]
            dob = row[4]
            gender = row[5]
            education = row[7]
            employeed = row[8]
            abroad = row[9]
            date = row[6]
            reason_for_unemployment = row[10]
            reason_for_uneducated = row[11]
            reason_for_abroad = row[12]
            userid = row[13]
            # Extract other fields and insert into the database using SQL INSERT statements
            # Insert data into the database using SQL INSERT statements
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            INSERT INTO detail(
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
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s)""",
                            (
                                name,
                                fathername,
                                mothername,
                                grandfathername,
                                dob,
                                gender,
                                education,
                                employeed,
                                abroad,
                                date,
                                reason_for_unemployment,
                                reason_for_uneducated,
                                reason_for_abroad,
                                userid,
                            ),
                        )
                        conn.commit()
                        return redirect("/dataform")
            except Exception as e:
                conn.rollback()
                return str(e)


if __name__ == "__main__":
    app.run(debug=True)


@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=False)
