import streamlit as st
import pandas as pd
import google.genai as genai

st.set_page_config(page_title="福祉施設 AI評価システム", layout="wide")

@st.cache_data
def load_data():
    # 各マスター（ソース資料）を読み込みます
    staff = pd.read_csv('m_staff.csv', encoding='utf-8')
    missions = pd.read_csv('m_missions.csv', encoding='utf-8')
    criteria = pd.read_csv('m_evaluation_criteria.csv', encoding='utf-8')
    return staff, missions, criteria

try:
    df_staff, df_missions, df_criteria = load_data()
except Exception as e:
    st.error(f"CSV読み込み失敗: {e}")
    st.stop()

# --- サイドバー：職員選択と合計点表示 ---
st.sidebar.header("評価対象者の選択")
selected_name = st.sidebar.selectbox("職員を選んでください", df_staff['氏名'].tolist())

# 職員データの特定 [2]
staff_matches = df_staff[df_staff['氏名'] == selected_name]
if not staff_matches.empty:
    selected_staff = staff_matches.iloc[0]
    staff_id = selected_staff['職員ID']
    job_title = selected_staff['職種区分']
    department = selected_staff['所属部署']
    qualifications = selected_staff['保有資格']
else:
    st.stop()

# ミッションデータの特定 [3]
mission_matches = df_missions[df_missions['職員ID'] == staff_id]
if not mission_matches.empty:
    selected_mission = mission_matches.iloc[0]
    main_mission = selected_mission['重要ミッション']
    target_value = selected_mission['目標値']
else:
    main_mission, target_value = "未設定", "-"

# --- メイン画面 ---
st.title(f"📊 AI分析レポート作成: {selected_name} さん")
st.write(f"**役職:** {job_title} | **所属:** {department} | **資格:** {qualifications}")

st.divider()

# --- 評価入力（合計点集計機能付き） ---
# 資料の「初任者」と「新任」を紐付けます [2][1]
search_dept = "新任" if department == "初任者" else department
relevant_criteria = df_criteria[df_criteria['職種区分'] == search_dept]

scores = {}
if not relevant_criteria.empty:
    st.subheader(f"✅ {search_dept}職 評価項目入力")
    for _, item in relevant_criteria.iterrows():
        # ソース資料の各項目名をスライダーで表示 [1]
        scores[item['評価項目名']] = st.slider(item['評価項目名'], 1, 5, 3)
    
    # 【追加機能】合計点の計算
    total_score = sum(scores.values())
    max_score = len(relevant_criteria) * 5
    st.sidebar.markdown("---")
    st.sidebar.metric(label="行動評価 合計点", value=f"{total_score} / {max_score}")
else:
    st.warning(f"評価項目が見つかりません。")

# --- 【追加機能】面接者所感の入力 ---
st.subheader("📝 面接者所感")
interviewer_comments = st.text_area(
    "面接での気づきや、フィードバック事項を入力してください（この内容もAIが分析します）",
    placeholder="例：今期の目標値に対する具体的な行動計画が明確であり、意欲も非常に高い。",
    height=150
)

# --- AI分析実行 ---
if st.button("🚀 AI分析レポートを生成する"):
    eval_text = "\n".join([f"- {k}: {v}点" for k, v in scores.items()])
    
    prompt = f"""
    あなたは社会福祉施設の経営人事エキスパートです。
    以下のデータに基づき、評価レポートを作成してください。

    # 基本情報
    - 氏名：{selected_name} / 役職：{job_title}
    - ミッション：{main_mission} (目標値：{target_value})

    # 評価結果
    - 行動評価合計：{total_score}/{max_score}点
    - 各項目：
    {eval_text}

    # 面接者所感
    {interviewer_comments}
    """

    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        # 正しいモデル名 'gemini-2.0-flash' を指定
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        with st.spinner('AIがレポートを生成中...'):
            response = model.generate_content(prompt)
            st.success("分析が完了しました！")
            st.markdown("---")
            st.markdown(response.text)
    except Exception as e:
        st.error(f"AI分析中にエラーが発生しました。詳細: {e}")
