import streamlit as st
import sqlite3
import pandas as pd
import os
import altair as alt
from datetime import datetime, timedelta

DB_NAME = "autism_progress.db"

def table_exists(cursor, table_name):
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None

def setup_database():
    """Creates the database and inserts sample data if tables don't exist"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    if not table_exists(cursor, "APP_USER"):
        st.info("📦 Creating database tables...")
        
        cursor.executescript("""
            CREATE TABLE APP_USER (
                user_id        INTEGER PRIMARY KEY,
                name           TEXT NOT NULL,
                email          TEXT UNIQUE NOT NULL,
                password_hash  TEXT NOT NULL,
                role           TEXT CHECK (role IN ('Parent','Consultant'))
            );
            CREATE TABLE CONSULTANT (
                consultant_id   INTEGER PRIMARY KEY,
                user_id         INTEGER NOT NULL,
                specialization  TEXT,
                FOREIGN KEY (user_id) REFERENCES APP_USER(user_id)
            );
            CREATE TABLE CHILD (
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
            CREATE TABLE PROBLEM (
                problem_id   INTEGER PRIMARY KEY,
                name         TEXT NOT NULL,
                description  TEXT
            );
            CREATE TABLE CHILD_PROBLEM (
                child_id       INTEGER NOT NULL,
                problem_id     INTEGER NOT NULL,
                identified_on  TEXT,
                PRIMARY KEY (child_id, problem_id),
                FOREIGN KEY (child_id) REFERENCES CHILD(child_id),
                FOREIGN KEY (problem_id) REFERENCES PROBLEM(problem_id)
            );
            CREATE TABLE GOAL (
                goal_id         INTEGER PRIMARY KEY,
                problem_id      INTEGER NOT NULL,
                severity_level  INTEGER CHECK (severity_level BETWEEN 1 AND 3),
                description     TEXT NOT NULL,
                FOREIGN KEY (problem_id) REFERENCES PROBLEM(problem_id)
            );
            CREATE TABLE ACTIVITY (
                activity_id   INTEGER PRIMARY KEY,
                goal_id       INTEGER NOT NULL,
                name          TEXT NOT NULL,
                instructions  TEXT,
                FOREIGN KEY (goal_id) REFERENCES GOAL(goal_id)
            );
            CREATE TABLE PROGRESS_LOG (
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
            CREATE TABLE CONSULTANT_REVIEW (
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
        st.success("✅ Database created successfully!")
    else:
        cursor.execute("SELECT COUNT(*) FROM APP_USER")
        if cursor.fetchone()[0] == 0:
            cursor.executescript("""... (insert data) ...""")
            conn.commit()
            st.success("✅ Sample data inserted!")
    
    conn.close()

def reset_database():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    setup_database()
    st.success("✅ Database has been reset!")
    st.rerun()

def clean_column_name(col):
    words = col.split('_')
    return ' '.join(word.capitalize() for word in words)

def run_query(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    df.columns = [clean_column_name(col) for col in df.columns]
    return df

def add_sample_data():
    """Adds 12 new dummy progress logs"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Get IDs
    cursor.execute("SELECT user_id FROM APP_USER WHERE name = 'Ayesha Khan' LIMIT 1")
    user_id = cursor.fetchone()[0]
    
    sample_logs = [
        # Zain Khan (child_id = 1) - Traffic Light Game (activity_id = 1)
        (1, 1, user_id, '2026-08-05', 'Completed', 5, 'Excellent! Waited patiently for 10 seconds!'),
        (1, 1, user_id, '2026-08-07', 'Attempted', 4, 'Needed one reminder but did well'),
        (1, 1, user_id, '2026-08-09', 'Completed', 5, 'Perfect! No prompts needed'),
        (1, 1, user_id, '2026-08-11', 'Completed', 4, 'Great improvement this week'),
        
        # Zain Khan - Picture Card Requests (activity_id = 2)
        (1, 2, user_id, '2026-08-04', 'Attempted', 3, 'Still learning to point consistently'),
        (1, 2, user_id, '2026-08-06', 'Completed', 4, 'Pointed to the right card most times!'),
        (1, 2, user_id, '2026-08-08', 'Completed', 5, 'Amazing! Used cards to request 3 times'),
        (1, 2, user_id, '2026-08-10', 'Completed', 5, 'Very consistent this week'),
        
        # Hania Malik (child_id = 2) - Texture Box Exploration (activity_id = 3)
        (2, 3, user_id, '2026-08-03', 'Attempted', 3, 'Hesitant at first, touched one texture'),
        (2, 3, user_id, '2026-08-05', 'Attempted', 4, 'Touched 2 textures!'),
        (2, 3, user_id, '2026-08-07', 'Completed', 5, 'Explored all textures confidently!'),
        (2, 3, user_id, '2026-08-09', 'Completed', 5, 'Loved the fluffy texture the most'),
    ]
    
    for log in sample_logs:
        cursor.execute("""
            INSERT INTO PROGRESS_LOG (child_id, activity_id, recorded_by, log_date, status, parent_rating, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, log)
    
    conn.commit()
    conn.close()
    st.success("✅ 12 new progress logs added successfully!")

# --- APP STARTS HERE ---
st.set_page_config(page_title="🧠 Autism Hacked", layout="wide")

# ===== 🎨 COMPLETE THEME (Montserrat + Confetti Colors + FORCE LIGHT MODE) =====
st.markdown("""
<style>
    /* ===== FORCE LIGHT MODE - FIX FOR CHROME DARK MODE ===== */
    * {
        color-scheme: light !important;
    }
    
    .stApp {
        color-scheme: light !important;
    }
    
    /* ===== FONT: MONTSERRAT ===== */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        font-family: 'Montserrat', sans-serif;
    }
    
    .stSidebar * {
        font-family: 'Montserrat', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Montserrat', sans-serif;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }

    /* ===== CONFETTI BACKGROUND ===== */
    .stApp {
        background-image: url('https://raw.githubusercontent.com/Meh-Reen/Autism-Tracker-Project/main/confetti.png');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(248, 246, 240, 0.88);
        z-index: -1;
    }

    .stApp {
        z-index: 1;
    }

    /* ===== HEADERS ===== */
    h1 {
        color: #2D3436 !important;
        font-weight: 800 !important;
        font-size: 2.8rem !important;
        padding-bottom: 8px !important;
        border-bottom: 4px solid #81BEE4 !important;
        display: inline-block !important;
    }

    h2, h3 {
        color: #2D3436 !important;
        font-weight: 600 !important;
    }

    /* ===== SIDEBAR ===== */
    .stSidebar {
        background: #F0EDE6 !important;
        border-right: 2px solid rgba(129, 190, 228, 0.3) !important;
        padding-top: 20px !important;
    }

    .stSidebar * {
        color: #2D3436 !important;
    }

    .stSidebar h1 {
        color: #2D3436 !important;
        border-bottom-color: #81BEE4 !important;
    }

    .stSidebar .stSubheader {
        color: #81BEE4 !important;
        font-weight: 600 !important;
    }

    /* ===== BUTTONS ===== */
    .stButton > button {
        background: linear-gradient(135deg, #81BEE4, #C898DF) !important;
        color: white !important;
        border: none !important;
        border-radius: 30px !important;
        padding: 12px 32px !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(129, 190, 228, 0.3) !important;
    }

    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 8px 30px rgba(129, 190, 228, 0.5) !important;
        background: linear-gradient(135deg, #C898DF, #81BEE4) !important;
    }

    .stButton > button:active {
        transform: translateY(0px) !important;
    }

    .stButton > button[data-baseweb="button"]:nth-child(1) {
        background: linear-gradient(135deg, #FFB865, #FF9999) !important;
        box-shadow: 0 4px 15px rgba(255, 185, 101, 0.3) !important;
    }

    .stButton > button[data-baseweb="button"]:nth-child(1):hover {
        box-shadow: 0 8px 30px rgba(255, 185, 101, 0.5) !important;
    }

    /* ===== METRICS / CARDS ===== */
    .stMetric {
        background: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(10px) !important;
        border-radius: 20px !important;
        padding: 25px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06) !important;
        border: 2px solid #81BEE4 !important;
    }

    .stMetric label {
        color: #2D3436 !important;
        font-weight: 600 !important;
        font-size: 16px !important;
    }

    .stMetric .stMetricValue {
        color: #2D3436 !important;
        font-weight: 800 !important;
        font-size: 2.8rem !important;
    }

    .stMetric .stMetricDelta {
        color: #6B7280 !important;
    }

    /* ===== DATAFRAMES ===== */
    .stDataFrame {
        border-radius: 16px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06) !important;
        border: 1px solid rgba(129, 190, 228, 0.2) !important;
        background: white !important;
    }

    .stDataFrame thead th {
        background: #81BEE4 !important;
        color: white !important;
        font-weight: 600 !important;
        font-family: 'Montserrat', sans-serif !important;
        padding: 12px !important;
        text-transform: capitalize !important;
    }

    .stDataFrame tbody td {
        background: white !important;
        color: #2D3436 !important;
        font-family: 'Montserrat', sans-serif !important;
        padding: 10px !important;
    }

    .stDataFrame tbody tr:hover td {
        background: #F0EDE6 !important;
    }

    /* ===== ALERTS ===== */
    .stAlert {
        border-radius: 16px !important;
        border-left: 5px solid #81BEE4 !important;
        background: rgba(255, 255, 255, 0.95) !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05) !important;
        color: #2D3436 !important;
    }

    .stAlert .stAlertContent {
        color: #2D3436 !important;
    }

    .stAlert[data-baseweb="notification"] {
        border-left-color: #D2EE6E !important;
    }

    /* ===== NUMBER INPUT ===== */
    .stNumberInput input {
        border-radius: 25px !important;
        border: 2px solid #81BEE4 !important;
        padding: 8px 16px !important;
        font-family: 'Montserrat', sans-serif !important;
        background: white !important;
        color: #2D3436 !important;
    }

    .stNumberInput input:focus {
        border-color: #C898DF !important;
        box-shadow: 0 0 0 3px rgba(200, 152, 223, 0.2) !important;
    }

    /* ===== SELECT BOX ===== */
    .stSelectbox select {
        border-radius: 25px !important;
        border: 2px solid #81BEE4 !important;
        padding: 8px 16px !important;
        font-family: 'Montserrat', sans-serif !important;
        background: white !important;
        color: #2D3436 !important;
    }

    /* ===== RADIO BUTTONS ===== */
    .stRadio > div {
        background: rgba(255, 255, 255, 0.6) !important;
        border-radius: 12px !important;
        padding: 8px !important;
    }

    .stRadio label {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 500 !important;
        padding: 6px 12px !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
        color: #2D3436 !important;
    }

    .stRadio label:hover {
        background: rgba(129, 190, 228, 0.15) !important;
    }

    .stRadio .stRadioChecked {
        background: #81BEE4 !important;
        color: white !important;
        border-radius: 8px !important;
    }

    /* ===== FORMS ===== */
    .stForm {
        background: rgba(255, 255, 255, 0.85) !important;
        backdrop-filter: blur(10px) !important;
        border-radius: 20px !important;
        padding: 20px !important;
        border: 1px solid rgba(129, 190, 228, 0.15) !important;
    }

    /* ===== EXPANDER ===== */
    .streamlit-expanderHeader {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600 !important;
        color: #2D3436 !important;
        background: rgba(255, 255, 255, 0.5) !important;
        border-radius: 12px !important;
    }

    /* ===== SLIDER ===== */
    .stSlider .stSliderTrack {
        background: #81BEE4 !important;
    }

    .stSlider .stSliderThumb {
        background: #C898DF !important;
        border: 3px solid white !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1) !important;
    }

    /* ===== DIVIDERS ===== */
    hr {
        border: none !important;
        height: 2px !important;
        background: linear-gradient(90deg, #81BEE4, #C898DF, #FFB865, #FF9999, #D2EE6E) !important;
        opacity: 0.5 !important;
        margin: 20px 0 !important;
    }

    /* ===== COLOR PICKERS ===== */
    .stColorPicker {
        border-radius: 25px !important;
    }

    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 30px !important;
        padding: 8px 20px !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 500 !important;
        background: rgba(255, 255, 255, 0.5) !important;
        color: #6B7280 !important;
    }

    .stTabs [aria-selected="true"] {
        background: #81BEE4 !important;
        color: white !important;
    }

    /* ===== SIDEBAR SUBTEXT ===== */
    .stSidebar .stCaption {
        color: #6B7280 !important;
        font-weight: 400 !important;
    }

    .stSidebar .stColorPicker label {
        color: #2D3436 !important;
        font-weight: 500 !important;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar with reset button and dynamic colors
with st.sidebar:
    st.title("🧠 Autism Hacked")
    menu = st.radio("Go to", [
        "📊 Child Progress Logs",
        "📈 Parent vs Consultant Ratings",
        "🎯 Recommended Goals & Activities",
        "📋 Progress Summary (Completed/Attempted)",
        "⏳ Pending Consultant Reviews",
        "⭐ Consultant Average Ratings"
    ])
    st.markdown("---")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Reset Database", type="secondary"):
            reset_database()
    with col_btn2:
        if st.button("📥 Add Sample Data", type="primary"):
            add_sample_data()
            st.rerun()
    
    child_id = st.number_input("Filter by Child ID (1 or 2)", min_value=1, value=1, step=1)
    
    # ===== 🎨 DYNAMIC COLOR PICKERS (LIVE!) =====
    st.markdown("---")
    st.subheader("🎨 Chart Colors")
    
    col1, col2 = st.columns(2)
    with col1:
        color_completed = st.color_picker("✅ Completed", "#D2EE6E")
        color_parent = st.color_picker("👨‍👦 Parent Rating", "#81BEE4")
    with col2:
        color_attempted = st.color_picker("🟡 Attempted", "#FFB865")
        color_consultant = st.color_picker("👩‍⚕️ Consultant", "#C898DF")

# Initialize database on first load
if not os.path.exists(DB_NAME):
    setup_database()
else:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if not table_exists(cursor, "APP_USER"):
        conn.close()
        setup_database()
    else:
        conn.close()

st.title("🧠 Autism Hacked")

# --- QUERY SECTION WITH DYNAMIC CHART COLORS ---
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
        df_melted = df.melt(id_vars=['Child Name'], 
                            value_vars=['Parent Rating', 'Consultant Rating'],
                            var_name='Rating Type', 
                            value_name='Rating')
        chart = alt.Chart(df_melted).mark_bar().encode(
            x=alt.X('Child Name:N', title=''),
            y=alt.Y('Rating:Q', title='Rating (1-5)'),
            color=alt.Color('Rating Type:N', 
                            scale=alt.Scale(
                                domain=['Parent Rating', 'Consultant Rating'],
                                range=[color_parent, color_consultant]
                            ),
                            legend=alt.Legend(title='')),
            tooltip=['Child Name', 'Rating Type', 'Rating']
        ).properties(height=400)
        st.altair_chart(chart, use_container_width=True)

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
        df_melted = df.melt(id_vars=['Child Name'], 
                            value_vars=['Completed Count', 'Attempted Count'],
                            var_name='Status', 
                            value_name='Count')
        chart = alt.Chart(df_melted).mark_bar().encode(
            x=alt.X('Child Name:N', title=''),
            y=alt.Y('Count:Q', title='Number of Activities'),
            color=alt.Color('Status:N', 
                            scale=alt.Scale(
                                domain=['Completed Count', 'Attempted Count'],
                                range=[color_completed, color_attempted]
                            ),
                            legend=alt.Legend(title='')),
            tooltip=['Child Name', 'Status', 'Count']
        ).properties(height=400)
        st.altair_chart(chart, use_container_width=True)

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
        st.metric("Overall Avg Rating", f"{df['Avg Rating'].mean():.2f} ⭐")
