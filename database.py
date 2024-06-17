import psycopg2
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_db_connection():
    return psycopg2.connect(
   #for local
        # database="cms",
        # user="postgres",
        # password="@hybesty123",
        # host="127.0.0.1",
        # port=5432
        
        #for render.com
        
        database="cms_7j5a",
        user="cms_7j5a_user",
        password="MAFQ8hwWXNIo3JQIC3Zc2gqW8fPGdKhX",
        host="dpg-cpo6qpo8fa8c739n2ie0-a",
        port="5432"
    )
def database():
    email='raj@gmail.com'       
    password='admin'
    username='raj'
    hashed_password = hash_password(password)
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS LOGIN1(
            USER_ID SERIAL PRIMARY KEY NOT NULL,
            USERNAME VARCHAR(250) NOT NULL,
            EMAIL VARCHAR(250) NOT NULL UNIQUE,
            PASSWORD VARCHAR(250) NOT NULL,
            ROLE VARCHAR(250) NOT NULL
            );
            INSERT INTO LOGIN1 (username, password, email, role)
            SELECT %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM login1 WHERE email = %s
            );
            """, (username, hashed_password, email, 'admin', email)); 
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS Detail1 (
            Id_no SERIAL PRIMARY KEY NOT NULL,
            Certificate_no VARCHAR(250) NOT NULL,
            fullname VARCHAR(250) NOT NULL,
            mothername VARCHAR(250) NOT NULL,
            fathername VARCHAR(250) NOT NULL,
            grandfathername VARCHAR(250) NOT NULL,
            dob VARCHAR(250) NOT NULL,
            gender VARCHAR(250) NOT NULL,
            issueddate VARCHAR(250) NOT NULL,
            education VARCHAR(250) NOT NULL,
            employeed VARCHAR(250) NOT NULL,
            abroad VARCHAR(250) NOT NULL,
            reason_for_unemployment VARCHAR(250) DEFAULT '0',
            reason_for_uneducated VARCHAR(250) DEFAULT '0',
            reason_for_abroad VARCHAR(250) DEFAULT '0',
            USER_ID INT NOT NULL,
            FOREIGN KEY (USER_ID) REFERENCES login1 (USER_ID)
            );
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS message(
            subject varchar(250) not null,
            message varchar(250) not null,
            username varchar(250)not null,   
            USER_ID INT NOT NULL,
            FOREIGN KEY (USER_ID) REFERENCES login1 (USER_ID)
                );
            """)
            
        conn.commit()