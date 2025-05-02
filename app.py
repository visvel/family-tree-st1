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
query_id = normalize_id(params.get("id", "22"))
st.write(f"🆔 Query ID: {query_id}")

if not os.path.exists(DB_PATH):
    st.error("❌ SQLite database not found.")
    st.stop()

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Initialize state
if "root_id" not in st.session_state:
    st.session_state.root_id = query_id
if "node_map" not in st.session_state:
    st.session_state.node_map = {}
if "child_queue" not in st.session_state:
    st.session_state.child_queue = deque([query_id])
if "parent_queue" not in st.session_state:
    st.session_state.parent_queue = deque([query_id])
if "virtual_root" not in st.session_state:
    st.session_state.virtual_root = query_id
if "show_parents" not in st.session_state:
    st.session_state.show_parents = False
if "show_children" not in st.session_state:
    st.session_state.show_children = False

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
        "children": []
    }
    st.session_state.node_map[uid] = node
    return node

# Initial root node
if st.session_state.root_id not in st.session_state.node_map:
    build_node(st.session_state.root_id)

def expand_parents():
    to_add = deque()
    for _ in range(len(st.session_state.parent_queue)):
        uid = normalize_id(st.session_state.parent_queue.popleft())
        child_node = build_node(uid)
        person = fetch_person(uid)
        if not person:
            continue

        father = normalize_id(person["father_id"])
        mother = normalize_id(person["mother_id"])

        if not father and not mother:
            continue

        couple_id = f"couple_{father}_{mother}"
        if couple_id not in st.session_state.node_map:
            couple_node = {
                "id": couple_id,
                "name": "",
                "children": [child_node],
                "is_couple": True
            }
            if father:
                father_node = build_node(father)
                couple_node["father"] = father_node
            if mother:
                mother_node = build_node(mother)
                couple_node["mother"] = mother_node
            st.session_state.node_map[couple_id] = couple_node
        else:
            couple_node = st.session_state.node_map[couple_id]
            if child_node not in couple_node["children"]:
                couple_node["children"].append(child_node)
        to_add.extend([father, mother])
        st.session_state.virtual_root = couple_id  # re-root tree at topmost couple

    st.session_state.parent_queue.extend(filter(None, to_add))

def expand_children():
    to_add = deque()
    for _ in range(len(st.session_state.child_queue)):
        uid = normalize_id(st.session_state.child_queue.popleft())
        parent_node = build_node(uid)
        person = fetch_person(uid)
        if not person or not person["children_ids"]:
            continue
        child_ids = [normalize_id(cid) for cid in person["children_ids"].split(";") if cid]
        for cid in child_ids:
            child_node = build_node(cid)
            if child_node and child_node not in parent_node["children"]:
                parent_node["children"].append(child_node)
                to_add.append(cid)
    st.session_state.child_queue.extend(to_add)

# Buttons
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

# Tree render logic
def render_tree(root_id):
    root = st.session_state.node_map.get(root_id)
    if not root:
        return None
    if root.get("is_couple"):
        children = root["children"]
        return {
            "name": "",
            "children": [
                {
                    "name": root["father"]["name"] if "father" in root else "",
                    "title": root["father"]["title"] if "father" in root else "",
                    "children": []
                },
                {
                    "name": root["mother"]["name"] if "mother" in root else "",
                    "title": root["mother"]["title"] if "mother" in root else "",
                    "children": []
                },
                {
                    "name": "▼",
                    "children": children
                }
            ]
        }
    return root

tree_data = render_tree(st.session_state.virtual_root)

if not tree_data:
    st.error("❌ No data to render.")
else:
    with open("d3_family_tree_template.html", "r") as f:
        d3_template = f.read()
    rendered_html = d3_template.replace("{{DATA}}", json.dumps(tree_data))
    html(rendered_html, height=800, scrolling=True)
