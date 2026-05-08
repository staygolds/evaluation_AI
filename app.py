import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- 1. ページ基本設定 ---
st.set_page_config(page_title="福祉施設 AI評価システム", layout="wide")

# --- 2. APIキーの設定（Secretsから安全に取得） ---
# st.secrets.get("GEMINI_API_KEY") とすることで、Secrets内の名前を指定します
GOOGLE_API_KEY = st.secrets.get("GEMINI_API_KEY")

if not GOOGLE_API_KEY:
    st.error("Google Generative AI APIキーが設定されていません。Streamlit CloudのSecretsに 'GEMINI_API_KEY' を設定してください。")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# --- 3. データの読み込み（キャッシュを利用） ---
@st.cache_data
def load_data():
    # ソース資料[1][2][3][4]に基づくCSV読み込み
    try:
        staff = pd.read_csv('m_staff.csv', encoding='utf-8')
        missions = pd.read_csv('m_missions.csv', encoding='utf-8')
        criteria = pd.read_csv('m_evaluation_criteria.csv', encoding='utf-8')
        return staff, missions, criteria
    except Exception as e:
        st.error(f"CSVファイルの読み込みに失敗しました: {e}")
        st.stop()

df_staff, df_missions, df_criteria = load_data()

# --- 4. 職種マッピング定義 ---
# ソース資料[1]のマッピングをベースに、「初任者」対応を追加
job_category_mapping = {
    '管理者': '幹部',
    '副管理者兼サービス管理責任者': '幹部',
    '主任事務員': '事務',
    '事務員': '事務',
    '主任看護師': '医務',
    '看護師': '医務',
    '主任生活支援員': '幹部',
    '副主任生活支援員': '幹部',
    '生活支援員': '支援',
    '主任管理栄養士': '栄養',
    '管理栄養士': '栄養',
    '主任調理員': '栄養',
    '調理員': '栄養',
    '主任相談支援専門員': '支援',
    '相談支援専門員': '支援',
    '相談員': '支援'
}

# --- 5. サイドバー：評価対象者の選択 ---
st.sidebar.header("評価対象者の選択")
selected_name = st.sidebar.selectbox("職員を選んでください", df_staff['氏名'].tolist())

# --- 6. 選択された職員のデータ抽出 ---
staff_info = df_staff[df_staff['氏名'] == selected_name].iloc[0]
staff_id = staff_info['職員ID']
job_title = staff_info['職種区分']
department = staff_info['所属部署']
qualifications = staff_info['保有資格']

# ミッションデータの取得（ソース資料[3]より）
mission_data = df_missions[df_missions['職員ID'] == staff_id].iloc[0] if not df_missions[df_missions['職員ID'] == staff_id].empty else None
main_mission = mission_data['重要ミッション'] if mission_data is not None else "未設定"
target_val = mission_data['目標値'] if mission_data is not None else "-"

# --- 7. メイン画面表示 ---
st.title(f"📊 AI分析レポート作成: {selected_name} さん")
col1, col2 = st.columns(2)
with col1:
    st.write(f"**役職:** {job_title} | **所属:** {department}")
with col2:
    st.write(f"**資格:** {qualifications}")

st.info(f"**今期の最優先ミッション:**\n{main_mission} (目標値: {target_val})")

st.divider()

# --- 8. 評価入力（合計点集計機能付き） ---
# 「初任者」部署の場合は「新任」の評価項目を適用するロジック（ソース資料[5][4]対応）
if department == "初任者":
    search_category = "新任"
else:
    search_category = job_category_mapping.get(job_title, "支援")

relevant_criteria = df_criteria[df_criteria['職種区分'] == search_category]

scores = {}
if not relevant_criteria.empty:
    st.subheader(f"✅ {search_category}職 評価項目入力")
    for _, item in relevant_criteria.iterrows():
        # スライダーで1〜5点を選択
        scores[item['評価項目名']] = st.slider(item['評価項目名'], 1, 5, 3)
    
    # 合計点の計算
    total_score = sum(scores.values())
    max_score = len(relevant_criteria) * 5
    st.sidebar.markdown("---")
    st.sidebar.metric(label="行動評価 合計点", value=f"{total_score} / {max_score}")
else:
    st.warning("対応する評価項目が見つかりません。")

# --- 9. 面接者所感の入力 ---
st.subheader("📝 面接者所感")
interviewer_comments = st.text_area(
    "面接での気づきやフィードバック、本人への期待を入力してください",
    placeholder="例：数値目標に対する意識が非常に高く、具体的な行動計画も立てられている。",
    height=150
)

# --- 10. AI分析実行 ---
if st.button("🚀 AI分析レポートを生成する"):
    if not scores:
        st.error("評価項目が入力されていません。")
    else:
        # AIへの指示文（プロンプト）の作成
        eval_details = "\n".join([f"- {k}: {v}点" for k, v in scores.items()])
        
        prompt = f"""
        あなたは社会福祉施設の経営人事エキスパートです。
        以下のデータに基づき、{selected_name}さんの評価レポートを作成してください。

        # 対象者情報
        - 氏名: {selected_name}
        - 役職: {job_title} / 資格: {qualifications}
        - 重要ミッション: {main_mission} (目標値: {target_val})

        # 評価結果
        - 行動評価合計: {total_score}/{max_score}点
        - 項目別詳細:
        {eval_details}

        # 面接者所感
        {interviewer_comments}

        # レポート構成
        1. 【総評】ミッション達成に向けた現状分析
        2. 【強みの抽出】点数の高い項目と資格の活かし方
        3. 【改善・期待】合計点と所感を踏まえた次期の具体的なアクション
        """

try:
    model = genai.GenerativeModel('gemini-2.5-pro')

response = model.generate_content(
    prompt,
    generation_config={
        "temperature": 0.7,
        "max_output_tokens": 8192,
    }
)

st.write(response.text)

except Exception as e:
    st.error(f"AI分析中にエラーが発生しました: {e}")
