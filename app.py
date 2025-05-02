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
if "root_id" not in st.session_state:
    st.session_state.root_id = query_id
if "parent_queue" not in st.session_state:
    st.session_state.parent_queue = deque([query_id])
if "child_queue" not in st.session_state:
    st.session_state.child_queue = deque([query_id])
if "node_map" not in st.session_state:
    st.session_state.node_map = {}

# Fetch a person by ID
def fetch_person(uid):
    cursor.execute("SELECT * FROM people WHERE id = ?", (uid,))
    return cursor.fetchone()

# Create a new node for a person
def build_node(uid):
    person = fetch_person(uid)
    if not person:
        return None
    node = {
        "id": uid,
        "name": person["name"],
        "valavu": person["valavu"],
        "notes": person["notes"],
        "title": f"Valavu: {person['valavu']}\\nNotes: {person['notes']}",
        "children": []
    }
    st.session_state.node_map[uid] = node
    return node

# Initialize root node
if st.session_state.root_id not in st.session_state.node_map:
    root_node = build_node(st.session_state.root_id)

# Expand parents of nodes in parent_queue
def expand_parents():
    st.write("🔼 Expanding parents for queue:", list(st.session_state.parent_queue))
    to_add = deque()
    for _ in range(len(st.session_state.parent_queue)):
        uid = st.session_state.parent_queue.popleft()
        node = st.session_state.node_map.get(uid)
        person = fetch_person(uid)
        if not person or not node:
            continue
        parent_nodes = []
        for parent_id in [person["father_id"], person["mother_id"]]:
            if parent_id and parent_id not in st.session_state.node_map:
                parent_node = build_node(parent_id)
                if parent_node:
                    parent_node["children"].append(node)
                    parent_nodes.append(parent_node)
                    to_add.append(parent_id)
        # If already in map, attach this node to them
        for parent_id in [person["father_id"], person["mother_id"]]:
            parent_node = st.session_state.node_map.get(parent_id)
            if parent_node and node not in parent_node["children"]:
                parent_node["children"].append(node)
    st.session_state.parent_queue.extend(to_add)

# Expand children of nodes in child_queue
def expand_children():
    st.write("🔽 Expanding children for queue:", list(st.session_state.child_queue))
    to_add = deque()
    for _ in range(len(st.session_state.child_queue)):
        uid = st.session_state.child_queue.popleft()
        node = st.session_state.node_map.get(uid)
        person = fetch_person(uid)
        if not person or not node or not person["children_ids"]:
            continue
        child_ids = [cid.strip() for cid in person["children_ids"].split(";") if cid.strip()]
        for cid in child_ids:
            if cid not in st.session_state.node_map:
                child_node = build_node(cid)
                if child_node:
                    node["children"].append(child_node)
