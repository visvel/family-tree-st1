import streamlit as st
import sqlite3
import json
import os
from streamlit.components.v1 import html

st.set_page_config(layout='wide')
DB_PATH = "family_tree.db"

if not os.path.exists(DB_PATH):
    st.error("SQLite database not found.")
    st.stop()

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

params = st.query_params
uid = params.get("id", "22")
if isinstance(uid, list):
    uid = uid[0]
uid = str(uid).strip()

# -- State Management --
if "current_id" not in st.session_state:
    st.session_state.current_id = uid
if "expand_parents" not in st.session_state:
    st.session_state.expand_parents = False
if "expand_children" not in st.session_state:
    st.session_state.expand_children = True  # default shows children

# -- Fetch Data --
def fetch_person(uid):
    cursor.execute("SELECT * FROM people WHERE id = ?", (uid,))
    return cursor.fetchone()

def build_tree(uid, expand_up=False, expand_down=True):
    person = fetch_person(uid)
    if not person:
        return None

    node = {
        "name": person["name"],
        "id": person["id"],
        "gender": person["gender"],
        "valavu": person["valavu"],
        "notes": person["notes"],
        "title": f"Valavu: {person['valavu']}\nNotes: {person['notes']}",
        "children": []
    }

    # Expand downwards
    if expand_down and person["children_ids"]:
        child_ids = [c.strip() for c in person["children_ids"].split(";") if c.strip()]
        node["children"] = [build_tree(c, expand_up=False, expand_down=True) for c in child_ids if build_tree(c)]

    # Expand upwards (wrap parent nodes around this person)
    if expand_up:
        parents = []
        if person["father_id"]:
            father = build_tree(person["father_id"], expand_up=True, expand_down=False)
            if father:
                father["children"] = [node]
                parents.append(father)
        if person["mother_id"]:
            mother = build_tree(person["mother_id"], expand_up=True, expand_down=False)
            if mother:
                mother["children"] = [node]
                parents.append(mother)
        if parents:
            return {
                "name": "↑",
                "children": parents
            }

    return node

# Buttons
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("+ Show Parents"):
        st.session_state.expand_parents = True
with col2:
    if st.button("- Show Children"):
        st.session_state.expand_children = True

# Tree Data Build
tree_data = build_tree(
    st.session_state.current_id,
    expand_up=st.session_state.expand_parents,
    expand_down=st.session_state.expand_children
)

# Render with D3
if not tree_data:
    st.error(f"No person found with ID {uid}")
else:
    with open("d3_family_tree_template.html", "r") as f:
        d3_template = f.read()

    d3_render = d3_template.replace("{{DATA}}", json.dumps(tree_data))
    html(d3_render, height=800, scrolling=True)
