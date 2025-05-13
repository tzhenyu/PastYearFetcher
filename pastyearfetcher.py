import streamlit
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth

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
    past_year_title.replace(" ", "+")
    rss_url = f"https://eprints.tarc.edu.my/cgi/search/simple/export_eprints_RSS2.xml?screen=Search&dataset=archive&_action_export=1&output=RSS2&exp=0%7C1%7C-date%2Fcreators_name%2Ftitle%7Carchive%7C-%7Cq%3Aabstract%2Fcreators_name%2Fdate%2Fdocuments%2Ftitle%3AALL%3AIN%3A{past_year_title}%7C-%7Ceprint_status%3Aeprint_status%3AANY%3AEQ%3Aarchive%7Cmetadata_visibility%3Ametadata_visibility%3AANY%3AEQ%3Ashow&n="
    response = requests.get(rss_url)

    # Online fetching of XML content
    if response.status_code == 200:
        xml_content = response.text 
    else:
        print(f"Failed to fetch RSS feed: {response.status_code}")
    root = ET.fromstring(xml_content)
    results = []

    ## Offline fetching of XML content
    # with open("rss.xml", "r") as file:
    #     root = ET.fromstring(file.read())
    #     results = []

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

            
        except IndexError:
            continue
    return results

def main():
    streamlit.title("TAR UMT's Past Years Fetcher")
    streamlit.markdown("Made by [@tzhenyu](https://github.com/tzhenyu)")
    streamlit.markdown("This project does not store any of your credentials. You may check the source code [here]()")
    streamlit.markdown("This is a personal project and is not affiliated with TAR UMT in any way. Use at your own risk.")
    
    if "clear_on_next_run" in streamlit.session_state and streamlit.session_state.clear_on_next_run:
        streamlit.session_state.past_year_title = ""
        streamlit.session_state.selected_faculty = "All"
        streamlit.session_state.search_results = []
        streamlit.session_state.clear_on_next_run = False

    if "past_year_title" not in streamlit.session_state:
        streamlit.session_state.past_year_title = ""
    if "selected_faculty" not in streamlit.session_state:
        streamlit.session_state.selected_faculty = "All"

    faculty_options = ["All"] + faculties

    with streamlit.expander("Please put your TAR UMT credentials to download the PDF files.", expanded=True):
        username_input = streamlit.text_input("Username", key="eprints_username")
        password_input = streamlit.text_input("Password", type="password", key="eprints_password")
        submit_cred = streamlit.button("Submit Credentials")

    # Store credentials only when submit is clicked
    if "username" not in streamlit.session_state:
        streamlit.session_state.username = ""
    if "password" not in streamlit.session_state:
        streamlit.session_state.password = ""

    if submit_cred:
        streamlit.session_state.username = username_input
        streamlit.write("Please enter a title to search.")
        streamlit.session_state.password = password_input
        streamlit.success("Credentials saved!")

    # Use these variables for authentication
    username = streamlit.session_state.username
    password = streamlit.session_state.password

    past_year_title = streamlit.text_input(
        "Course Code e.g. BACS1013",
        key="past_year_title"
    )
    selected_faculty = streamlit.selectbox(
        "Filter by Faculty",
        faculty_options,
        key="selected_faculty"
    )

    if "search_results" not in streamlit.session_state:
        streamlit.session_state.search_results = []


    col_search, col_clear, col_empty = streamlit.columns([1, 1,6])
    with col_search:
        search_clicked = streamlit.button("Search")
    with col_clear:
        clear_clicked = streamlit.button("Clear")

    # Only update results when Search is clicked
    if search_clicked:
        if past_year_title:
            streamlit.session_state.search_results = search_paper(past_year_title, selected_faculty)
        else:
            streamlit.session_state.search_results = []

    # Clear results when Clear is clicked
    if clear_clicked:
        streamlit.session_state.clear_on_next_run = True
        streamlit.rerun()


    results = streamlit.session_state.search_results

    if results:
        streamlit.write(f"{len(results)} result(s) found!")
        for idx, paper in enumerate(results):
            col1, col2, col3, col4 = streamlit.columns([1, 2, 1, 2])
            with col1:
                streamlit.write(f"{paper['year']}")
            with col2:
                streamlit.write(f"{paper['month']}")
            with col3:
                abbrs = [faculty_abbr.get(f, f) for f in paper['faculties']]
                streamlit.write(f"{', '.join(abbrs)}") 
            with col4:

                # streamlit.write(f"{link}") 
                response = requests.get(paper['link'])
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    meta_tags = soup.find_all("meta", attrs={"name": "eprints.document_url"})

                    for i, tag in enumerate(meta_tags):
                        if tag.has_attr("content"):
                            pdf_url = tag['content'] + "?download=1"
                            pdf_response = requests.get(pdf_url, auth=HTTPBasicAuth(username, password))

                            if pdf_response.status_code == 200:
                                streamlit.download_button(
                                    label=f"📥 Download PDF",
                                    data=pdf_response.content,
                                    file_name=f"{paper['year']}{paper['month']}.pdf",
                                    mime="application/pdf",
                                    key=f"download_{pdf_url}"
                                )
                            elif pdf_response.status_code == 401:
                                streamlit.warning(f"⚠ Invalid credentials.")
                        
                else:
                    print(f"Failed to fetch page: {response.status_code}")


    elif "search_results" in streamlit.session_state and not results and past_year_title:
        streamlit.write("No results found. It's likely that the paper is not available in the system.")

if __name__ == "__main__":
    main()
    # Uncomment the line below to run the search_paper function directly