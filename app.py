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

# --- 評価入力セクション ---
search_dept = "新任" if department == "初任者" else department
relevant_criteria = df_criteria[df_criteria['職種区分'] == search_dept]

scores = {}
if not relevant_criteria.empty:
    st.subheader(f"✅ {search_dept}職 評価項目入力")
    for _, item in relevant_criteria.iterrows():
        # ソース[1]の評価項目名を表示
        scores[item['評価項目名']] = st.slider(item['評価項目名'], 1, 5, 3)
    
    # --- 【追加機能】合計点の表示 ---
    total_score = sum(scores.values())
    max_score = len(relevant_criteria) * 5
    st.sidebar.markdown("---")
    st.sidebar.metric(label="評価点 合計", value=f"{total_score} / {max_score}")
else:
    st.warning(f"「{department}」に対応する評価項目が見つかりません。")

# --- 【追加機能】面接者所感の入力 ---
st.subheader("📝 面接者所感")
interviewer_comments = st.text_area(
    "面接での気づきや、本人へのフィードバック補足事項を入力してください",
    placeholder="例：数値目標への意識が高く、具体的な行動計画も立てられている。",
    height=150
)

# --- AI分析実行 ---
if st.button("🚀 AI分析レポートを生成する"):
    eval_text = "\n".join([f"- {k}: {v}点" for k, v in scores.items()])
    
    # 所感と合計点もAIに伝えます
    prompt = f"""
    あなたは社会福祉施設の経営人事エキスパートです。
    以下のデータに基づき、評価レポートを作成してください。

    # 基本情報
    - 氏名：{selected_name} / 役職：{job_title}
    - 今期ミッション：{main_mission} (目標：{target_value})

    # 評価データ
    - 行動評価合計点：{total_score}点（{max_score}点満点）
    - 各項目の点数：
    {eval_text}

    # 面接者からの所感
    {interviewer_comments}

    # レポート構成
    1. 【総評】数値目標と行動評価の整合性
    2. 【強みの分析】
    3. 【課題と改善アドバイス】面接者所感を踏まえた具体案
    """

    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        with st.spinner('AIがレポートを生成中...'):
            response = model.generate_content(prompt)
            st.success("分析完了")
            st.markdown(response.text)
    except Exception as e:
        st.error(f"エラーが発生しました。詳細: {e}")
