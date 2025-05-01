import streamlit as st
import sqlite3
import os

st.set_page_config(layout='wide')

DB_PATH = "family_tree.db"

if not os.path.exists(DB_PATH):
    st.error("SQLite database not found. Please ensure 'family_tree.db' is in the root directory.")
    st.stop()

# Safe SQLite access across threads
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# --- Get ID from query parameter ---
params = st.query_params
uid = params.get("id", "22")  # default to 22
if isinstance(uid, list):  # handle multi-value
    uid = uid[0]
uid = str(uid).strip()

# --- Data access methods ---
def get_person(uid):
    try:
        cursor.execute("SELECT * FROM people WHERE id = ?", (uid,))
        return cursor.fetchone()
    except sqlite3.OperationalError as e:
        st.error(f"SQLite error: {e}")
        return None

def get_persons_by_ids(id_list):
    ids = [i.strip() for i in id_list.split(';') if i.strip()]
    return [get_person(i) for i in ids if get_person(i)]

# --- Session state ---
if "parent_uids" not in st.session_state:
    st.session_state.parent_uids = []
if "child_uids" not in st.session_state:
    st.session_state.child_uids = []

# --- Main person ---
person = get_person(uid)
if not person:
    st.error(f"No person found with ID: {uid}")
    st.stop()

# --- Page content ---
st.title("Family Tree Viewer")
st.subheader(f"Person: {person['name']} (ID: {uid})")

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("+ Show Parents"):
        if person["father_id"]:
            st.session_state.parent_uids.append(person["father_id"])
        if person["mother_id"]:
            st.session_state.parent_uids.append(person["mother_id"])

with col2:
    if st.button("- Show Children"):
        if person["children_ids"]:
            st.session_state.child_uids.extend(person["children_ids"].split(";"))

# --- Display Parents ---
st.markdown("### Parents")
for pid in st.session_state.parent_uids:
    p = get_person(pid)
    if p:
        st.write(f"👴 {p['name']} (ID: {p['id']})")

# --- Display Current ---
st.markdown("---")
st.markdown("### Current Person")
st.json(dict(person))

# --- Display Children ---
st.markdown("### Children")
for cid in st.session_state.child_uids:
    c = get_person(cid)
    if c:
        st.write(f"🧒 {c['name']} (ID: {c['id']})")
