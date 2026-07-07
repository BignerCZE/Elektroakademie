import sqlite3

conn = sqlite3.connect("db.sqlite3(backup).sqlite3")
cursor = conn.cursor()

cursor.execute("""
    SELECT
        q.id,
        q.text,
        c.text,
        c.is_correct
    FROM courses_question q
    JOIN courses_choice c
        ON c.question_id = q.id
    ORDER BY q.id, c.id
    LIMIT 15
""")

for question_id, question, answer, is_correct in cursor.fetchall():
    marker = "✓" if is_correct else "✗"

    print(f"Otázka {question_id}: {question}")
    print(f"  {marker} {answer}")
    print()

conn.close()