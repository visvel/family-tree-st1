import streamlit as st
import sqlite3
import json
import os
from streamlit.components.v1 import html
from collections import deque

st.set_page_config(layout='wide')
DB_PATH = "family_tree.db"

def normalize_id(raw):
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return str(int(float(raw)))
    except:
        return str(raw).strip()

params = st.query_params
query_id = normalize_id(params.get("id"))
if not query_id:
    st.error("❗ Missing `id` parameter in URL. Use ?id=UNIQUE_ID.")
    st.stop()

if not os.path.exists(DB_PATH):
    st.error("❌ SQLite database not found.")
    st.stop()

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# --- Init State ---
if "node_map" not in st.session_state:
    st.session_state.node_map = {}
if "parent_queue" not in st.session_state:
    st.session_state.parent_queue = deque([query_id])
if "child_queue" not in st.session_state:
    st.session_state.child_queue = deque([query_id])
if "top_ids" not in st.session_state:
    st.session_state.top_ids = set([query_id])
if "show_parents" not in st.session_state:
    st.session_state.show_parents = False
if "show_children" not in st.session_state:
    st.session_state.show_children = False

# --- Fetch + Build Node ---
def fetch_person(uid):
    uid = normalize_id(uid)
    cursor.execute("SELECT * FROM people WHERE id = ?", (uid,))
    return cursor.fetchone()

def build_node(uid):
    uid = normalize_id(uid)
    if uid in st.session_state.node_map:
        return st.session_state.node_map[uid]
    person = fetch_person(uid)
    if not person:
        return None
    node = {
        "id": uid,
        "name": person["name"],
        "valavu": person["valavu"],
        "notes": person["notes"],
        "title": f"Valavu: {person['valavu']}\\nNotes: {person['notes']}",
        "children": [],
        "parents": []
    }
    st.session_state.node_map[uid] = node
    return node

build_node(query_id)

# --- Expand Logic ---
def expand_parents():
    current_top_ids = list(st.session_state.top_ids)
    new_parents = set()

    for uid in current_top_ids:
        child = build_node(uid)
        person = fetch_person(uid)
        if not person or not child:
            continue
        for p_type in ["father_id", "mother_id"]:
            pid = normalize_id(person[p_type])
            if pid:
                parent_node = build_node(pid)
                if child not in parent_node["children"]:
                    parent_node["children"].append(child)
                if parent_node not in child["parents"]:
                    child["parents"].append(parent_node)
                new_parents.add(pid)
    st.session_state.top_ids = new_parents.union(st.session_state.top_ids)
    st.session_state.parent_queue.extend(new_parents)

def expand_children():
    new_children = set()
    leaf_ids = [uid for uid in st.session_state.node_map if not st.session_state.node_map[uid]["children"]]
    for uid in leaf_ids:
        parent = build_node(uid)
        person = fetch_person(uid)
        if not person or not person["children_ids"]:
            continue
        for cid in [normalize_id(c) for c in person["children_ids"].split(";") if c.strip()]:
            child = build_node(cid)
            if child and child not in parent["children"]:
                parent["children"].append(child)
                child["parents"].append(parent)
                new_children.add(cid)
    st.session_state.child_queue.extend(new_children)

# --- UI Buttons ---
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("+ Show Parents"):
        st.session_state.show_parents = True
with col2:
    if st.button("- Show Children"):
        st.session_state.show_children = True

if st.session_state.show_parents:
    st.session_state.show_parents = False
    expand_parents()

if st.session_state.show_children:
    st.session_state.show_children = False
    expand_children()

# --- Root builder ---
def find_root_candidates():
    all_nodes = st.session_state.node_map
    has_parents = set()
    for node in all_nodes.values():
        for c in node.get("children", []):
            has_parents.add(c["id"])
    roots = [n for n in all_nodes if n not in has_parents]
    return roots

def build_tree_forest():
    forest = []
    for rid in find_root_candidates():
        root = st.session_state.node_map[rid]
        forest.append(root)
    return { "name": "root", "children": forest }

tree_data = build_tree_forest()

# --- Clean tree for JSON serialization ---
def clean_tree(node, visited=None):
    if visited is None:
        visited = set()
    node_id = node.get("id") or node.get("name")
    if node_id in visited:
        return None
    visited.add(node_id)
    return {
        "name": node.get("name", ""),
        "title": node.get("title", ""),
        "children": list(filter(None, [clean_tree(child, visited.copy()) for child in node.get("children", [])]))
    }

# --- Render ---
if not tree_data["children"]:
    st.error("❌ No data to render.")
else:
    with open("d3_family_tree_template.html", "r") as f:
        d3_template = f.read()
    safe_tree = clean_tree(tree_data)
    rendered_html = d3_template.replace("{{DATA}}", json.dumps(safe_tree))
    html(rendered_html, height=800, scrolling=True)
