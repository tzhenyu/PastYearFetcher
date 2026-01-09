import streamlit as st
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth
import hashlib
import zipfile
import io

SESSION_KEYS = {
    "past_year_title": "",
    "selected_faculty": "All",
    "search_results": [],
    "username": "",
    "password": "",
    "cred_saved": False,
    "clear_on_next_run": False,
    "has_searched": False,
    "dialog_shown": False
}

FACULTY_ABBR = {
    "Faculty of Accountancy, Finance and Business": "FAFB",
    "Faculty of Applied Sciences": "FOAS",
    "Faculty of Computing and Information Technology": "FOCS",
    "Faculty of Built Environment": "FOBE",
    "Faculty of Engineering and Technology": "FOET",
    "Faculty of Communication and Creative Industries": "FCCI",
    "Faculty of Social Science and Humanities": "FSSH",
    "Centre for Pre-University Studies": "Foundation"
}

@st.dialog("Welcome!")
def disclaimer_dialog():
    st.markdown("This is a personal project and is not affiliated with TAR UMT in any way. Use at your own risk.")
    st.markdown("This project does not store any of your credentials or data. All data is fetched directly from TAR UMT's ePrints system.")
    st.markdown("You can check the source code [here](https://github.com/tzhenyu/PastYearFetcher/blob/main/pastyearfetcher.py).")
    st.markdown("Made by [tzhenyu](https://github.com/tzhenyu)")
   
def initialize_session_state():
    """Initialize all session state variables."""
    for key, default in SESSION_KEYS.items():
        if key not in st.session_state:
            st.session_state[key] = default

def search_paper(past_year_title, selected_faculty):
    query = past_year_title.replace(" ", "+")
    rss_url = f"https://eprints.tarc.edu.my/cgi/search/archive/advanced/export_eprints_RSS2.xml?screen=Search&dataset=archive&_action_export=1&output=RSS2&exp=0%7C1%7C-date%2Fcreators_name%2Ftitle%7Carchive%7C-%7Ctitle%3Atitle%3AALL%3AIN%3A{query}%7Ctype%3Atype%3AANY%3AEQ%3Ateaching_resource%7C-%7Ceprint_status%3Aeprint_status%3AANY%3AEQ%3Aarchive%7Cmetadata_visibility%3Ametadata_visibility%3AANY%3AEQ%3Ashow&n="
    response = requests.get(rss_url)
    if response.status_code != 200:
        return []
    xml_content = response.text
    root = ET.fromstring(xml_content)
    results = []

    faculty_full_names = list(FACULTY_ABBR.keys())
    
    for child in root.findall(".//channel/item"):
        try:
            title = child.find("title").text.strip().split(" (")[0]            
            link = child.find("link").text
            description = child.find("description").text.split(".")[0]
            year = description.split(" (")[1].split(")")[0]
            month = description.split(",")[-1].removesuffix(" Examination)")

            # Find which faculties are mentioned in the description
            faculties_found = [faculty for faculty in faculty_full_names if faculty in description]
            

            if faculties_found and "Tunku Abdul Rahman" in description:
                # Convert full faculty names to abbreviations for display
                faculty_abbrs = [FACULTY_ABBR[f] for f in faculties_found]
                
                if selected_faculty == "All" or selected_faculty in faculty_abbrs:
                    results.append({
                        "title": title,
                        "faculties": faculty_abbrs, 
                        "link": link,
                        "year": year,
                        "month": month
                    })
        except Exception:
            continue
    return results

def list_paper_section(results):
    username = st.session_state.get('username', '')
    password = st.session_state.get('password', '')
    
    # Initialize pagination state
    if 'papers_per_page' not in st.session_state:
        st.session_state.papers_per_page = 6
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    
    if not results:
        return
    
    # Pagination controls at the top
    total_papers = len(results)
    total_pages = (total_papers - 1) // st.session_state.papers_per_page + 1
    
    # Calculate which papers to show FIRST
    start_idx = (st.session_state.current_page - 1) * st.session_state.papers_per_page
    end_idx = min(start_idx + st.session_state.papers_per_page, total_papers)
    current_page_papers = results[start_idx:end_idx]
    
    # Fetch PDFs only for current page
    if username and password and current_page_papers:
        uncached = [p for p in current_page_papers if f"pdf_{hashlib.md5(p['link'].encode()).hexdigest()}" not in st.session_state]
        if uncached:
            progress_bar = st.progress(0)
            for idx, paper in enumerate(uncached):
                pdf_url = get_pdf_url(paper['link'])
                if pdf_url:
                    pdf_response = requests.get(pdf_url, auth=HTTPBasicAuth(username, password))
                    if pdf_response.status_code == 200:
                        paper_key = f"pdf_{hashlib.md5(paper['link'].encode()).hexdigest()}"
                        st.session_state[paper_key] = pdf_response.content
                progress_bar.progress((idx + 1) / len(uncached))
            st.rerun()
    
    # Callback functions
    def next_page():
        if st.session_state.current_page < total_pages:
            st.session_state.current_page += 1
    
    def prev_page():
        if st.session_state.current_page > 1:
            st.session_state.current_page -= 1
    
    with st.container(border=True):
        col1, col2, col3 = st.columns([1, 5, 1])
        with col1:
            st.button("⬅️ Previous", disabled=st.session_state.current_page == 1, on_click=prev_page, key="prev_top")
        with col2:
            st.markdown(f"<center>Page {st.session_state.current_page} of {total_pages} ({total_papers} papers)</center>", unsafe_allow_html=True)
        with col3:
            st.button("Next ➡️", disabled=st.session_state.current_page >= total_pages, on_click=next_page, key="next_top")
        
    # Display papers for current page
    for paper in current_page_papers:
        with st.container(border=True):
            st.markdown(f"<b>{paper['title']}</b> ", unsafe_allow_html=True)
            
            faculties_str = ", ".join(paper['faculties'])
            
            st.markdown(f"{paper['year']}{paper['month']} · {faculties_str}", unsafe_allow_html=True)
            
            paper_key = f"pdf_{hashlib.md5(paper['link'].encode()).hexdigest()}"
            filename = f"{paper['title']}_{paper['year']}{paper['month']}"
            filename = filename.replace(" ", "_")            
            if paper_key in st.session_state:
                st.download_button(
                    label="⬇️",
                    data=st.session_state[paper_key],
                    file_name=f"{filename}.pdf",
                    mime="application/pdf",
                    key=f"download_{paper['link']}"   
                )
            else:
                st.info("Log In your TAR UMT credentials to get the paper!")
    
    # Pagination controls at the bottom
    with st.container(border=True):
        col1, col2, col3 = st.columns([1, 5, 1])
        with col1:
            st.button("⬅️ Prev", disabled=st.session_state.current_page == 1, on_click=prev_page, key="prev_bottom")
        with col2:
            st.markdown(f"<center>Page {st.session_state.current_page} of {total_pages}</center>", unsafe_allow_html=True)
        with col3:
            st.button("Next ➡️", disabled=st.session_state.current_page >= total_pages, on_click=next_page, key="next_bottom")

def get_pdf_url(paper_link):
    """Extract PDF URL from paper page."""
    response = requests.get(paper_link)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        meta_tags = soup.find_all("meta", attrs={"name": "eprints.document_url"})
        for tag in meta_tags:
            if tag.has_attr("content"):
                return tag['content']
    return None
            

def create_batch_zip(results, year_from=None, year_to=None):
    """Create a ZIP file containing multiple PDFs."""
    username = st.session_state.get('username', '')
    password = st.session_state.get('password', '')
    
    if not username or not password:
        st.error("Please login first")
        return None
    
    # Filter by year range if specified
    if year_from is not None and year_to is not None:
        filtered_papers = [p for p in results if int(year_from) <= int(p['year']) <= int(year_to)]
    else:
        filtered_papers = results
    
    if not filtered_papers:
        st.warning(f"No papers found for year range {year_from} - {year_to}")
        return None
    
    zip_buffer = io.BytesIO()
    
    with st.spinner(f"Preparing {len(filtered_papers)} papers..."):
        progress_bar = st.progress(0)
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for idx, paper in enumerate(filtered_papers):
                paper_key = f"pdf_{hashlib.md5(paper['link'].encode()).hexdigest()}"
                
                # Check if already cached
                if paper_key not in st.session_state:
                    pdf_url = get_pdf_url(paper['link'])
                    if pdf_url:
                        pdf_response = requests.get(pdf_url, auth=HTTPBasicAuth(username, password))
                        if pdf_response.status_code == 200:
                            st.session_state[paper_key] = pdf_response.content
                
                # Add to ZIP if we have the content
                if paper_key in st.session_state:
                    # Clean filename: replace problematic characters
                    filename = f"{paper['title']}_{paper['year']}{paper['month']}.pdf"
                    # Remove path separators and other problematic characters
                    filename = filename.replace("/", "_").replace("\\", "_").replace(":", "_")
                    filename = filename.replace(" ", "_")
                    # Ensure it's just a filename, not a path
                    filename = filename.split("/")[-1].split("\\")[-1]
                    
                    zip_file.writestr(filename, st.session_state[paper_key])
                
                progress_bar.progress((idx + 1) / len(filtered_papers))
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def login_section():
    with st.container(border=True):
        st.text("Enter TARUMT credentials for the access")
        username_input = st.text_input("Username", key="eprints_username")
        password_input = st.text_input("Password", type="password", key="eprints_password")
        submit_cred = st.button("Submit")
        if submit_cred:
            st.session_state.username = username_input
            st.session_state.password = password_input
            st.session_state.cred_saved = True
            st.success("Credentials Submitted")

def batch_download_section(course, selected_faculty):
    with st.container(border=True):
        st.text("Batch Download")
        
        # Get unique years from results
        results = search_paper(course, selected_faculty) if course else []
        
        if results:
            years_asc = sorted(set(p['year'] for p in results), reverse=False)
            years_desc = sorted(set(p['year'] for p in results), reverse=True)
            
            # Year range selection
            col_from, col_to = st.columns(2)
            with col_from:
                year_from = st.selectbox("From", years_asc, key="year_from")
            with col_to:
                year_to = st.selectbox("To", years_desc, key="year_to")
            
            if st.button("📦 Download Batch"):
                # Convert years to integers for comparison
                year_start = int(year_from)
                year_end = int(year_to)
                
                # Ensure start <= end
                if year_start > year_end:
                    year_start, year_end = year_end, year_start
                
                zip_data = create_batch_zip(results, year_start, year_end)
                
                if zip_data:
                    st.download_button(
                        label="💾 Download ZIP",
                        data=zip_data,
                        file_name=f"papers_{year_start}_to_{year_end}_{course}.zip",
                        mime="application/zip",
                        key="batch_download"
                    )
        else:

            st.info("Search for papers first")

def clear_search():
    st.session_state.course_input = ""
    st.session_state.current_page = 1

def main():
    if "dialog_shown" not in st.session_state:
        disclaimer_dialog()
        st.session_state.dialog_shown = True    

    st.set_page_config(page_title="Past Year Fetcher", page_icon="📃", layout="wide")
    st.title("TAR UMT Past Year Fetcher")

    col1, col2, col3 = st.columns([5,1,1], vertical_alignment='bottom')
    with col1:
        course = st.text_input("Course Name / Course Code", key="course_input")
    with col2:
        selected_faculty = st.selectbox(
            "Filter by Faculty",
            ["All"] + list(FACULTY_ABBR.values()),
            key="selected_faculty",
            on_change=lambda: setattr(st.session_state, 'faculty_changed', True)
        )
    with col3:
        st.button("Clear", use_container_width=True, on_click=clear_search)

    col1, col2 = st.columns([2,3])
    with col1:
        login_section()
        batch_download_section(course, selected_faculty)
    with col2:
        results = search_paper(course, selected_faculty) if course else []
        list_paper_section(results)

if __name__ == "__main__":
    main()
    initialize_session_state()

    print('Reloaded! All good!')
