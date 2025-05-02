import streamlit as st
import sqlite3
import json
import os
from streamlit.components.v1 import html

st.set_page_config(layout='wide')
DB_PATH = "family_tree.db"

# Debug log
st.write("🔍 Starting family tree app")

if not os.path.exists(DB_PATH):
    st.error("SQLite database not found.")
    st.stop()

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Read URL parameter
params = st.query_params
query_id = params.get("id", "22")
if isinstance(query_id, list):
    query_id = query_id[0]
query_id = str(query_id).strip()
st.write(f"🆔 URL ID: {query_id}")

# State management
if "current_id" not in st.session_state:
    st.session_state.current_id = query_id
if "expand_parents" not in st.session_state:
    st.session_state.expand_parents = False
if "expand_children" not in st.session_state:
    st.session_state.expand_children = False

st.write(f"📍 Current ID in session: {st.session_state.current_id}")
st.write(f"⬆️ Expand Parents: {st.session_state.expand_parents}")
st.write(f"⬇️ Expand Children: {st.session_state.expand_children}")

# Fetch a person by ID
def fetch_person(uid):
    cursor.execute("SELECT * FROM people WHERE id = ?", (uid,))
    return cursor.fetchone()

# Build the tree data
def build_tree(uid, expand_up=False, expand_down=False):
    person = fetch_person(uid)
    if not person:
        st.warning(f"No person found for ID: {uid}")
        return None

    st.write(f"🔧 Building node for {person['name']} (ID: {uid})")

    node = {
        "name": person["name"],
        "id": person["id"],
        "gender": person["gender"],
        "valavu": person["valavu"],
        "notes": person["notes"],
        "title": f"Valavu: {person['valavu']}\\nNotes: {person['notes']}",
        "children": []
    }

    # Expand downward
    if expand_down and person["children_ids"]:
        child_ids = [c.strip() for c in person["children_ids"].split(";") if c.strip()]
        st.write(f"👶 Expanding children: {child_ids}")
        node["children"] = [
            build_tree(c, expand_up=False, expand_down=False)
            for c in child_ids if build_tree(c)
        ]

    # Expand upward
    if expand_up:
        parents = []
        if person["father_id"]:
            st.write(f"👴 Adding father: {person['father_id']}")
            father = build_tree(person["father_id"], expand_up=True, expand_down=False)
            if father:
                father["children"] = [node]
                parents.append(father)
        if person["mother_id"]:
            st.write(f"👵 Adding mother: {person['mother_id']}")
            mother = build_tree(person["mother_id"], expand_up=True, expand_down=False)
            if mother:
                mother["children"] = [node]
                parents.append(mother)
        if parents:
            return {
                "name": "↑ Ancestors",
                "children": parents
            }

    return node

# Buttons to control expansion
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("+ Show Parents"):
        st.session_state.expand_parents = True
        st.session_state.expand_children = False
with col2:
    if st.button("- Show Children"):
        st.session_state.expand_children = True
        st.session_state.expand_parents = False

# Build and render the tree
tree_data = build_tree(
    st.session_state.current_id,
    expand_up=st.session_state.expand_parents,
    expand_down=st.session_state.expand_children
)

if not tree_data:
    st.error(f"No data to render for ID {st.session_state.current_id}")
else:
    with open("d3_family_tree_template.html", "r") as f:
        d3_template = f.read()

    d3_render = d3_template.replace("{{DATA}}", json.dumps(tree_data))
    html(d3_render, height=800, scrolling=True)
