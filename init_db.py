import pandas as pd
import sqlite3

def init_db(excel_path, db_path):
    df = pd.read_excel(excel_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS people (
            id TEXT PRIMARY KEY,
            name TEXT,
            father_id TEXT,
            mother_id TEXT,
            spouse_id TEXT,
            children_ids TEXT,
            dob TEXT,
            valavu TEXT,
            alive TEXT,
            notes TEXT
        )
    ''')

    for _, row in df.iterrows():
        cursor.execute('''
            INSERT OR REPLACE INTO people (id, name, father_id, mother_id, spouse_id,
                children_ids, dob, valavu, alive, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(row['Unique ID']), row['Name'], row['Father ID'], row['Mother ID'],
            row['Spouse ID'], row['Children IDs'], row['DOB'], row['Valavu'],
            row['Alive'], row['Notes']
        ))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db("family_tree_synthetic.xlsx", "family_tree.db")
