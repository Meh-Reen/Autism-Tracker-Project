import streamlit as st
import sqlite3
import pandas as pd

DB_NAME = "autism_progress.db"

def run_query(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

st.set_page_config(page_title="Autism Progress Tracker", layout="wide")
st.title("🧩 Autism Progress-Tracking Dashboard")

# Sidebar navigation
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
    query = """
        SELECT pl.log_date, a.name AS activity, pl.status, pl.parent_rating, pl.notes
        FROM PROGRESS_LOG pl
        JOIN ACTIVITY a ON pl.activity_id = a.activity_id
        WHERE pl.child_id = ?
        ORDER BY pl.log_date DESC;
    """
    df = run_query(query, (child_id,))
    st.dataframe(df, use_container_width=True)

elif menu == "📈 Parent vs Consultant Ratings":
    st.header("Rating Comparison per Log")
    query = """
        SELECT pl.log_id, c.name AS child_name, a.name AS activity,
               pl.parent_rating, cr.consultant_rating, cr.review_notes
        FROM PROGRESS_LOG pl
        JOIN CHILD c ON pl.child_id = c.child_id
        JOIN ACTIVITY a ON pl.activity_id = a.activity_id
        LEFT JOIN CONSULTANT_REVIEW cr ON pl.log_id = cr.log_id
        WHERE pl.child_id = ?;
    """
    df = run_query(query, (child_id,))
    st.dataframe(df, use_container_width=True)
    
    # Simple bar chart
    if not df.empty:
        st.bar_chart(df[['parent_rating', 'consultant_rating']].rename(
            columns={'parent_rating': 'Parent', 'consultant_rating': 'Consultant'}))

elif menu == "🎯 Recommended Goals & Activities":
    st.header("Personalized Recommendations")
    query = """
        SELECT p.name AS problem, g.description AS goal, a.name AS activity
        FROM CHILD_PROBLEM cp
        JOIN CHILD c ON cp.child_id = c.child_id
        JOIN PROBLEM p ON cp.problem_id = p.problem_id
        JOIN GOAL g ON g.problem_id = p.problem_id AND g.severity_level = c.severity_level
        JOIN ACTIVITY a ON a.goal_id = g.goal_id
        WHERE c.child_id = ?;
    """
    df = run_query(query, (child_id,))
    st.dataframe(df, use_container_width=True)

elif menu == "📋 Progress Summary (Completed/Attempted)":
    st.header("Summary of Activities")
    query = """
        SELECT c.name AS child_name,
               SUM(CASE WHEN pl.status = 'Completed' THEN 1 ELSE 0 END) AS completed_count,
               SUM(CASE WHEN pl.status = 'Attempted' THEN 1 ELSE 0 END) AS attempted_count
        FROM PROGRESS_LOG pl
        JOIN CHILD c ON pl.child_id = c.child_id
        GROUP BY c.name;
    """
    df = run_query(query)
    st.dataframe(df, use_container_width=True)
    
    # Plot
    if not df.empty:
        st.bar_chart(df.set_index('child_name')[['completed_count', 'attempted_count']])

elif menu == "⏳ Pending Consultant Reviews":
    st.header("Logs Awaiting Review")
    query = """
        SELECT pl.log_id, c.name AS child_name, a.name AS activity, pl.log_date
        FROM PROGRESS_LOG pl
        JOIN CHILD c ON pl.child_id = c.child_id
        JOIN ACTIVITY a ON pl.activity_id = a.activity_id
        LEFT JOIN CONSULTANT_REVIEW cr ON pl.log_id = cr.log_id
        WHERE cr.review_id IS NULL;
    """
    df = run_query(query)
    st.dataframe(df, use_container_width=True)

elif menu == "⭐ Consultant Average Ratings":
    st.header("Consultant Performance")
    query = """
        SELECT co.consultant_id, u.name AS consultant_name, 
               AVG(cr.consultant_rating) AS avg_rating
        FROM CONSULTANT_REVIEW cr
        JOIN CONSULTANT co ON cr.consultant_id = co.consultant_id
        JOIN APP_USER u ON co.user_id = u.user_id
        GROUP BY co.consultant_id, u.name;
    """
    df = run_query(query)
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        st.metric("Overall Avg Rating", f"{df['avg_rating'].mean():.2f} ⭐")

st.sidebar.info("Built with ❤️ using Streamlit & SQLite")