import os
import json
import base64
import secrets
import string
import sqlite3
import streamlit as st
import pandas as pd
from user import User
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv


page_bg_img = f"""
<style>
[data-testid="stAppViewContainer"] > .main {{
background-image: url("https://img.freepik.com/premium-vector/padlock-security-cyber-digital-concept_42421-738.jpg?w=1800");
background-size: cover;
display: flex;
background-position: top left;
background-repeat: no-repeat;
background-attachment: local;
textColor: "white";
}}
[data-testid="stSidebarContent"] {{
background: rgba(0, 0, 0, 0)
}}
[data-testid="stHeader"]{{
background-color: rgba(0, 0, 0, 0);
}}
</style>
"""

# Database connection and Initializations

conn = sqlite3.connect("users.db")
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS app_credentials (
          app_name VARCHAR(20) NOT NULL,
          user_name VARCHAR(50) NOT NULL,
          pass_word VARCHAR(50) NOT NULL,
          primary key(app_name));
""")
conn.commit()

# Load the custom .env.app file 
if not st.secrets:
    load_dotenv(dotenv_path='.env.app')
    key = os.getenv("FERNET_KEY")
else:
    key = st.secrets["FERNET_KEY_TEST"]
# Initialize the Cipher
fernet = Fernet(key)


def encrypt_password(password):
    return fernet.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password):
    return fernet.decrypt(encrypted_password).decode()

def generate_strong_password(password_len=12):
    char_pool = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(char_pool) for i in range(password_len))
    return password

def insert_data(u):
    with conn:
        c.execute("INSERT INTO app_credentials VALUES(:app, :user, :pass)", 
                  {'app': u.app, 'user': u.username, 'pass': u.password})
        
def get_cred_by_app(app):
    with conn:
        c.execute("SELECT app_name, user_name, pass_word FROM app_credentials WHERE app_name= :name", {'name': app})
        return c.fetchone()
    
def remove_cred_by_app(app):
    with conn:
        c.execute("DELETE FROM app_credentials WHERE app_name = :name", {'name': app})

def update_cred_by_app(app, new_password):
    with conn:
        c.execute("UPDATE app_credentials SET pass_word = :pass WHERE app_name = :name", {'name': app, 'pass': new_password})

# Application Code 
def main():
    # Loading Page styles
    st.markdown(page_bg_img, unsafe_allow_html=True)

    st.title("My Password Manager")
    st.markdown("---")

    # Fetch DB info
    c.execute("SELECT COUNT(*) FROM app_credentials;")
    db_size = c.fetchone()[0]

    c.execute("SELECT app_name FROM app_credentials;")
    app_names_raw = c.fetchall()
    app_names = [i[0] for i in app_names_raw]

    # Create sidebar menu
    radio_option = st.sidebar.radio("Menu", options=[
        "Home",
        "Add Account",
        "Update Password",
        "Delete Account",
        "Generate Password"
    ])

    # Render pages based on selection
    match radio_option:
        case "Home":
            st.subheader("Find Credential 🔎")
            if db_size > 0:
                # Populate application names
                option = st.selectbox('Select Application 📱', app_names)

                if st.button('Fetch credentials 👇', use_container_width=True):

                    # Function to get credentials by taking application name selected
                    cred = get_cred_by_app(option)

                    stored_password = cred[2]
                    decrypted_password = decrypt_password(stored_password)

                    with st.container():
                        st.text(f"Username 👤")
                        st.code(f"{cred[1]}", language="python")
                        st.text_input('Password 🔑', value=decrypted_password, type="password")
            else:
                # Display error message when db is empty
                st.info('Database is empty.', icon="ℹ️")

        case "Add Account":
            st.subheader("Add New Credential: ")
            app_name = st.text_input('Application 📱', 'Facebook')
            user_name = st.text_input('User Name 👤', 'johndoe@email.com')
            pass_word = st.text_input('Password 🔑', 'pass123', type="password")

            encrypted_password = encrypt_password(pass_word)

            if st.button('Save ⬇', use_container_width=True):
                try:
                    data = User(app_name, user_name, encrypted_password)
                    insert_data(data)
                    st.success(f"{app_name}'s credentials are added successfully to the database!", icon="✅")
                except Exception as e:
                    print(e)
                    st.warning("Uh-Oh! Something went wrong, please try again", icon="❗")


            # Display current size of the database
            st.info(f"Available credentials in database: {db_size}")

        case "Update Password":
            st.subheader("Update Password 🔃")
            # Check if there are any credentials stored in database
            if db_size > 0:
                update_app_name = st.selectbox('Select an account you want to update 👇', app_names)
                new_password1 = st.text_input('New Password', 'new123', type="password")
                new_password2 = st.text_input('Confirm New Password', 'new123', type="password")
                if new_password1 == new_password2:
                    encrypted_new_password = encrypt_password(new_password1)
                    if st.button('Update ⚡', use_container_width=True):
                        try:
                            update_cred_by_app(update_app_name, encrypted_new_password)
                            st.success(f"{update_app_name}'s password is updated!", icon="✅")
                        except:
                            st.warning("There was a problem updating the database, please try again!", icon="⚠️")
                else:
                    st.warning("Passwords don't match! Try again.", icon="❗")

            else:
                st.info('Database is empty.', icon="ℹ️")

        case "Delete Account":
            st.subheader("Delete Credential 🗑")
            if db_size > 0:
                view_full_db = st.checkbox('View Full Database')
                if view_full_db:
                    # Display information in table format
                    c.execute("SELECT APP_NAME FROM app_credentials")
                    results = c.fetchall()
                    results_df = pd.DataFrame(results, columns = ['Apps'])
                    st.dataframe(results_df)
                    # st.table(results)

                delete_option_selected = st.selectbox('Select an Account you want to delete 👇', app_names)
                if st.button('Delete ⛔', use_container_width=True):
                    try:
                        remove_cred_by_app(delete_option_selected)
                        st.success(f"{delete_option_selected}'s Credential is successfully removed from database!", 
                                    icon="✅")
                    except:
                        st.info('An error occurred, or the database is empty, Go to Add Account', icon='ℹ️')
            # Display information when db is empty
            else:
                st.info('Database is empty.', icon="ℹ️")
        
        case "Generate Password":
            st.header("Password Generator")
            password_length = st.slider("Select Password Length", min_value=8, max_value=32, value=12)
            if st.button("Generate Secure Password"):
                generated_password = generate_strong_password(password_length)
                st.success(f"Generated Password: {generated_password}")
                st.write("Tip: Use the generated password in the 'Add Account' section to store it securely.")
          

if __name__ == "__main__":
    main()