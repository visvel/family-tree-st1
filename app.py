import streamlit as st
import sqlite3
import json
import os
from streamlit.components.v1 import html

DB_PATH = "family_tree.db"

st.set_page_config(layout='wide')

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

def fetch_person(uid):
    cursor.execute("SELECT * FROM people WHERE id = ?", (uid,))
    return cursor.fetchone()

def build_tree(uid):
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

    spouse = fetch_person(person["spouse_id"]) if person["spouse_id"] else None
    if spouse:
        node["spouse"] = {
            "name": spouse["name"],
            "gender": spouse["gender"],
            "title": f"Valavu: {spouse['valavu']}\nNotes: {spouse['notes']}"
        }

    if person["children_ids"]:
        child_ids = [c.strip() for c in person["children_ids"].split(";") if c.strip()]
        node["children"] = [build_tree(c) for c in child_ids if build_tree(c)]

    return node

tree_data = build_tree(uid)
if not tree_data:
    st.error(f"No person found with ID {uid}")
    st.stop()

# Display using D3.js
with open("d3_family_tree_template.html", "r") as f:
    d3_template = f.read()

d3_render = d3_template.replace("{{DATA}}", json.dumps(tree_data))
html(d3_render, height=800, scrolling=True)
