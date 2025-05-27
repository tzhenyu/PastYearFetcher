import streamlit as st
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth
import hashlib

faculties = [
    "Faculty of Accountancy, Finance and Business",
    "Faculty of Applied Sciences",
    "Faculty of Computing and Information Technology",
    "Faculty of Built Environment",
    "Faculty of Engineering and Technology",
    "Faculty of Communication and Creative Industries",
    "Faculty of Social Science and Humanities"
]

faculty_abbr = {
    "Faculty of Accountancy, Finance and Business": "FAFB",
    "Faculty of Applied Sciences": "FOAS",
    "Faculty of Computing and Information Technology": "FOCS",
    "Faculty of Built Environment": "FOBE",
    "Faculty of Engineering and Technology": "FOET",
    "Faculty of Communication and Creative Industries": "FCCI",
    "Faculty of Social Science and Humanities": "FSSH"
}

def search_paper(past_year_title, selected_faculty):
    query = past_year_title.replace(" ", "+")
    rss_url = f"https://eprints.tarc.edu.my/cgi/search/simple/export_eprints_RSS2.xml?screen=Search&dataset=archive&_action_export=1&output=RSS2&exp=0%7C1%7C-date%2Fcreators_name%2Ftitle%7Carchive%7C-%7Cq%3Aabstract%2Fcreators_name%2Fdate%2Fdocuments%2Ftitle%3AALL%3AIN%3A{query}%7C-%7Ceprint_status%3Aeprint_status%3AANY%3AEQ%3Aarchive%7Cmetadata_visibility%3Ametadata_visibility%3AANY%3AEQ%3Ashow&n="
    response = requests.get(rss_url)
    if response.status_code != 200:
        return []
    xml_content = response.text
    root = ET.fromstring(xml_content)
    results = []
    for child in root.findall(".//channel/item"):
        try:
            title = child.find("title").text.split(" (")[0]
            link = child.find("link").text
            description = child.find("description").text.split(".")[0]
            year = description.split(" (")[1].split(")")[0]
            month = description.split(",")[-1].removesuffix(" Examination)")
            faculties_found = [faculty for faculty in faculties if faculty in description]
            if faculties_found and "Tunku Abdul Rahman" in description:
                if selected_faculty == "All" or selected_faculty in faculties_found:
                    results.append({
                        "title": title,
                        "faculties": faculties_found,
                        "link": link,
                        "year": year,
                        "month": month
                    })
        except Exception:
            continue
    return results

def handle_credentials():
    """Handle the credentials input and storage in session state."""
    with st.expander("Please put your TAR UMT credentials.", expanded=True):
        username_input = st.text_input("Username", key="eprints_username")
        password_input = st.text_input("Password", type="password", key="eprints_password")
        submit_cred = st.button("Submit")
        if submit_cred:
            st.session_state.username = username_input
            st.session_state.password = password_input
            st.session_state.cred_saved = True
            st.success("Credentials saved!")
    return st.session_state.username, st.session_state.password
def handle_pdf_actions(col, paper, username, password):
    """Handle PDF fetch and download actions for a paper."""
    with col:
        paper_key = f"pdf_{hashlib.md5(paper['link'].encode()).hexdigest()}"
        
        if paper_key not in st.session_state:
            # Fetch PDF content immediately
            response = requests.get(paper['link'])
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                meta_tags = soup.find_all("meta", attrs={"name": "eprints.document_url"})
                for tag in meta_tags:
                    if tag.has_attr("content"):
                        pdf_url = tag['content'] + "?download=1"
                        pdf_response = requests.get(pdf_url, auth=HTTPBasicAuth(username, password))
                        if pdf_response.status_code == 200:
                            filename = f"{paper['title']}_{paper['year']}_{paper['month']}.pdf"
                            filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))
                            
                            # Add Content-Disposition header to force download
                            headers = {
                                'Content-Type': 'application/pdf',
                                'Content-Disposition': f'attachment; filename="{filename}"'
                            }
                            
                            st.session_state[paper_key] = {
                                'content': pdf_response.content,
                                'filename': filename,
                                'headers': headers,
                                'status': 'success'
                            }
                            break
                        elif pdf_response.status_code == 401:
                            st.session_state[paper_key] = {'status': 'unauthorized'}
                            break
            else:
                st.session_state[paper_key] = {'status': 'not_found'}
        
        # Show appropriate button/message based on status
        if paper_key in st.session_state:
            data = st.session_state[paper_key]
            if data.get('status') == 'success':
                st.download_button(
                    label="Get",
                    data=data['content'],
                    file_name=data['filename'],
                    mime="application/pdf",
                    key=f"download_{paper_key}",
                    help=f"Download {data['filename']}",
                    use_container_width=True,
                
                )

            elif data.get('status') == 'unauthorized':
                st.error("Invalid password or username")
            else:
                st.warning("⚠️")

@st.dialog("Welcome!")
def disclaimer_dialog():
    st.markdown("This is a personal project and is not affiliated with TAR UMT in any way. Use at your own risk.")
    st.markdown("This project does not store any of your credentials or data. All data is fetched directly from TAR UMT's ePrints system.")
    st.markdown("You can check the source code [here](https://github.com/tzhenyu/PastYearFetcher/blob/main/pastyearfetcher.py) to assure your data is safe.")
    st.markdown("Made by [tzhenyu](https://github.com/tzhenyu)")
   

def main():
    if "dialog_shown" not in st.session_state:
        disclaimer_dialog()  # Show dialog only first time
        st.session_state.dialog_shown = True
    
    st.title("TAR UMT's Past Years Fetcher")
 
 
    
    st.markdown("""
        <style>
            /* Reduce font size for mobile */
            @media (max-width: 740px) {
                /* Reduce padding */
                .block-container {
                    padding-top: 2.5rem ;
                    padding-bottom: 2.5rem ;
                }

                /* Header font size */
                h1 {
                    font-size: 20px !important;}

                /* Standardize all buttons */
                .stButton button,
                div[data-testid="stDownloadButton"] button {
                    padding: 0.25rem 0.5rem !important;
                    font-size: 12px !important;
                    width: 100% !important;
                    min-height: 32px !important;
                    box-sizing: border-box !important;
                }

                /* Remove extra padding/margin from download button container */
                div[data-testid="stDownloadButton"] {
                    width: 100% !important;
                    margin: 0 !important;
                    padding: 0 !important;
                }

                /* Ensure button containers have same width */
                div.element-container {
                    width: 100% !important;
                }
            }
        </style>
    """, unsafe_allow_html=True)

    # --- Session State Initialization ---
    for key, default in [
        ("past_year_title", ""),
        ("selected_faculty", "All"),
        ("search_results", []),
        ("username", ""),
        ("password", ""),
        ("cred_saved", False),
        ("clear_on_next_run", False),
        ("has_searched", False),
        ("dialog_shown", False)
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # --- Credentials Box ---
    username, password = handle_credentials()

    # --- Clear logic ---
    if st.session_state.clear_on_next_run:
        st.session_state.past_year_title = ""
        st.session_state.selected_faculty = "All"
        st.session_state.search_results = []
        for key in list(st.session_state.keys()):
            if key.startswith('pdf_'):
                del st.session_state[key]
        st.session_state.clear_on_next_run = False

    # --- Search UI ---
    col_course_code, col_faculty = st.columns([5, 2])
    with col_course_code:
        faculty_options = ["All"] + faculties
        past_year_title = st.text_input(
            "Course Code e.g. BACS1013",
            key="past_year_title"
        )
    with col_faculty:
        faculty_display = {"All": "All"} | {f: faculty_abbr[f] for f in faculties}
        selected_faculty = st.selectbox(
            "Filter by Faculty",
            faculty_options,
            format_func=lambda x: faculty_display[x],
            key="selected_faculty"
        )

    col_search, col_clear, col_empty = st.columns([2, 2, 13])
    with col_search:
        search_clicked = st.button("Search")
    with col_clear:
        clear_clicked = st.button("Clear")

    # --- Search and Clear Actions ---
    if search_clicked:
        st.session_state.has_searched = True  # Set to True when search is clicked
        if past_year_title:
            st.session_state.search_results = search_paper(past_year_title, selected_faculty)
        else:
            st.session_state.search_results = []
    if clear_clicked:
        st.session_state.clear_on_next_run = True
        st.session_state.has_searched = False  # Reset search state
        st.rerun()

    results = st.session_state.search_results

    # --- Results Display ---
    if results and not st.session_state.clear_on_next_run:
        st.success(f"{len(results)} result(s) found!")
        st.markdown("""
            <style>
                @media (max-width: 640px) {

                    /* Reduce text size */
                    .stMarkdown p {
                        font-size: 15px !important;
                        margin: 0 !important;
                        white-space: nowrap !important;
                        overflow: hidden !important;
                        text-overflow: ellipsis !important;
                    }

                }
            </style>
        """, unsafe_allow_html=True)
        for idx, paper in enumerate(results):
            abbrs = [faculty_abbr.get(f, f) for f in paper['faculties']]

            col1, col2 = st.columns([6,1])
            with col1:
                abbrs = [faculty_abbr.get(f, f) for f in paper['faculties']]
                
                st.write(f"{paper['year']} - {paper['month']} | {', '.join(abbrs)} | {paper['title']}")

            with col2:
                handle_pdf_actions(col2, paper, username, password)
    elif st.session_state.has_searched and not st.session_state.clear_on_next_run:
        st.warning("No results found.")

if __name__ == "__main__":
    main()
    print('Reloaded! All good!')