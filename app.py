import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- ページ基本設定 ---
st.set_page_config(page_title="福祉施設 AI評価システム", layout="wide")

# --- データの読み込み関数 ---
@st.cache_data
def load_data():
    # 職員マスター[1], 職務分掌マスター[2], 評価項目マスター[3]を読み込みます
    staff = pd.read_csv('m_staff.csv', encoding='utf-8')
    missions = pd.read_csv('m_missions.csv', encoding='utf-8')
    criteria = pd.read_csv('m_evaluation_criteria.csv', encoding='utf-8')
    return staff, missions, criteria

try:
    df_staff, df_missions, df_criteria = load_data()
except Exception as e:
    st.error(f"CSVファイルの読み込みに失敗しました: {e}")
    st.stop()

# --- サイドバー：評価対象者の選択 ---
st.sidebar.header("評価対象者の選択")
staff_names = df_staff['氏名'].tolist()
selected_name = st.sidebar.selectbox("職員を選んでください", staff_names)

# --- データの絞り込み（エラー回避の重要ポイント） ---
# 氏名で検索し、最初の1件を「単一の行データ」として取得します
staff_matches = df_staff[df_staff['氏名'] == selected_name]

if not staff_matches.empty:
    # .iloc を使うことで、リストではなく「1人分のデータ」として確定させます
    selected_staff = staff_matches.iloc
    staff_id = selected_staff['職員ID']
    job_type = selected_staff['職種区分']
    qualifications = selected_staff['保有資格']
else:
    st.error("職員情報が見つかりません。")
    st.stop()

# 職員IDをキーにミッション情報を取得
# 前回の ValueError を防ぐため、ここでも .iloc を使用します
mission_matches = df_missions[df_missions['職員ID'] == staff_id]

if not mission_matches.empty:
    selected_mission = mission_matches.iloc
    main_mission = selected_mission['重要ミッション']
    target_metric = selected_mission['主要数値目標']
    target_value = selected_mission['目標値']
else:
    main_mission, target_metric, target_value = "未設定", "未設定", "-"

# --- メイン画面：基本情報の表示 ---
st.title(f"📊 AI分析レポート作成: {selected_name} さん")

col1, col2 = st.columns(2)
with col1:
    st.subheader("👤 職員プロフィール")
    st.write(f"**職種区分:** {job_type}")
    st.write(f"**保有資格:** {qualifications}")
with col2:
    st.subheader("🎯 今期のミッション")
    st.info(f"**最優先事項:**\n{main_mission}")
    st.write(f"**数値目標:** {target_metric} ({target_value})")

st.divider()

# --- 評価入力セクション ---
st.subheader(f"✅ {job_type}職 評価項目入力")
# 職種区分（事務、医務、支援など）に一致する項目を抽出 [3]
relevant_criteria = df_criteria[df_criteria['職種区分'] == job_type]

scores = {}
if not relevant_criteria.empty:
    for _, item in relevant_criteria.iterrows():
        scores[item['評価項目名']] = st.slider(item['評価項目名'], 1, 5, 3)
else:
    st.warning(f"「{job_type}」職用の評価項目が見つかりません。")

# --- AI分析実行 ---
if st.button("🚀 AI分析レポートを生成する"):
    eval_text = "\n".join([f"- {k}: {v}点" for k, v in scores.items()])
    
    prompt = f"""
    あなたは社会福祉施設の経営人事エキスパートです。以下のデータに基づき分析してください。
    # 氏名：{selected_name} / 職種：{job_type} / 保有資格：{qualifications}
    # 重要ミッション：{main_mission}
    # 数値目標：{target_metric} ({target_value})
    # 評価点：\n{eval_text}
    """

    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        with st.spinner('AI分析中...'):
            response = model.generate_content(prompt)
            st.success("分析が完了しました！")
            st.markdown("---")
            st.markdown(response.text)
    except Exception as e:
        st.error("AI分析中にエラーが発生しました。Secrets設定を確認してください。")
