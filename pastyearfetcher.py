import streamlit as st
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth
import hashlib
import pandas as pd
import base64

# Constants
FACULTIES = [
    "Faculty of Accountancy, Finance and Business",
    "Faculty of Applied Sciences",
    "Faculty of Computing and Information Technology",
    "Faculty of Built Environment",
    "Faculty of Engineering and Technology",
    "Faculty of Communication and Creative Industries",
    "Faculty of Social Science and Humanities"
]

FACULTY_ABBR = {
    "Faculty of Accountancy, Finance and Business": "FAFB",
    "Faculty of Applied Sciences": "FOAS",
    "Faculty of Computing and Information Technology": "FOCS",
    "Faculty of Built Environment": "FOBE",
    "Faculty of Engineering and Technology": "FOET",
    "Faculty of Communication and Creative Industries": "FCCI",
    "Faculty of Social Science and Humanities": "FSSH"
}

# Session state keys
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


def sanitize_filename(filename):
    """Sanitize filename for safe file download."""
    return "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))


def create_error_message(paper_title, error_type):
    """Create standardized error messages for PDF download failures."""
    error_messages = {
        'unauthorized': f"Invalid credentials for {paper_title}",
        'not_found': f"PDF not found for {paper_title}",
        'access_failed': f"Failed to access {paper_title}",
        'download_failed': f"Download failed for {paper_title}"
    }
    return error_messages.get(error_type, f"Unknown error for {paper_title}")


def generate_download_script(b64_content, safe_filename, delay_ms):
    """Generate JavaScript for automatic PDF download."""
    return f"""
    <script>
    setTimeout(function() {{
        try {{
            const data = atob('{b64_content}');
            const bytes = new Uint8Array(data.length);
            for (let i = 0; i < data.length; i++) {{
                bytes[i] = data.charCodeAt(i);
            }}
            const blob = new Blob([bytes], {{type: 'application/pdf'}});
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '{safe_filename}';
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }} catch(e) {{
            console.error('Download failed:', e);
        }}
    }}, {delay_ms});
    </script>
    """


def initialize_session_state():
    """Initialize all session state variables."""
    for key, default in SESSION_KEYS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def apply_custom_styles():
    """Apply custom CSS styles for mobile responsiveness and UI improvements."""
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
                div[data-testid="stDownloadButton"] button,
                div[data-testid="stPopover"] button {
                    padding: 0.25rem 0.5rem !important;
                    font-size: 12px !important;
                    width: 100% !important;
                    min-height: 32px !important;
                    box-sizing: border-box !important;
                }

                /* Ensure button containers have same width */
                div.element-container {
                    width: 100% !important;
                }
            }
            
            /* Toast styling */
            div[data-testid=stToastContainer] {
                align-items: end;
                position: sticky; 
            }
                
            div[data-testid=stToastContainer] {
                position: fixed !important;
                bottom: 10% !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
            }           
             
            [data-testid=stToastContainer] [data-testid=stMarkdownContainer] > p {
                font-size: 1.5rem;
                padding: 10px 10px 10px 10px;
            }
        </style>
    """, unsafe_allow_html=True)


def clear_session_data():
    """Clear search results and PDF cache from session state."""
    st.session_state.past_year_title = ""
    st.session_state.selected_faculty = "All"
    st.session_state.search_results = []
    for key in list(st.session_state.keys()):
        if key.startswith('pdf_'):
            del st.session_state[key]
    st.session_state.clear_on_next_run = False


def show_toast_messages(successful_downloads, failed_downloads):
    """Show appropriate toast messages for download results."""
    if successful_downloads:
        st.toast(f"{len(successful_downloads)} paper(s) downloaded automatically!", icon='✅')
    
    if failed_downloads:
        st.toast(f"{len(failed_downloads)} paper(s) failed to download:", icon='❌')
        for error_msg in failed_downloads:
            st.toast(f"• {error_msg}")


def create_display_dataframe(results):
    """Create and format DataFrame for display."""
    df = pd.DataFrame(results)
    df['faculties_str'] = df['faculties'].apply(lambda x: ', '.join([FACULTY_ABBR.get(f, f) for f in x]))
    
    # Reorder and rename columns for display
    display_df = df[['year', 'month', 'faculties_str']].copy()
    display_df['Select'] = False  # Add checkbox column
    display_df.columns = ['Year', 'Month', 'Faculties', 'Select']
    return display_df


def get_data_editor_config():
    """Get configuration for the data editor."""
    return {
        "Select": st.column_config.CheckboxColumn(
            "Select",
            default=False
        )
    }


def process_downloads(selected_indices, results, username, password):
    """Process PDF downloads for selected papers."""
    st.toast(f"Processing {len(selected_indices)} selected paper(s)...", icon='🔄')
    successful_downloads = []
    failed_downloads = []
    download_scripts = []
    
    for idx in selected_indices:
        paper = results[idx]
        success, content, filename = handle_pdf_actions(paper, username, password)
        
        if success:
            # Clean filename for JavaScript
            safe_filename = filename.replace("'", "\\'").replace('"', '\\"')
            b64_content = base64.b64encode(content).decode()
            
            download_script = generate_download_script(b64_content, safe_filename, idx * 1000)
            download_scripts.append(download_script)
            successful_downloads.append(filename)
        else:
            failed_downloads.append(filename)
    
    # Show toast messages and execute downloads
    show_toast_messages(successful_downloads, failed_downloads)
    
    if download_scripts:
        # Execute all download scripts with delay
        combined_script = "".join(download_scripts)
        st.components.v1.html(combined_script, height=0)


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
            faculties_found = [faculty for faculty in FACULTIES if faculty in description]
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


def handle_pdf_actions(paper, username, password):
    """Handle PDF fetch and return content for a paper."""
    paper_key = f"pdf_{hashlib.md5(paper['link'].encode()).hexdigest()}"
    
    if paper_key not in st.session_state:
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
                        filename = sanitize_filename(filename)
                        
                        st.session_state[paper_key] = {
                            'content': pdf_response.content,
                            'filename': filename,
                            'status': 'success'
                        }
                        return True, pdf_response.content, filename
                    elif pdf_response.status_code == 401:
                        st.session_state[paper_key] = {'status': 'unauthorized'}
                        return False, None, create_error_message(paper['title'], 'unauthorized')
            st.session_state[paper_key] = {'status': 'not_found'}
            return False, None, create_error_message(paper['title'], 'not_found')
        else:
            st.session_state[paper_key] = {'status': 'not_found'}
            return False, None, create_error_message(paper['title'], 'access_failed')
    
    # Handle already processed papers
    data = st.session_state[paper_key]
    if data.get('status') == 'success':
        return True, data['content'], data['filename']
    elif data.get('status') == 'unauthorized':
        return False, None, create_error_message(paper['title'], 'unauthorized')
    else:
        return False, None, create_error_message(paper['title'], 'download_failed')

@st.dialog("Welcome!")
def disclaimer_dialog():
    st.markdown("This is a personal project and is not affiliated with TAR UMT in any way. Use at your own risk.")
    st.markdown("This project does not store any of your credentials or data. All data is fetched directly from TAR UMT's ePrints system.")
    st.markdown("You can check the source code [here](https://github.com/tzhenyu/PastYearFetcher/blob/main/pastyearfetcher.py)")
    st.markdown("Made by [tzhenyu](https://github.com/tzhenyu).")
   

def main():
    if "dialog_shown" not in st.session_state:
        disclaimer_dialog()  # Show dialog only first time
        st.session_state.dialog_shown = True
    
    st.title("TAR UMT Past Years Fetcher")
    
    # Apply custom CSS styles
    apply_custom_styles()

    # Initialize session state variables
    initialize_session_state()

    # Get credentials from session state
    username, password = st.session_state.username, st.session_state.password

    # Handle clear logic
    if st.session_state.clear_on_next_run:
        clear_session_data()

    # --- Search UI ---
    past_year_title = st.text_input(
        "Course Code e.g. BACS1013",
        key="past_year_title"
    )

    col_login, col_search, col_clear,col_empty, col_download_ticked  = st.columns([3, 3, 3, 12,1])
    with col_search:
        search_clicked = st.button("Search")
    with col_clear:
        clear_clicked = st.button("Clear")
    with col_login:
        with st.popover("Login"):
            st.text("Enter TARUMT credentials for download access.")
            st.text("This project does not store any credential.")
            username_input = st.text_input("Username", key="eprints_username")
            password_input = st.text_input("Password", type="password", key="eprints_password")
            submit_cred = st.button("Submit")
            if submit_cred:
                st.session_state.username = username_input
                st.session_state.password = password_input
                st.session_state.cred_saved = True
                st.success("Credentials saved!")
    with col_download_ticked:
        pass  # Download button will appear only when results are found


    # --- Search and Clear Actions ---
    if search_clicked:
        st.session_state.has_searched = True  # Set to True when search is clicked
        if past_year_title:
            st.session_state.search_results = search_paper(past_year_title, "All")
        else:
            st.session_state.search_results = []
    if clear_clicked:
        st.session_state.clear_on_next_run = True
        st.session_state.has_searched = False  # Reset search state
        st.rerun()

    results = st.session_state.search_results

    # --- Results Display ---
    if results and not st.session_state.clear_on_next_run:
        # Create formatted DataFrame for display
        display_df = create_display_dataframe(results)
        
        st.success(f"{len(results)} result(s) found. Tick the paper you want to download and click \"Download\" button.")
        
        # Download button appears only when results are found
        download_clicked = st.button("Download", key="download_results")
        
        # Display DataFrame and capture selections
        edited_df = st.data_editor(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=int((len(display_df.reset_index(drop=True))+1) * 35),
            column_config=get_data_editor_config(),
            key="papers_selection"
        )
        
        # Handle download action
        if download_clicked:
            selected_indices = edited_df[edited_df['Select']].index.tolist()
            if selected_indices:
                if not username or not password:
                    st.toast("Please enter your TARUMT login credentials to download papers.")
                else:
                    process_downloads(selected_indices, results, username, password)
            else:
                st.toast("Please select at least one paper to download.")

    elif st.session_state.has_searched and not st.session_state.clear_on_next_run:
        st.warning("No results found.")

if __name__ == "__main__":
    main()
    print('Reloaded! All good!')