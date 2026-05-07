import streamlit as st
import pandas as pd
import random
import google.generativeai as genai
import os # For local testing if needed

st.set_page_config(layout="wide")
st.title("AI-Driven Staff Evaluation System")

# API Key handling for Streamlit Cloud
GOOGLE_API_KEY = st.secrets.get("AIzaSyDTZbt-Do_s_5__az0vx3SLbOup8-0e_nI")

if not GOOGLE_API_KEY:
    st.error("Google Generative AI APIキーが設定されていません。Streamlit CloudのSecretsまたはローカルの環境変数に設定してください。")
    st.stop() # Stop the app if API key is not set

genai.configure(api_key=GOOGLE_API_KEY)

# 1. Data Loading (using relative paths for app.py deployment)
# Assuming CSV files are in the same directory as app.py
try:
    df_staff = pd.read_csv('m_staff.csv')
    df_missions = pd.read_csv('m_missions.csv')
    df_evaluation_criteria = pd.read_csv('m_evaluation_criteria.csv')
except FileNotFoundError as e:
    st.error(f"CSVファイルが見つかりませんでした。`app.py`と同じディレクトリに配置してください: {e}")
    st.stop()

# 2. Job category mapping
job_category_mapping = {
    '管理者': '幹部',
    '副管理者兼サービス管理責任者': '幹部',
    '主任事務員': '事務',
    '事務員': '事務',
    '主任看護師': '医務',
    '看護師': '医務',
    '主任生活支援員': '支援',
    '副主任生活支援員': '支援',
    '生活支援員': '支援',
    '主任管理栄養士': '栄養',
    '管理栄養士': '栄養',
    '主任調理員': '栄養',
    '調理員': '栄養',
    '主任相談支援専門員': '支援',
    '相談支援専門員': '支援',
    '相談員': '支援'
}
df_staff['評価職種区分'] = df_staff['職種区分'].map(job_category_mapping)

# 3. Data Merging
df_merged_staff_missions = pd.merge(df_staff, df_missions, on='職員ID', how='inner')
df_integrated = pd.merge(
    df_merged_staff_missions,
    df_evaluation_criteria,
    left_on='評価職種区分',
    right_on='職種区分',
    how='inner'
)

# 4. get_staff_info function
def get_staff_info(staff_name):
    staff_data = df_integrated[df_integrated['氏名'] == staff_name]
    if staff_data.empty:
        return {}
    original_job_division = staff_data['職種区分_x'].unique().tolist()
    evaluation_job_division = staff_data['評価職種区分'].unique().tolist()
    basic_missions = staff_data['基本職務内容'].unique().tolist()
    return {
        '職員名': staff_name,
        '元の職種区分': original_job_division,
        '評価職種区分': evaluation_job_division,
        '基本職務内容': basic_missions
    }

# 5. get_evaluation_criteria function
def get_evaluation_criteria(evaluation_job_category):
    criteria_data = df_evaluation_criteria[df_evaluation_criteria['職種区分'] == evaluation_job_category]
    if criteria_data.empty:
        return []
    evaluation_items = criteria_data[['評価項目名', '重要度ウェイト']].to_dict(orient='records')
    return evaluation_items

# 6. simulate_evaluation function
def simulate_evaluation(staff_name):
    staff_info = get_staff_info(staff_name)
    if not staff_info or not staff_info['評価職種区分']:
        return {}
    evaluation_job_category = staff_info['評価職種区分'][0]
    evaluation_criteria = get_evaluation_criteria(evaluation_job_category)
    if not evaluation_criteria:
        return {}

    evaluated_items = []
    total_weighted_score = 0
    for item in evaluation_criteria:
        score = random.randint(1, 5) # Assign a random score between 1 and 5
        weighted_score = score * item['重要度ウェイト']
        total_weighted_score += weighted_score
        evaluated_items.append({
            '評価項目名': item['評価項目名'],
            '評価点': score,
            '重要度ウェイト': item['重要度ウェイト'],
            '加重評価点': weighted_score
        })

    # Dummy interviewer feedback
    interviewer_feedback = (
        "この職員は、指示された業務を常に正確かつ迅速に遂行し、チームへの貢献も大きい。"
        "特に問題解決能力が高く、困難な状況でも冷静に対応できる点が評価される。"
        "今後はリーダーシップの機会を増やし、若手職員の育成にも積極的に関わることが期待される。"
    )

    return {
        '職員名': staff_name,
        '評価職種区分': evaluation_job_category,
        '評価項目詳細': evaluated_items,
        '総合評価点': total_weighted_score,
        '面談者所感': interviewer_feedback
    }

# 7. generate_ai_prompt function
def generate_ai_prompt(evaluation_results):
    if not evaluation_results:
        return "評価結果が提供されていません。"
    prompt_parts = []
    prompt_parts.append(f"対象職員: {evaluation_results['職員名']}")
    prompt_parts.append(f"評価職種区分: {evaluation_results['評価職種区分']}\n")

    staff_info_re = get_staff_info(evaluation_results['職員名'])
    if staff_info_re and staff_info_re['基本職務内容']:
        prompt_parts.append("### 基本職務内容 ###")
        for mission in staff_info_re['基本職務内容']:
            prompt_parts.append(f"- {mission}")
        prompt_parts.append("\n")

    prompt_parts.append("### 評価項目詳細 ###")
    for item in evaluation_results['評価項目詳細']:
        prompt_parts.append(f"- 評価項目: {item['評価項目名']}")
        prompt_parts.append(f"  評価点: {item['評価点']}")
        prompt_parts.append(f"  重要度ウェイト: {item['重要度ウェイト']}")
        prompt_parts.append(f"  加重評価点: {item['加重評価点']}")
    prompt_parts.append("\n")

    prompt_parts.append(f"総合評価点: {evaluation_results['総合評価点']}\n")

    if '面談者所感' in evaluation_results:
        prompt_parts.append("### 面談者所感 ###")
        prompt_parts.append(evaluation_results['面談者所感'])
    prompt_parts.append("\n")

    prompt_parts.append("上記の評価結果に基づいて、この職員の強み、改善点、および今後の育成方針についてAIとして詳細に分析してください。")
    return "\n".join(prompt_parts)

# Streamlit UI
staff_names = df_staff['氏名'].unique().tolist()
selected_staff_name = st.selectbox("評価する職員を選択してください:", staff_names)

if st.button("評価シミュレーションとAI分析を実行"):
    with st.spinner("評価シミュレーションとAI分析を実行中..."):
        simulated_results = simulate_evaluation(selected_staff_name)

        if simulated_results:
            st.subheader(f"{simulated_results['職員名']} の評価シミュレーション結果")
            st.write(f"**評価職種区分:** {simulated_results['評価職種区分']}")
            st.write(f"**総合評価点:** {simulated_results['総合評価点']}")

            st.markdown("---")
            st.subheader("各評価項目詳細")
            for item in simulated_results['評価項目詳細']:
                st.write(f"- **{item['評価項目名']}**")
                st.write(f"  評価点: {item['評価点']}, 重要度ウェイト: {item['重要度ウェイト']}, 加重評価点: {item['加重評価点']}")

            st.markdown("---")
            st.subheader("面談者所感")
            st.write(simulated_results['面談者所感'])

            st.markdown("---")
            st.subheader("AIによる総合分析")

            ai_analysis_prompt = generate_ai_prompt(simulated_results)

            try:
                # Use the identified working model: models/gemini-pro-latest
                model = genai.GenerativeModel('models/gemini-pro-latest')
                ai_response = model.generate_content(ai_analysis_prompt)

                if ai_response and ai_response.text:
                    st.write("### AI分析結果 ###")
                    st.write(ai_response.text)

                    # Simple parsing of AI response
                    st.write("### 整形されたAI分析結果 ###")
                    sections = {}
                    current_section = None
                    keywords = ['強み:', '改善点:', '今後の育成方針:', '総合分析:', 'Strengths:', 'Improvements:', 'Development Plan:', 'Overall Analysis:']
                    lines = ai_response.text.split('\n')

                    for line in lines:
                        found_keyword = False
                        for keyword in keywords:
                            if keyword in line:
                                current_section = keyword.replace(':', '').strip()
                                sections[current_section] = []
                                remaining_line = line.split(keyword, 1)[1].strip()
                                if remaining_line:
                                    sections[current_section].append(remaining_line)
                                found_keyword = True
                                break
                        if not found_keyword and current_section:
                            sections[current_section].append(line.strip())

                    if sections:
                        for section_name, content_lines in sections.items():
                            st.markdown(f'\n### {section_name} ###')
                            for content_line in content_lines:
                                if content_line:
                                    st.write(f'  {content_line}')
                    else:
                        st.warning('AI分析結果をセクションに分割できませんでした。AIの出力形式を確認してください。')
                else:
                    st.error("AIからの有効な応答が得られませんでした。")

            except Exception as e:
                st.error(f"AIによる分析結果の生成中にエラーが発生しました: {e}")
        else:
            st.error(f"職員 '{selected_staff_name}' の評価シミュレーションに失敗しました。")
