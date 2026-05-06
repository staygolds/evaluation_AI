import streamlit as st
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="福祉施設 AI評価システム", layout="wide")

@st.cache_data
def load_data():
    staff = pd.read_csv('m_staff.csv', encoding='utf-8')
    missions = pd.read_csv('m_missions.csv', encoding='utf-8')
    criteria = pd.read_csv('m_evaluation_criteria.csv', encoding='utf-8')
    return staff, missions, criteria

try:
    df_staff, df_missions, df_criteria = load_data()
except Exception as e:
    st.error(f"CSVファイルの読み込みに失敗しました: {e}")
    st.stop()

st.sidebar.header("評価対象者の選択")
staff_names = df_staff['氏名'].tolist()
selected_name = st.sidebar.selectbox("職員を選んでください", staff_names)

# --- エラーを回避する新しい書き方 ---
# queryを使って対象者を絞り込み、最初の値を直接取り出します
selected_staff_df = df_staff[df_staff['氏名'] == selected_name]

if not selected_staff_df.empty:
    # .iloc の代わりに .values を使って直接中身を取り出します
    staff_id = selected_staff_df['職員ID'].values
    job_type = selected_staff_df['職種区分'].values
    qualifications = selected_staff_df['保有資格'].values
else:
    st.error("職員情報が見つかりません。")
    st.stop()

# 職務分掌マスター(m_missions)からミッションを取得 [1]
mission_df = df_missions[df_missions['職員ID'] == staff_id]
if not mission_df.empty:
    main_mission = mission_df['重要ミッション'].values
    target_metric = mission_df['主要数値目標'].values
    target_value = mission_df['目標値'].values
else:
    main_mission, target_metric, target_value = "未設定", "未設定", "-"

st.title(f"📊 AI分析レポート作成: {selected_name} さん")
col1, col2 = st.columns(2)
with col1:
    st.subheader("👤 職員プロフィール")
    st.write(f"**職種区分:** {job_type}")
    st.write(f"**保有資格:** {qualifications}") # [2]
with col2:
    st.subheader("🎯 今期のミッション")
    st.info(f"**最優先事項:**\n{main_mission}") # [1]
    st.write(f"**数値目標:** {target_metric} ({target_value})")

st.divider()

st.subheader(f"✅ {job_type}職 評価項目入力")
relevant_criteria = df_criteria[df_criteria['職種区分'] == job_type] # [3]

scores = {}
if not relevant_criteria.empty:
    for _, item in relevant_criteria.iterrows():
        scores[item['評価項目名']] = st.slider(item['評価項目名'], 1, 5, 3)
else:
    st.warning(f"「{job_type}」職用の評価項目が見つかりません。")

if st.button("🚀 AI分析レポートを生成する"):
    eval_text = "\n".join([f"- {k}: {v}点" for k, v in scores.items()])
    prompt = f"あなたは社会福祉施設の経営人事エキスパートです...\n\n# 氏名：{selected_name}\n# ミッション：{main_mission}\n# 評価：\n{eval_text}"
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        st.markdown("---")
        st.markdown(response.text)
    except Exception as e:
        st.error("APIキーの設定を確認してください。")
