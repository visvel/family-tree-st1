import streamlit as st
import sqlite3
import json
import os
from streamlit.components.v1 import html
from collections import deque

st.set_page_config(layout='wide')
DB_PATH = "family_tree.db"

# Ensure database exists
if not os.path.exists(DB_PATH):
    st.error("❌ SQLite database not found.")
    st.stop()

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# --- Normalize IDs ---
def normalize_id(raw):
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return str(int(float(raw)))
    except:
        return str(raw).strip()

# --- Read ID from URL ---
params = st.query_params
query_id = normalize_id(params.get("id", "22"))
st.write(f"🆔 Query ID: {query_id}")

# --- Init State ---
if "root_id" not in st.session_state:
    st.session_state.root_id = query_id
if "parent_queue" not in st.session_state:
    st.session_state.parent_queue = deque([query_id])
if "child_queue" not in st.session_state:
    st.session_state.child_queue = deque([query_id])
if "node_map" not in st.session_state:
    st.session_state.node_map = {}
if "top_nodes" not in st.session_state:
    st.session_state.top_nodes = set([query_id])
if "show_parents" not in st.session_state:
    st.session_state.show_parents = False
if "show_children" not in st.session_state:
    st.session_state.show_children = False

# --- Helpers ---
def fetch_person(uid):
    uid = normalize_id(uid)
    st.write(f"🔍 Fetching person: {uid}")
    cursor.execute("SELECT * FROM people WHERE id = ?", (uid,))
    return cursor.fetchone()

def build_node(uid):
    uid = normalize_id(uid)
    if uid in st.session_state.node_map:
        return st.session_state.node_map[uid]
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
    st.write(f"✅ Created node: {uid} - {node['name']}")
    return node

# --- Root Initialization ---
if st.session_state.root_id not in st.session_state.node_map:
    st.write(f"🧱 Initializing root node {st.session_state.root_id}")
    build_node(st.session_state.root_id)

# --- Expand Parents ---
def expand_parents():
    st.write("🔼 Expanding parents for:", list(st.session_state.parent_queue))
    new_parents = set()
    for _ in range(len(st.session_state.parent_queue)):
        uid = normalize_id(st.session_state.parent_queue.popleft())
        node = st.session_state.node_map.get(uid)
        person = fetch_person(uid)
        if not person or not node:
            continue
        for parent_id in [person["father_id"], person["mother_id"]]:
            pid = normalize_id(parent_id)
            if pid and pid not in st.session_state.node_map:
                parent_node = build_node(pid)
                if parent_node:
                    parent_node["children"].append(node)
                    new_parents.add(pid)
            elif pid:
                existing = st.session_state.node_map[pid]
                if node not in existing["children"]:
                    existing["children"].append(node)
                new_parents.add(pid)
    st.session_state.parent_queue.extend(new_parents)
    st.session_state.top_nodes = new_parents or st.session_state.top_nodes

# --- Expand Children ---
def expand_children():
    st.write("🔽 Expanding children for:", list(st.session_state.child_queue))
    to_add = deque()
    for _ in range(len(st.session_state.child_queue)):
        uid = normalize_id(st.session_state.child_queue.popleft())
        node = st.session_state.node_map.get(uid)
        person = fetch_person(uid)
        if not person or not node or not person["children_ids"]:
            continue
        child_ids = [normalize_id(cid) for cid in person["children_ids"].split(";") if cid.strip()]
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

# --- Buttons ---
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("+ Show Parents"):
        st.session_state.show_parents = True
with col2:
    if st.button("- Show Children"):
        st.session_state.show_children = True

# --- Handle Expansions ---
if st.session_state.show_parents:
    st.session_state.show_parents = False
    expand_parents()

if st.session_state.show_children:
    st.session_state.show_children = False
    expand_children()

# --- Render from Virtual Root ---
def render_virtual_root():
    top_nodes = list(st.session_state.top_nodes)
    children = []
    for tid in top_nodes:
        node = st.session_state.node_map.get(tid)
        if node:
            children.append(node)
    return {
        "name": "Family Tree Root",
        "title": "Virtual Root",
        "children": children
    }

tree_data = render_virtual_root()

# --- D3 Rendering ---
if not tree_data["children"]:
    st.error("❌ No data available to render.")
else:
    with open("d3_family_tree_template.html", "r") as f:
        d3_template = f.read()
    rendered_html = d3_template.replace("{{DATA}}", json.dumps(tree_data))
    html(rendered_html, height=800, scrolling=True)
