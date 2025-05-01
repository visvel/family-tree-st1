import streamlit as st
import sqlite3
import urllib.parse

st.set_page_config(layout='wide')

# Database connection
conn = sqlite3.connect("family_tree.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# URL Parameter
params = st.experimental_get_query_params()
uid = params.get("id", ["22"])[0]

def get_person(uid):
    cursor.execute("SELECT * FROM people WHERE id = ?", (uid,))
    return cursor.fetchone()

def get_persons_by_ids(id_list):
    ids = [i.strip() for i in id_list.split(';') if i.strip()]
    return [get_person(i) for i in ids if get_person(i)]

# State for level navigation
if "parent_uids" not in st.session_state:
    st.session_state.parent_uids = []
if "child_uids" not in st.session_state:
    st.session_state.child_uids = []

person = get_person(uid)

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

# Show Parents
st.markdown("### Parents")
for pid in st.session_state.parent_uids:
    p = get_person(pid)
    if p:
        st.write(f"👴 {p['name']} (ID: {p['id']})")

# Show Current Person
st.markdown("---")
st.markdown("### Current Person")
st.json(dict(person))

# Show Children
st.markdown("### Children")
for cid in st.session_state.child_uids:
    c = get_person(cid)
    if c:
        st.write(f"🧒 {c['name']} (ID: {c['id']})")
