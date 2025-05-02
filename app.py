import streamlit as st
import sqlite3
import json
import os
from streamlit.components.v1 import html
from collections import deque

st.set_page_config(layout='wide')
DB_PATH = "family_tree.db"

# Ensure the database exists
if not os.path.exists(DB_PATH):
    st.error("SQLite database not found.")
    st.stop()

# Connect to SQLite
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Read ID from URL
params = st.query_params
query_id = params.get("id", "22")
if isinstance(query_id, list):
    query_id = query_id[0]
query_id = str(query_id).strip()
st.write(f"🆔 Query ID: {query_id}")

# Initialize state
if "current_id" not in st.session_state:
    st.session_state.current_id = query_id
if "parent_queue" not in st.session_state:
    st.session_state.parent_queue = deque([query_id])
if "child_queue" not in st.session_state:
    st.session_state.child_queue = deque([query_id])
if "tree_roots" not in st.session_state:
    st.session_state.tree_roots = [query_id]

# Data fetch helper
def fetch_person(uid):
    cursor.execute("SELECT * FROM people WHERE id = ?", (uid,))
    return cursor.fetchone()

# Build a single person node
def build_tree(uid):
    person = fetch_person(uid)
    if not person:
        return None
    return {
        "name": person["name"],
        "id": person["id"],
        "gender": person["gender"],
        "valavu": person["valavu"],
        "notes": person["notes"],
        "title": f"Valavu: {person['valavu']}\\nNotes: {person['notes']}",
        "children": []
    }

# Expand parents queue
def expand_parents():
    new_ids = set()
    for _ in range(len(st.session_state.parent_queue)):
        uid = st.session_state.parent_queue.popleft()
        person = fetch_person(uid)
        if not person:
            continue
        for pid in [person["father_id"], person["mother_id"]]:
            if pid and pid not in st.session_state.tree_roots:
                st.session_state.tree_roots.insert(0, pid)
                new_ids.add(pid)
    st.session_state.parent_queue.extend(new_ids)

# Expand children queue
def expand_children():
    new_ids = set()
    for _ in range(len(st.session_state.child_queue)):
        uid = st.session_state.child_queue.popleft()
        person = fetch_person(uid)
        if not person or not person["children_ids"]:
            continue
        child_ids = [cid.strip() for cid in person["children_ids"].split(";") if cid.strip()]
        for cid in child_ids:
            if cid not in st.session_state.tree_roots:
                st.session_state.tree_roots.append(cid)
                new_ids.add(cid)
    st.session_state.child_queue.extend(new_ids)

# Buttons to expand
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("+ Show Parents"):
        expand_parents()
with col2:
    if st.button("- Show Children"):
        expand_children()

# Build complete tree for rendering
def build_full_tree():
    nodes = {}
    for uid in st.session_state.tree_roots:
        person = fetch_person(uid)
        if not person:
            continue
        node = build_tree(uid)
        if person["children_ids"]:
            child_ids = [cid.strip() for cid in person["children_ids"].split(";") if cid.strip()]
            node["children"] = [build_tree(cid) for cid in child_ids if build_tree(cid)]
        nodes[uid] = node
    return {"name": "Family Tree", "children": list(nodes.values())}

tree_data = build_full_tree()

# Render with D3
if not tree_data or not tree_data["children"]:
    st.error("No data to render.")
else:
    with open("d3_family_tree_template.html", "r") as f:
        d3_template = f.read()
    d3_render = d3_template.replace("{{DATA}}", json.dumps(tree_data))
    html(d3_render, height=800, scrolling=True)
