import streamlit as st
import sqlite3
import pandas as pd
import os

DB_NAME = "autism_progress.db"

# --- THIS CREATES THE DATABASE AUTOMATICALLY ---
def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS APP_USER (
            user_id        INTEGER PRIMARY KEY,
            name           TEXT NOT NULL,
            email          TEXT UNIQUE NOT NULL,
            password_hash  TEXT NOT NULL,
            role           TEXT CHECK (role IN ('Parent','Consultant'))
        );
        CREATE TABLE IF NOT EXISTS CONSULTANT (
            consultant_id   INTEGER PRIMARY KEY,
            user_id         INTEGER NOT NULL,
            specialization  TEXT,
            FOREIGN KEY (user_id) REFERENCES APP_USER(user_id)
        );
        CREATE TABLE IF NOT EXISTS CHILD (
            child_id        INTEGER PRIMARY KEY,
            parent_id       INTEGER NOT NULL,
            name            TEXT NOT NULL,
            dob             TEXT NOT NULL,
            gender          TEXT,
            severity_level  INTEGER CHECK (severity_level BETWEEN 1 AND 3),
            diagnosed_by    TEXT,
            diagnosis_date  TEXT,
            FOREIGN KEY (parent_id) REFERENCES APP_USER(user_id)
        );
        CREATE TABLE IF NOT EXISTS PROBLEM (
            problem_id   INTEGER PRIMARY KEY,
            name         TEXT NOT NULL,
            description  TEXT
        );
        CREATE TABLE IF NOT EXISTS CHILD_PROBLEM (
            child_id       INTEGER NOT NULL,
            problem_id     INTEGER NOT NULL,
            identified_on  TEXT,
            PRIMARY KEY (child_id, problem_id),
            FOREIGN KEY (child_id) REFERENCES CHILD(child_id),
            FOREIGN KEY (problem_id) REFERENCES PROBLEM(problem_id)
        );
        CREATE TABLE IF NOT EXISTS GOAL (
            goal_id         INTEGER PRIMARY KEY,
            problem_id      INTEGER NOT NULL,
            severity_level  INTEGER CHECK (severity_level BETWEEN 1 AND 3),
            description     TEXT NOT NULL,
            FOREIGN KEY (problem_id) REFERENCES PROBLEM(problem_id)
        );
        CREATE TABLE IF NOT EXISTS ACTIVITY (
            activity_id   INTEGER PRIMARY KEY,
            goal_id       INTEGER NOT NULL,
            name          TEXT NOT NULL,
            instructions  TEXT,
            FOREIGN KEY (goal_id) REFERENCES GOAL(goal_id)
        );
        CREATE TABLE IF NOT EXISTS PROGRESS_LOG (
            log_id         INTEGER PRIMARY KEY,
            child_id       INTEGER NOT NULL,
            activity_id    INTEGER NOT NULL,
            recorded_by    INTEGER NOT NULL,
            log_date       TEXT NOT NULL,
            status         TEXT CHECK (status IN ('Not Attempted','Attempted','Completed')),
            parent_rating  INTEGER CHECK (parent_rating BETWEEN 1 AND 5),
            notes          TEXT,
            FOREIGN KEY (child_id) REFERENCES CHILD(child_id),
            FOREIGN KEY (activity_id) REFERENCES ACTIVITY(activity_id),
            FOREIGN KEY (recorded_by) REFERENCES APP_USER(user_id)
        );
        CREATE TABLE IF NOT EXISTS CONSULTANT_REVIEW (
            review_id           INTEGER PRIMARY KEY,
            log_id              INTEGER NOT NULL,
            consultant_id       INTEGER NOT NULL,
            consultant_rating   INTEGER CHECK (consultant_rating BETWEEN 1 AND 5),
            review_notes        TEXT,
            reviewed_on         TEXT,
            FOREIGN KEY (log_id) REFERENCES PROGRESS_LOG(log_id),
            FOREIGN KEY (consultant_id) REFERENCES CONSULTANT(consultant_id)
        );
    """)

    # Insert sample data only if empty
    cursor.execute("SELECT COUNT(*) FROM APP_USER")
    if cursor.fetchone()[0] == 0:
        cursor.executescript("""
            INSERT INTO APP_USER (name, email, password_hash, role) VALUES
            ('Ayesha Khan', 'ayesha@example.com', 'hashed_pw_1', 'Parent'),
            ('Dr. Bilal Ahmed', 'bilal@example.com', 'hashed_pw_2', 'Consultant'),
            ('Sara Malik', 'sara@example.com', 'hashed_pw_3', 'Parent'),
            ('Muhammad Ahmed', 'mahmed@example.com', 'hashed_pw_4', 'Parent');
            INSERT INTO CONSULTANT (user_id, specialization) VALUES (2, 'Child Behavioral Therapist');
            INSERT INTO CHILD (parent_id, name, dob, gender, severity_level, diagnosed_by, diagnosis_date) VALUES
            (1, 'Zain Khan', '2019-03-14', 'Male', 2, 'Dr. Fatima Noor', '2023-01-10'),
            (3, 'Hania Malik', '2020-07-22', 'Female', 1, 'Dr. Fatima Noor', '2023-05-02');
            INSERT INTO PROBLEM (name, description) VALUES
            ('Impulsivity', 'Difficulty controlling immediate reactions'),
            ('Communication Difficulty', 'Trouble expressing needs verbally'),
            ('Sensory Sensitivity', 'Over/under sensitivity to sensory input');
            INSERT INTO CHILD_PROBLEM (child_id, problem_id, identified_on) VALUES
            (1, 1, '2023-01-15'), (1, 2, '2023-01-15'), (2, 3, '2023-05-10');
            INSERT INTO GOAL (problem_id, severity_level, description) VALUES
            (1, 2, 'Wait 10 seconds before responding to a prompt'),
            (2, 1, 'Use one-word requests for basic needs'),
            (3, 1, 'Tolerate one new texture per session');
            INSERT INTO ACTIVITY (goal_id, name, instructions) VALUES
            (1, 'Traffic Light Game', 'Child waits for green light before answering a question'),
            (2, 'Picture Card Requests', 'Child points to a picture card to request an item'),
            (3, 'Texture Box Exploration', 'Child touches one new textured object per session');
            INSERT INTO PROGRESS_LOG (child_id, activity_id, recorded_by, log_date, status, parent_rating, notes) VALUES
            (1, 1, 1, '2026-08-01', 'Completed', 4, 'Waited well today, only one prompt needed'),
            (1, 1, 1, '2026-08-03', 'Attempted', 3, 'Needed two reminders'),
            (2, 3, 3, '2026-08-02', 'Completed', 5, 'Touched the sponge without hesitation');
            INSERT INTO CONSULTANT_REVIEW (log_id, consultant_id, consultant_rating, review_notes, reviewed_on) VALUES
            (1, 1, 4, 'Good improvement, continue at this pace', '2026-08-02'),
            (2, 1, 3, 'Consistent with last week, keep reinforcing', '2026-08-04');
        """)
    conn.commit()
    conn.close()

# --- RUN THE SETUP BEFORE THE APP LOADS ---
if not os.path.exists(DB_NAME):
    setup_database()

# --- DASHBOARD QUERIES ---
def run_query(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

st.set_page_config(page_title="Autism Progress Tracker", layout="wide")
st.title("🧩 Autism Progress-Tracking Dashboard")

menu = st.sidebar.radio("Go to", [
    "📊 Child Progress Logs",
    "📈 Parent vs Consultant Ratings",
    "🎯 Recommended Goals & Activities",
    "📋 Progress Summary (Completed/Attempted)",
    "⏳ Pending Consultant Reviews",
    "⭐ Consultant Average Ratings"
])

st.sidebar.markdown("---")
child_id = st.sidebar.number_input("Filter by Child ID (1 or 2)", min_value=1, value=1, step=1)

if menu == "📊 Child Progress Logs":
    st.header("Progress Logs for Child")
    query = """SELECT pl.log_date, a.name AS activity, pl.status, pl.parent_rating, pl.notes
               FROM PROGRESS_LOG pl JOIN ACTIVITY a ON pl.activity_id = a.activity_id
               WHERE pl.child_id = ? ORDER BY pl.log_date DESC;"""
    df = run_query(query, (child_id,))
    st.dataframe(df, use_container_width=True)

elif menu == "📈 Parent vs Consultant Ratings":
    st.header("Rating Comparison per Log")
    query = """SELECT pl.log_id, c.name AS child_name, a.name AS activity,
               pl.parent_rating, cr.consultant_rating, cr.review_notes
               FROM PROGRESS_LOG pl JOIN CHILD c ON pl.child_id = c.child_id
               JOIN ACTIVITY a ON pl.activity_id = a.activity_id
               LEFT JOIN CONSULTANT_REVIEW cr ON pl.log_id = cr.log_id
               WHERE pl.child_id = ?;"""
    df = run_query(query, (child_id,))
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        st.bar_chart(df[['parent_rating', 'consultant_rating']].rename(columns={'parent_rating': 'Parent', 'consultant_rating': 'Consultant'}))

elif menu == "🎯 Recommended Goals & Activities":
    st.header("Personalized Recommendations")
    query = """SELECT p.name AS problem, g.description AS goal, a.name AS activity
               FROM CHILD_PROBLEM cp JOIN CHILD c ON cp.child_id = c.child_id
               JOIN PROBLEM p ON cp.problem_id = p.problem_id
               JOIN GOAL g ON g.problem_id = p.problem_id AND g.severity_level = c.severity_level
               JOIN ACTIVITY a ON a.goal_id = g.goal_id WHERE c.child_id = ?;"""
    df = run_query(query, (child_id,))
    st.dataframe(df, use_container_width=True)

elif menu == "📋 Progress Summary (Completed/Attempted)":
    st.header("Summary of Activities")
    query = """SELECT c.name AS child_name,
               SUM(CASE WHEN pl.status = 'Completed' THEN 1 ELSE 0 END) AS completed_count,
               SUM(CASE WHEN pl.status = 'Attempted' THEN 1 ELSE 0 END) AS attempted_count
               FROM PROGRESS_LOG pl JOIN CHILD c ON pl.child_id = c.child_id GROUP BY c.name;"""
    df = run_query(query)
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        st.bar_chart(df.set_index('child_name')[['completed_count', 'attempted_count']])

elif menu == "⏳ Pending Consultant Reviews":
    st.header("Logs Awaiting Review")
    query = """SELECT pl.log_id, c.name AS child_name, a.name AS activity, pl.log_date
               FROM PROGRESS_LOG pl JOIN CHILD c ON pl.child_id = c.child_id
               JOIN ACTIVITY a ON pl.activity_id = a.activity_id
               LEFT JOIN CONSULTANT_REVIEW cr ON pl.log_id = cr.log_id
               WHERE cr.review_id IS NULL;"""
    df = run_query(query)
    st.dataframe(df, use_container_width=True)

elif menu == "⭐ Consultant Average Ratings":
    st.header("Consultant Performance")
    query = """SELECT co.consultant_id, u.name AS consultant_name, AVG(cr.consultant_rating) AS avg_rating
               FROM CONSULTANT_REVIEW cr JOIN CONSULTANT co ON cr.consultant_id = co.consultant_id
               JOIN APP_USER u ON co.user_id = u.user_id GROUP BY co.consultant_id, u.name;"""
    df = run_query(query)
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        st.metric("Overall Avg Rating", f"{df['avg_rating'].mean():.2f} ⭐")
