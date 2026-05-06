import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- ページ基本設定 ---
st.set_page_config(page_title="福祉施設 AI評価システム", layout="wide")

# --- データの読み込み ---
@st.cache_data
def load_data():
    staff = pd.read_csv('m_staff.csv', encoding='utf-8')
    missions = pd.read_csv('m_missions.csv', encoding='utf-8')
    criteria = pd.read_csv('m_evaluation_criteria.csv', encoding='utf-8')
    return staff, missions, criteria

try:
    df_staff, df_missions, df_criteria = load_data()
except Exception as e:
    st.error(f"CSV読み込み失敗: {e}")
    st.stop()

# --- サイドバー：評価対象者の選択 ---
st.sidebar.header("評価対象者の選択")
selected_name = st.sidebar.selectbox("職員を選んでください", df_staff['氏名'].tolist())

# --- データ抽出 ---
staff_matches = df_staff[df_staff['氏名'] == selected_name]
if not staff_matches.empty:
    selected_staff = staff_matches.iloc[0] # .iloc で1行を確定
    staff_id = selected_staff['職員ID']
    job_title = selected_staff['職種区分']
    department = selected_staff['所属部署']
    qualifications = selected_staff['保有資格']
else:
    st.stop()

mission_matches = df_missions[df_missions['職員ID'] == staff_id]
if not mission_matches.empty:
    selected_mission = mission_matches.iloc[0]
    main_mission = selected_mission['重要ミッション']
    target_metric = selected_mission['主要数値目標']
    target_value = selected_mission['目標値']
else:
    main_mission, target_metric, target_value = "未設定", "未設定", "-"

# --- メイン画面表示 ---
st.title(f"📊 AI分析レポート作成: {selected_name} さん")
st.write(f"**役職:** {job_title} | **所属:** {department} | **資格:** {qualifications}")
st.info(f"**今期の最優先ミッション:**\n{main_mission}")

st.divider()

# --- 評価入力（名称不一致の吸収） ---
search_dept = "新任" if department == "初任者" else department
relevant_criteria = df_criteria[df_criteria['職種区分'] == search_dept]

scores = {}
if not relevant_criteria.empty:
    st.subheader(f"✅ {search_dept}職 評価項目入力")
    for _, item in relevant_criteria.iterrows():
        scores[item['評価項目名']] = st.slider(item['評価項目名'], 1, 5, 3)
else:
    st.warning(f"「{department}」に対応する評価項目が見つかりません。")

# --- AI分析実行（ここがエラーの箇所でした） ---
if st.button("🚀 AI分析レポートを生成する"):
    eval_text = "\n".join([f"- {k}: {v}点" for k, v in scores.items()])
    
    prompt = f"""
    あなたは社会福祉施設の経営人事エキスパートです。
    # 氏名：{selected_name} / 役職：{job_title} / 資格：{qualifications}
    # ミッション：{main_mission}
    # 目標：{target_metric} ({target_value})
    # 行動評価結果：\n{eval_text}
    """

    try:
        # インデント（字下げ）を try と合わせることが重要です
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        
        # モデル名は安定版の 'gemini-1.5-flash' を使用
        model = genai.GenerativeModel('gemini-1.0-pro')
        
        with st.spinner('AIが分析中...'):
            response = model.generate_content(prompt)
            st.success("分析が完了しました！")
            st.markdown("---")
            st.markdown(response.text)
            
    except Exception as e:
        # ここを try と垂直に揃えることで IndentationError を防ぎます
        st.error(f"AI分析中にエラーが発生しました。詳細: {e}")
