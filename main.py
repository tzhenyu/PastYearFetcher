import streamlit as st
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth
import hashlib
import pandas as pd
import base64

st.set_page_config(page_title="Past Year Fetcher", page_icon="📃")

# Constants
FACULTIES = [
    "Faculty of Accountancy, Finance and Business",
    "Faculty of Applied Sciences",
    "Faculty of Computing and Information Technology",
    "Faculty of Built Environment",
    "Faculty of Engineering and Technology",
    "Faculty of Communication and Creative Industries",
    "Faculty of Social Science and Humanities",
    "Centre for Pre-University Studies"
]

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




def create_error_message(paper_title, error_type):
    """Create standardized error messages for PDF download failures."""
    error_messages = {
        'unauthorized': f"Invalid credentials",
        'not_found': f"PDF not found for {paper_title}",
        'access_failed': f"Failed to access {paper_title}",
        'download_failed': f"Download failed for {paper_title}"
    }
    return error_messages.get(error_type, f"Unknown error for {paper_title}")


def generate_download_script(b64_content, safe_filename, delay_ms):
    """Generate JavaScript for automatic PDF download."""
    return f"""
    <script>
    // Hide this iframe immediately
    if (window.frameElement) {{
        window.frameElement.style.cssText = 'position:absolute!important;left:-9999px!important;width:1px!important;height:1px!important;opacity:0!important;pointer-events:none!important;border:none!important;';
        if (window.frameElement.parentElement) {{
            window.frameElement.parentElement.style.cssText = 'position:absolute!important;left:-9999px!important;width:1px!important;height:1px!important;opacity:0!important;pointer-events:none!important;';
        }}
    }}
    
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
            
            // Try to hide parent iframe after download
            setTimeout(() => {{
                try {{
                    if (window.parent && window.parent.document) {{
                        const iframes = window.parent.document.querySelectorAll('div[data-testid="stIFrame"]');
                        iframes.forEach(container => {{
                            container.style.cssText = 'position:absolute!important;left:-9999px!important;width:1px!important;height:1px!important;opacity:0!important;pointer-events:none!important;';
                        }});
                    }}
                }} catch(e) {{
                    // Ignore cross-origin errors
                }}
            }}, 200);
            
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
                div[data-testid="stVerticalBlockBorderWrapper"] button {
                    font-size: 12px !important;
                    width: 100% !important;
                    min-height: 32px !important;
                    box-sizing: border-box !important;
                }

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
            
            /* Mobile toast styling */
            @media (max-width: 740px) {
                [data-testid=stToastContainer] [data-testid=stMarkdownContainer] > p {
                    font-size: 1rem !important;
                    padding: 8px 12px !important;
                }
            }
            
            /* Center download buttons in container */
            div[data-testid="stVerticalBlockBorderWrapper"] .stColumn:last-child div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlock"] {
                display: flex !important;
                flex-direction: column !important;
                justify-content: center !important;
                min-height: 60px !important;
            }
            
            /* Prevent button state changes - target the correct button */
            div[data-testid="stVerticalBlockBorderWrapper"] button[data-testid="stBaseButton-secondary"] {
                background-color: #ffffff !important;
                border: 1px solid #d3d3d3 !important;
                color: #262730 !important;
                transition: none !important;
                transform: none !important;
                position: relative !important;
            }
            
            div[data-testid="stVerticalBlockBorderWrapper"] button[data-testid="stBaseButton-secondary"]:hover {
                background-color: #f8f9fa !important;
                border-color: #d3d3d3 !important;
                color: #262730 !important;
                transform: none !important;
            }
            
            div[data-testid="stVerticalBlockBorderWrapper"] button[data-testid="stBaseButton-secondary"]:active,
            div[data-testid="stVerticalBlockBorderWrapper"] button[data-testid="stBaseButton-secondary"]:focus {
                background-color: #ffffff !important;
                border-color: #d3d3d3 !important;
                color: #262730 !important;
                box-shadow: none !important;
                outline: none !important;
                transform: none !important;
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


def create_display_dataframe(results):
    """Create and format DataFrame for display."""
    df = pd.DataFrame(results)
    df['faculties_str'] = df['faculties'].apply(lambda x: ', '.join([FACULTY_ABBR.get(f, f) for f in x]))
    
    # Reorder and rename columns for display
    display_df = df[['year', 'month', 'faculties_str']].copy()
    display_df.columns = ['Year', 'Month', 'Faculties']
    return display_df


def process_single_download(paper, username, password):
    """Process PDF download for a single paper."""
    success, content, filename = handle_pdf_actions(paper, username, password)

    if success:
        # Use Streamlit's native download button for proper browser download behavior
        st.download_button(
            label="📥 Download PDF",
            data=content,
            file_name=filename,
            mime="application/pdf",
            key=f"download_{hashlib.md5(paper['link'].encode()).hexdigest()}"
        )
        st.toast(f"✅ PDF ready for download!")
    else:
        st.toast(f"❌ Failed: {filename}")



def search_paper(past_year_title, selected_faculty):
    query = past_year_title.replace(" ", "+")
    rss_url = f"https://eprints.tarc.edu.my/cgi/search/archive/advanced/export_eprints_RSS2.xml?screen=Search&dataset=archive&_action_export=1&output=RSS2&exp=0%7C1%7C-date%2Fcreators_name%2Ftitle%7Carchive%7C-%7Ctitle%3Atitle%3AALL%3AIN%3A{query}%7Ctype%3Atype%3AANY%3AEQ%3Ateaching_resource%7C-%7Ceprint_status%3Aeprint_status%3AANY%3AEQ%3Aarchive%7Cmetadata_visibility%3Ametadata_visibility%3AANY%3AEQ%3Ashow&n="
    response = requests.get(rss_url)
    if response.status_code != 200:
        return []
    xml_content = response.text
    root = ET.fromstring(xml_content)
    results = []
    for child in root.findall(".//channel/item"):
        try:
            title = child.find("title").text.strip().split(" (")[0]            
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
                        month = paper['month'].replace(" ", "")
                        filename = f"{paper['title']}_{paper['year']}_{month}.pdf"
                        filename = filename.replace(" ", "_")
                        
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
    st.markdown("You can check the source code [here](https://github.com/tzhenyu/PastYearFetcher/blob/main/pastyearfetcher.py).")
    st.markdown("Made by [tzhenyu](https://github.com/tzhenyu)")
   

def main():
    if "dialog_shown" not in st.session_state:
        disclaimer_dialog()
        st.session_state.dialog_shown = True
    
    st.title("📃 TAR UMT Past Years Fetcher")
    st.markdown("[Any feedback is welcome!](https://forms.gle/dSaszkRzZ6reoFc88)")
    
    # Apply custom CSS styles
    st.markdown("""
        <style>
            /* Hide empty element containers that appear after download */
            .stElementContainer:empty,
            div[data-testid="stElementContainer"]:empty {
                display: none !important;
            }
            
            /* Hide st.components.v1.html containers */
            iframe[src^="data:text/html"] {
                position: absolute !important;
                left: -9999px !important;
                width: 1px !important;
                height: 1px !important;
                opacity: 0 !important;
                pointer-events: none !important;
                border: none !important;
                visibility: hidden !important;
            }
            
            div[data-testid="stIFrame"] {
                position: absolute !important;
                left: -9999px !important;
                width: 1px !important;
                height: 1px !important;
                opacity: 0 !important;
                pointer-events: none !important;
                visibility: hidden !important;
                overflow: hidden !important;
            }
            
            /* Additional hiding for iframe containers */
            div[data-testid="stIFrame"]:has(iframe[src^="data:text/html"]) {
                display: none !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # Initialize session state variables
    initialize_session_state()
    username, password = st.session_state.username, st.session_state.password

    if st.session_state.clear_on_next_run:
        clear_session_data()

    col1, col2 = st.columns([4,1])
    with col1:
        past_year_title = st.text_input("Search course", placeholder="e.g. BACS1013 or Problem Solving", key="past_year_title", on_change=lambda: setattr(st.session_state, 'search_triggered', True))
    with col2:
        selected_faculty = st.selectbox(
            "Filter by Faculty",
            ["All"] + list(FACULTY_ABBR.values()),
            key="selected_faculty",
            on_change=lambda: setattr(st.session_state, 'faculty_changed', True)
        )

    # Check if search should be triggered by Enter key or faculty change
    if (hasattr(st.session_state, 'search_triggered') and st.session_state.search_triggered) or \
       (hasattr(st.session_state, 'faculty_changed') and st.session_state.faculty_changed):
        if past_year_title != st.session_state.get('last_search_query', '') or selected_faculty != st.session_state.get('last_faculty_filter', ''):
            st.session_state.has_searched = True
            if past_year_title:
                faculty_filter = "All" if selected_faculty == "All" else next(
                    (k for k, v in FACULTY_ABBR.items() if v == selected_faculty), "All"
                )
                st.session_state.search_results = search_paper(past_year_title, faculty_filter)
                if st.session_state.search_results:
                    st.toast(f"{len(st.session_state.search_results)} result(s) found.")
            else:
                st.session_state.search_results = []
            st.session_state.last_search_query = past_year_title
            st.session_state.last_faculty_filter = selected_faculty
        st.session_state.search_triggered = False
        if hasattr(st.session_state, 'faculty_changed'):
            st.session_state.faculty_changed = False

    col_login, col_search, col_clear, col_empty = st.columns([3, 3, 3, 12])
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

    if search_clicked:
        st.session_state.has_searched = True
        if past_year_title:
            faculty_filter = "All" if selected_faculty == "All" else next(
                (k for k, v in FACULTY_ABBR.items() if v == selected_faculty), "All"
            )
            st.session_state.search_results = search_paper(past_year_title, faculty_filter)
            if st.session_state.search_results:
                st.toast(f"{len(st.session_state.search_results)} result(s) found.")
        else:
            st.session_state.search_results = []
    if clear_clicked:
        st.session_state.clear_on_next_run = True
        st.session_state.has_searched = False

    results = st.session_state.search_results

    # --- Results Display ---
    if results and not st.session_state.clear_on_next_run:
        # Create formatted DataFrame for display
        display_df = create_display_dataframe(results)
        
        # Display papers with individual download buttons
        for idx, (_, row) in enumerate(display_df.iterrows()):
            paper = results[idx]
            
            with st.container(border=True):
                col1, col2 = st.columns([5.5, 1])
                
                with col1:
                    st.markdown(f"<b>{paper['title']}</b> ", unsafe_allow_html=True)
                    st.markdown(f"{row['Year']} · {row['Month']} · {row['Faculties']}", unsafe_allow_html=True)
                
                with col2:
                    download_key = f"download_{idx}"
                    paper_key = f"pdf_{hashlib.md5(paper['link'].encode()).hexdigest()}"

                    # Check if PDF is already cached and ready for download
                    if paper_key in st.session_state and st.session_state[paper_key].get('status') == 'success':
                        # Show download button for cached PDF
                        cached_data = st.session_state[paper_key]
                        st.download_button(
                            label="📥 Download",
                            data=cached_data['content'],
                            file_name=cached_data['filename'],
                            mime="application/pdf",
                            key=f"download_btn_{idx}"
                        )
                    else:
                        # Show fetch button
                        if st.button("Fetch", key=download_key):
                            if not username or not password:
                                st.toast("Please enter your TARUMT login credentials to download papers.")
                            else:
                                process_single_download(paper, username, password)

    elif st.session_state.has_searched and not st.session_state.clear_on_next_run:
        st.warning("No results found.")

if __name__ == "__main__":
    main()
    print('Reloaded! All good!')


