import streamlit as st
import pandas as pd
import numpy as np
import psycopg2
from datetime import datetime, timedelta, timezone
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode

    
def init_connection():
    return psycopg2.connect(**st.secrets["postgres"])
    
# Perform query.
# Uses st.experimental_memo to only rerun when the query changes or after 10 min.
# @st.experimental_memo(ttl=600)
def run_query(query):
    try:
        conn = init_connection()
        df = pd.read_sql(query,conn)
    except psycopg2.Error as e:
        # 데이터베이스 에러 처리
        print("DB error: ", e)
        conn.close()
    finally:
        conn.close()
    return df
            
def run_tx(query):
    try:
        conn = init_connection()
        with conn.cursor() as cur:
            cur.execute(query)
    except psycopg2.Error as e:
        # 데이터베이스 에러 처리
        print("DB error: ", e)
        conn.rollback()
        conn.close()
    finally:
        conn.commit()
        conn.close()
    return

st.set_page_config(page_title="대면 참석 신청")

datetime_utc = datetime.utcnow()
timezone_kst = timezone(timedelta(hours=9))
datetime_kst = datetime_utc.astimezone(timezone_kst)

### 강의일자 list
date_list = [datetime(2023, 3, 7, 11, 0, 0, tzinfo=timezone_kst), datetime(2023, 3, 9, 11, 0, 0, tzinfo=timezone_kst)]

### 참석인원 제한
student_limit = 50

for i in date_list:
    if i < datetime_kst:
        continue
    if i > datetime_kst:
        break

date_string = i.strftime("%Y-%m-%d")
if i < datetime_kst:
    st.title("현재 등록된 강의 일자가 없습니다.")
elif i > (datetime_kst + timedelta(hours=24)): 
    st.title("다음 대면 강의 일자: " + date_string)
else:
    st.title(date_string + " 강의 대면 참석 신청")
    
    # 현재 신청자 수 목록 조회 쿼리
    applycount_sql = f"SELECT count(*) FROM apply WHERE attend_date = '{date_string}' and canceled = False"
    # 만약 신청자 수 미달일 경우:
    if run_query(applycount_sql).iloc[0]['count'] < student_limit:
        # 신청
        st.subheader("아래에 신청 정보를 입력해주세요.")
        with st.form("my_form1"):
            sname = st.text_input('Name:', autocomplete="name", placeholder="ex: 홍길동")
            sid = st.text_input('Student ID:', autocomplete="on", placeholder="ex: 2023-00000", max_chars=10)
            spwd = st.text_input('Password:', type='password', max_chars=4, help='4자리 비밀번호 입력')
            apply_button = st.form_submit_button("신청")
            if apply_button:
                #입력 형식 체크
                if sname and sid and spwd:
                    if len(sid) < 10:
                        st.error("학번 형식을 다시 확인해주세요.")
                    elif len(spwd) < 4:
                        st.error("비밀번호 길이를 다시 확인해주세요.")
                    else:
                        # 이미 신청 기록이 있는지 확인
                        check_sql = f"SELECT * FROM apply WHERE sid = '{sid}' and attend_date = '{date_string}' and canceled = False"
                        if run_query(check_sql).empty:
                            # 신청 기록이 없을 경우 신청
                            datetime_utc = datetime.utcnow()
                            apply_timestamp = datetime_utc.astimezone(timezone_kst)
                            apply_sql = f"INSERT INTO apply (sname, sid, attend_date, apply_timestamp, secret) VALUES ('{sname}','{sid}','{date_string}','{apply_timestamp}','{spwd}')"
                            run_tx(apply_sql)
                            st.success("신청 완료!")
                        else:
                            st.error("이미 신청 정보가 존재합니다.")
                else:
                    st.error("모든 정보를 입력해주세요")
    # 신청자 수 초과한 경우
    else:
        st.markdown("## ⚠️신청 인원이 초과되어 현재 추가 신청이 불가능합니다.")

    # 신청 조회 및 취소
    st.subheader("신청 조회 및 취소")
    with st.form("my_form2"):
            sid = st.text_input('Student ID:', autocomplete="on", placeholder="ex: 2023-00000", max_chars=10)
            spwd = st.text_input('Password:', type='password', max_chars=4, help='4자리 비밀번호 입력')
            submitted = st.form_submit_button("조회")
            click_cancel = st.form_submit_button("신청 취소")
            # 조회 클릭
            if submitted:
                #입력 형식 체크
                if sid and spwd:
                    if len(sid) < 10:
                        st.error("학번 형식을 다시 확인해주세요.")
                    elif len(spwd) < 4:
                        st.error("비밀번호 길이를 다시 확인해주세요.")
                    else:
                        # 이미 신청 기록이 있는지 확인
                        check_sql = f"SELECT aid, sname as 이름, sid as 학번, attend_date as 참석일자 FROM apply WHERE sid = '{sid}' and attend_date = '{date_string}' and canceled = False and secret = '{spwd}'"
                        df_check = run_query(check_sql)
                        if df_check.empty:
                            st.error("해당 학번과 비밀번호로 신청된 정보가 없습니다.")
                        else:
                            # 신청 기록이 있을 경우
                            st.success("조회 완료!")
                            st.write(run_query(check_sql))
                else:
                    st.error("모든 정보를 입력해주세요")
            # 신청 취소 클릭
            if click_cancel:
                #입력 형식 체크
                if sid and spwd:
                    if len(sid) < 10:
                        st.error("학번 형식을 다시 확인해주세요.")
                    elif len(spwd) < 4:
                        st.error("비밀번호 길이를 다시 확인해주세요.")
                    else:
                        # 이미 신청 기록이 있는지 확인
                        check_sql = f"SELECT aid, sname as 이름, sid as 학번, attend_date as 참석일자 FROM apply WHERE sid = '{sid}' and attend_date = '{date_string}' and canceled = False and secret = '{spwd}'"
                        df_check = run_query(check_sql)
                        if df_check.empty:
                            st.error("해당 학번과 비밀번호로 신청된 정보가 없습니다.")
                        else:
                            # 신청 기록이 있을 경우
                            aid = df_check.iloc[0]['aid']
                            cancel_sql = f"UPDATE apply SET canceled = True WHERE aid = '{aid}'"
                            run_tx(cancel_sql)
                            st.success("취소 완료!")
                else:
                    st.error("모든 정보를 입력해주세요")