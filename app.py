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
if "couple_map" not in st.session_state:
    st.session_state.couple_map = {}
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

# --- DB Helpers ---
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
        "is_couple": False
    }
    st.session_state.node_map[uid] = node
    return node

def build_couple_node(father_id, mother_id):
    cid = f"couple_{father_id}_{mother_id}"
    if cid in st.session_state.node_map:
        return st.session_state.node_map[cid]

    couple_node = {
        "id": cid,
        "name": "",
        "title": "",
        "children": [],
        "is_couple": True,
        "father": build_node(father_id),
        "mother": build_node(mother_id)
    }
    st.session_state.node_map[cid] = couple_node
    st.session_state.couple_map[cid] = couple_node
    return couple_node

# --- Tree Construction ---
build_node(query_id)

def expand_parents():
    current_top_ids = list(st.session_state.top_ids)
    new_parents = set()

    for uid in current_top_ids:
        child = build_node(uid)
        person = fetch_person(uid)
        if not person or not child:
            continue

        father_id = normalize_id(person["father_id"])
        mother_id = normalize_id(person["mother_id"])

        if not father_id and not mother_id:
            continue

        couple_node = build_couple_node(father_id or "NA", mother_id or "NA")
        if child not in couple_node["children"]:
            couple_node["children"].append(child)

        new_parents.update(filter(None, [father_id, mother_id]))

    st.session_state.top_ids = new_parents.union(st.session_state.top_ids)
    st.session_state.parent_queue.extend(new_parents)

def expand_children():
    new_children = set()
    leaf_ids = [uid for uid in st.session_state.node_map if not st.session_state.node_map[uid]["children"] and not st.session_state.node_map[uid].get("is_couple")]
    for uid in leaf_ids:
        parent = build_node(uid)
        person = fetch_person(uid)
        if not person or not person["children_ids"]:
            continue
        for cid in [normalize_id(c) for c in person["children_ids"].split(";") if c.strip()]:
            child = build_node(cid)
            if child and child not in parent["children"]:
                parent["children"].append(child)
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

# --- Tree Root + Clean ---
def find_root_candidates():
    has_parents = set()
    for node in st.session_state.node_map.values():
        for child in node.get("children", []):
            has_parents.add(child["id"])
    return [n for n in st.session_state.node_map if n not in has_parents]

def build_tree_forest():
    forest = []
    for rid in find_root_candidates():
        root = st.session_state.node_map[rid]
        forest.append(root)
    return { "name": "root", "children": forest }

def clean_tree(node):
    if node.get("is_couple"):
        return {
            "name": "Parents",
            "title": "",
            "children": [
                {
                    "name": node.get("father", {}).get("name", ""),
                    "title": node.get("father", {}).get("title", "")
                },
                {
                    "name": node.get("mother", {}).get("name", ""),
                    "title": node.get("mother", {}).get("title", "")
                },
                {
                    "name": "",
                    "title": "",
                    "children": [clean_tree(child) for child in node.get("children", [])]
                }
            ]
        }
    return {
        "name": node.get("name", ""),
        "title": node.get("title", ""),
        "children": [clean_tree(child) for child in node.get("children", [])]
    }

# --- Render ---
tree_data = build_tree_forest()

if not tree_data["children"]:
    st.error("❌ No data to render.")
else:
    with open("d3_family_tree_template.html", "r") as f:
        d3_template = f.read()
    safe_tree = clean_tree(tree_data)
    rendered_html = d3_template.replace("{{DATA}}", json.dumps(safe_tree))
    html(rendered_html, height=800, scrolling=True)
