import streamlit as st
import sqlite3
import json
import os
from streamlit.components.v1 import html
from collections import deque

st.set_page_config(layout='wide')
DB_PATH = "family_tree.db"

if not os.path.exists(DB_PATH):
    st.error("❌ SQLite database not found.")
    st.stop()

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# --- Get ID from URL ---
params = st.query_params
query_id = params.get("id", "22")
if isinstance(query_id, list):
    query_id = query_id[0]
query_id = str(query_id).strip()
st.write(f"🆔 URL query ID = {query_id}")

# --- Init State ---
if "root_id" not in st.session_state:
    st.session_state.root_id = query_id
if "parent_queue" not in st.session_state:
    st.session_state.parent_queue = deque([query_id])
if "child_queue" not in st.session_state:
    st.session_state.child_queue = deque([query_id])
if "node_map" not in st.session_state:
    st.session_state.node_map = {}
if "show_parents" not in st.session_state:
    st.session_state.show_parents = False
if "show_children" not in st.session_state:
    st.session_state.show_children = False

# --- Fetch & Build Node ---
def fetch_person(uid):
    st.write(f"🔍 Fetching person: {uid}")
    cursor.execute("SELECT * FROM people WHERE id = ?", (uid,))
    return cursor.fetchone()

def build_node(uid):
    person = fetch_person(uid)
    if not person:
        st.warning(f"⚠️ No person found for ID: {uid}")
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
    st.write(f"✅ Node created for {uid}: {node['name']}")
    return node

# --- Root Init ---
if st.session_state.root_id not in st.session_state.node_map:
    st.write(f"🧱 Initializing root node {st.session_state.root_id}")
    build_node(st.session_state.root_id)

# --- Expand Parents ---
def expand_parents():
    st.write("🔼 Expanding parents for queue:", list(st.session_state.parent_queue))
    to_add = deque()
    for _ in range(len(st.session_state.parent_queue)):
        uid = st.session_state.parent_queue.popleft()
        node = st.session_state.node_map.get(uid)
        person = fetch_person(uid)
        if not person or not node:
            continue
        for parent_id in [person["father_id"], person["mother_id"]]:
            if parent_id:
                if parent_id not in st.session_state.node_map:
                    parent_node = build_node(parent_id)
                    if parent_node:
                        parent_node["children"].append(node)
                        to_add.append(parent_id)
                else:
                    existing = st.session_state.node_map[parent_id]
                    if node not in existing["children"]:
                        existing["children"].append(node)
    st.session_state.parent_queue.extend(to_add)

# --- Expand Children ---
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
                    to_add.append(cid)
            else:
                existing = st.session_state.node_map[cid]
                if existing not in node["children"]:
                    node["children"].append(existing)
    st.session_state.child_queue.extend(to_add)

# --- UI Buttons ---
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("+ Show Parents"):
        st.session_state.show_parents = True
with col2:
    if st.button("- Show Children"):
        st.session_state.show_children = True

# --- Trigger expansion ---
if st.session_state.show_parents:
    st.session_state.show_parents = False
    expand_parents()

if st.session_state.show_children:
    st.session_state.show_children = False
    expand_children()

# --- Render Final Tree ---
def render_tree(uid):
    return st.session_state.node_map.get(uid)

tree_data = render_tree(st.session_state.root_id)

if not tree_data:
    st.error("❌ No data available to render the tree.")
else:
    with open("d3_family_tree_template.html", "r") as f:
        d3_template = f.read()
    rendered_html = d3_template.replace("{{DATA}}", json.dumps(tree_data))
    html(rendered_html, height=800, scrolling=True)
