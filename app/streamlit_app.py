"""
Founder BI Agent - Streamlit Dashboard

Run:
python -m streamlit run app/streamlit_app.py
"""


import sys
from pathlib import Path

sys.path.append(
    str(Path(__file__).resolve().parent.parent)
)


import streamlit as st


from app import (
    config,
    data_cleaning,
    leadership_update
)

from app.llm_agent import BIAgent

from app.monday_client import (
    MondayAPIError,
    MondayClient
)



# ---------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------

st.set_page_config(
    page_title="Founder BI Agent",
    page_icon="📊",
    layout="wide"
)



# ---------------------------------------------------------
# CUSTOM CSS
# ---------------------------------------------------------

st.markdown(
"""
<style>


.stApp{

background:#f8fafc;

}


/* Header */

.header{

font-size:40px;
font-weight:800;
color:#0f172a;

}


.sub{

font-size:18px;
color:#64748b;

}



/* Cards */

div[data-testid="metric-container"]{

background:white;
padding:20px;
border-radius:18px;
box-shadow:0px 5px 20px rgba(0,0,0,0.08);

}



/* Chat */

[data-testid="stChatMessage"]{

background:white;
border-radius:18px;
padding:15px;
box-shadow:0px 3px 12px rgba(0,0,0,0.05);

}



/* Buttons */

button{

border-radius:12px !important;

}



</style>

""",
unsafe_allow_html=True
)





# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------


if "loaded" not in st.session_state:

    st.session_state.loaded=False



if "chat_history" not in st.session_state:

    st.session_state.chat_history=[]





# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------


with st.sidebar:


    st.title("📊 Founder BI Agent")


    st.markdown(
    """
    ### AI Business Assistant

    ✅ monday.com Analytics

    ✅ Deal Tracking

    ✅ Work Order Monitoring

    ✅ Leadership Reports

    ---
    """
    )


    if st.session_state.loaded:

        st.success(
            "🟢 monday.com Connected"
        )

    else:

        st.warning(
            "Connecting..."
        )






# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------


def load_data():


    try:


        client = MondayClient(
            config.MONDAY_API_TOKEN
        )


        client.test_connection()



        raw_deals = client.get_all_items(
            config.DEALS_BOARD_ID
        )


        raw_workorders = client.get_all_items(
            config.WO_BOARD_ID
        )



        deals_df, deals_quality = (
            data_cleaning.clean_deals(
                raw_deals
            )
        )


        wo_df, wo_quality = (
            data_cleaning.clean_work_orders(
                raw_workorders
            )
        )



        st.session_state.deals_df=deals_df

        st.session_state.wo_df=wo_df


        st.session_state.deals_quality=deals_quality

        st.session_state.wo_quality=wo_quality



        st.session_state.loaded=True



    except Exception as e:


        st.error(
            f"Loading failed: {e}"
        )

        st.stop()






if not st.session_state.loaded:


    with st.spinner(
        "Loading monday.com data..."
    ):

        load_data()






# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------


st.markdown(
"""
<div class="header">

📊 Founder BI Agent

</div>


<div class="sub">

AI powered business intelligence dashboard for monday.com

</div>

""",
unsafe_allow_html=True
)




# ---------------------------------------------------------
# METRICS
# ---------------------------------------------------------


deals_df=st.session_state.deals_df

wo_df=st.session_state.wo_df


dq=st.session_state.deals_quality

wq=st.session_state.wo_quality



issues=(

sum(dq["missing_fields"].values())

+

sum(wq["missing_fields"].values())

)



c1,c2,c3=st.columns(3)



c1.metric(

"💼 Deals",

dq["total_rows"]

)



c2.metric(

"📋 Work Orders",

wq["total_rows"]

)



c3.metric(

"⚠️ Data Issues",

issues

)






# ---------------------------------------------------------
# DATA QUALITY
# ---------------------------------------------------------


with st.expander(
"🔍 Data Quality Report"
):


    st.write(
        "Deals Quality"
    )


    st.json(
        dq
    )


    st.write(
        "Work Orders Quality"
    )


    st.json(
        wq
    )







# ---------------------------------------------------------
# TABS
# ---------------------------------------------------------


chat_tab,update_tab=st.tabs(

[
"💬 AI Assistant",
"📋 Leadership Update"
]

)






# ---------------------------------------------------------
# CHAT
# ---------------------------------------------------------


with chat_tab:


    st.info(

"""
Ask questions:

• Which deals are closing soon?

• Show high value opportunities

• Which work orders are delayed?

• Summarize business performance

"""

)



    for msg in st.session_state.chat_history:


        avatar="🧑‍💼" if msg["role"]=="user" else "🤖"


        with st.chat_message(
            msg["role"],
            avatar=avatar
        ):


            st.write(
                msg["content"]
            )





    question=st.chat_input(

        "Ask business question..."

    )



    if question:


        st.session_state.chat_history.append(

        {

        "role":"user",

        "content":question

        }

        )



        with st.chat_message(
            "user",
            avatar="🧑‍💼"
        ):

            st.write(question)




        if not config.OPENAI_API_KEY:


            st.error(
            "OpenAI API key missing"
            )


        else:


            agent=BIAgent(

                deals_df,

                wo_df,

                dq,

                wq

            )



            history=[

            {

            "role":x["role"],

            "content":x["content"]

            }

            for x in st.session_state.chat_history

            ]



            with st.chat_message(

                "assistant",

                avatar="🤖"

            ):


                with st.spinner(
                    "Thinking..."
                ):


                    result=agent.answer(
                        history
                    )



                st.write(
                    result["text"]
                )



            st.session_state.chat_history.append(

            {

            "role":"assistant",

            "content":result["text"]

            }

            )






# ---------------------------------------------------------
# LEADERSHIP UPDATE
# ---------------------------------------------------------


with update_tab:


    st.subheader(
        "Founder Summary Generator"
    )



    if st.button(
        "Generate Report"
    ):



        with st.spinner(
            "Creating report..."
        ):


            report=(

            leadership_update.generate_leadership_update(

                deals_df,

                wo_df,

                dq,

                wq

            )

            )



        st.success(
            "Report Generated"
        )


        st.write(
            report
        )



        st.download_button(

        "Download Report",

        report,

        "leadership_update.md"

        )






# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------


st.markdown(

"""

<hr>

<center>

🚀 Founder BI Agent | Streamlit + monday.com + AI

</center>

""",

unsafe_allow_html=True

)