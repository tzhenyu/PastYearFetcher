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

def main():
    st.title("TAR UMT's Past Years Fetcher")
    st.markdown("Made by [@tzhenyu](https://github.com/tzhenyu)")
    st.markdown("This project does not store any of your credentials. You may check the source code [here](https://github.com/tzhenyu/PastYearFetcher/blob/main/pastyearfetcher.py)")
    st.markdown("This is a personal project and is not affiliated with TAR UMT in any way. Use at your own risk.")

    # --- Session State Initialization ---
    for key, default in [
        ("past_year_title", ""),
        ("selected_faculty", "All"),
        ("search_results", []),
        ("username", ""),
        ("password", ""),
        ("cred_saved", False),
        ("clear_on_next_run", False)
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # --- Credentials Box ---
    with st.expander("Please put your TAR UMT credentials to download the PDF files.", expanded=True):
        username_input = st.text_input("Username", key="eprints_username")
        password_input = st.text_input("Password", type="password", key="eprints_password")
        submit_cred = st.button("Submit Credentials")
        if submit_cred:
            st.session_state.username = username_input
            st.session_state.password = password_input
            st.session_state.cred_saved = True
            st.success("Credentials saved!")

    username = st.session_state.username
    password = st.session_state.password

    # --- Clear logic ---
    if st.session_state.clear_on_next_run:
        st.session_state.past_year_title = ""
        st.session_state.selected_faculty = "All"
        st.session_state.search_results = []
        st.session_state.clear_on_next_run = False

    # --- Search UI ---
    faculty_options = ["All"] + faculties
    past_year_title = st.text_input(
        "Course Code e.g. BACS1013",
        key="past_year_title"
    )
    selected_faculty = st.selectbox(
        "Filter by Faculty",
        faculty_options,
        key="selected_faculty"
    )

    col_search, col_clear, _ = st.columns([1, 1, 6])
    with col_search:
        search_clicked = st.button("Search")
    with col_clear:
        clear_clicked = st.button("Clear")

    # --- Search and Clear Actions ---
    if search_clicked:
        if past_year_title:
            st.session_state.search_results = search_paper(past_year_title, selected_faculty)
        else:
            st.session_state.search_results = []
    if clear_clicked:
        st.session_state.clear_on_next_run = True
        st.rerun()

    results = st.session_state.search_results

    # --- Results Display ---
    if results:
        st.write(f"{len(results)} result(s) found!")
        for idx, paper in enumerate(results):
            col1, col2, col3, col4 = st.columns([1, 2, 1, 2])
            with col1:
                st.write(f"{paper['year']}")
            with col2:
                st.write(f"{paper['month']}")
            with col3:
                abbrs = [faculty_abbr.get(f, f) for f in paper['faculties']]
                st.write(f"{', '.join(abbrs)}")
            with col4:
                # Fetch the PDF download link from the paper page
                # Create a unique key for this paper's PDF in session state
                paper_key = f"pdf_{hashlib.md5(paper['link'].encode()).hexdigest()}"
                if paper_key not in st.session_state:
                    response = requests.get(paper['link'])
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, "html.parser")
                        meta_tags = soup.find_all("meta", attrs={"name": "eprints.document_url"})
                        pdf_content = None
                        for i, tag in enumerate(meta_tags):
                            if tag.has_attr("content"):
                                pdf_url = tag['content'] + "?download=1"
                                pdf_response = requests.get(pdf_url, auth=HTTPBasicAuth(username, password))
                                if pdf_response.status_code == 200:
                                    pdf_content = pdf_response.content
                                    break
                                elif pdf_response.status_code == 401:
                                    st.warning("❌ Invalid Credential: Please check your username and password.")
                                    break
                        st.session_state[paper_key] = pdf_content
                    else:
                        st.session_state[paper_key] = None

                pdf_content = st.session_state[paper_key]
                if pdf_content:
                    st.download_button(
                        label=f"📥 Download PDF",
                        data=pdf_content,
                        file_name=f"{paper['title']} - {paper['year']}{paper['month']}.pdf",
                        mime="application/pdf",
                        key=f"download_{paper_key}"
                    )
                elif pdf_content is None:
                    st.warning("⚠ Could not fetch the PDF file or not available.")

if __name__ == "__main__":
    main()