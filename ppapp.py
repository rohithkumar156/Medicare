import streamlit as st
import pandas as pd
import os
import requests
import json
from datetime import datetime
import base64
from urllib.parse import urlencode
import time

import pandas as pd
import os

DATA_FILE = "patients_data.csv"

def auto_fix_csv():
    required_columns = [
        "Name", "Age", "Gender", "Contact",
        "Blood Type", "Allergies", "Medical History",
        "FHIR_Patient_ID", "Last_Sync", "Source"
    ]

    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)

        # Add any missing columns with empty values
        for col in required_columns:
            if col not in df.columns:
                df[col] = ""

        # Reorder columns
        df = df[required_columns]

        # Save back the fixed file
        df.to_csv(DATA_FILE, index=False)
        print("✅ CSV file fixed successfully.")
    else:
        # Create a new file if it doesn't exist
        df = pd.DataFrame(columns=required_columns)
        df.to_csv(DATA_FILE, index=False)
        print("✅ New CSV file created.")

# Call this once when app starts
auto_fix_csv()


###########################
# File to store patient data
DATA_FILE = "patients_data.csv"

# FHIR Configuration (Using public test server)
FHIR_CONFIG = {
    "base_url": "https://hapi.fhir.org/baseR4/",
    "auth_url": "",  # No auth needed
    "token_url": "",  # No auth needed
    "client_id": "",
    "client_secret": "",
    "redirect_uri": "",
    "scope": "",
    "environment": "test",
    "fhir_version": "R4",
    "smart_version": "v1",
    "is_confidential": False,
    "uses_cds_hooks": False,
    "dynamic_registration": False
}

# Initialize the CSV file if it doesn't exist
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=[
        "Name", "Age", "Gender", "Contact", 
        "Blood Type", "Allergies", "Medical History",
        "FHIR_Patient_ID", "Last_Sync", "Source"
    ])
    df.to_csv(DATA_FILE, index=False)

def load_data():
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

class FHIRClient:
    def __init__(self, config):
        self.config = config
    
    def search_patients(self, search_params=None):
        url = f"{self.config['base_url']}Patient"
        
        try:
            response = requests.get(url, params=search_params)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            st.error(f"Error searching patients: {str(e)}")
            return None
    
    def get_patient_details(self, patient_id):
        url = f"{self.config['base_url']}Patient/{patient_id}"
        
        try:
            response = requests.get(url)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            st.error(f"Error getting patient details: {str(e)}")
            return None
    
    def get_patient_observations(self, patient_id):
        url = f"{self.config['base_url']}Observation"
        params = {'patient': patient_id}
        
        try:
            response = requests.get(url, params=params)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            st.error(f"Error getting observations: {str(e)}")
            return None

def parse_fhir_patient_data(fhir_patient):
    try:
        name = ""
        if 'name' in fhir_patient and fhir_patient['name']:
            name_obj = fhir_patient['name'][0]
            given = name_obj.get('given', [])
            family = name_obj.get('family', '')
            name = f"{' '.join(given)} {family}".strip()
        
        age = ""
        if 'birthDate' in fhir_patient:
            birth_date = datetime.strptime(fhir_patient['birthDate'], '%Y-%m-%d')
            age = datetime.now().year - birth_date.year
        
        gender = fhir_patient.get('gender', '').capitalize()
        contact = ""
        
        if 'telecom' in fhir_patient:
            for telecom in fhir_patient['telecom']:
                if telecom.get('system') == 'phone':
                    contact = telecom.get('value', '')
                    break
        
        return {
            'Name': name,
            'Age': age,
            'Gender': gender,
            'Contact': contact,
            'Blood Type': '',
            'Allergies': '',
            'Medical History': '',
            'FHIR_Patient_ID': fhir_patient.get('id', ''),
            'Last_Sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Source': 'FHIR Server'
        }
    except Exception as e:
        st.error(f"Error parsing FHIR patient data: {str(e)}")
        return None

# Initialize FHIR client
fhir_client = FHIRClient(FHIR_CONFIG)

# Streamlit App
st.set_page_config(page_title="Patient Health Records", layout="wide")
st.title("🏥 Patient Health Records - FHIR Integration with Demo")

# Configuration section
def show_configuration():
    with st.expander("⚙️ FHIR Server Configuration", expanded=False):
        st.markdown("""
        **Using public test FHIR server:**  
        🔹 No authentication required  
        🔹 Data is read-only  
        🔹 For demonstration purposes only  
        """)
        
        st.info("This demo uses a public test FHIR server at https://hapi.fhir.org/")

# Patient Management
def add_patient():
    st.subheader("Add New Patient Record")
    with st.form("patient_form"):
        name = st.text_input("Full Name*")
        age = st.number_input("Age*", min_value=0, max_value=120)
        gender = st.selectbox("Gender*", ["Male", "Female", "Other"])
        contact = st.text_input("Contact Number*")
        blood_type = st.selectbox("Blood Type", ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"])
        allergies = st.text_input("Allergies (if any)")
        medical_history = st.text_area("Medical History")
        fhir_patient_id = st.text_input("FHIR Patient ID (if known)")
        
        if st.form_submit_button("Save Patient"):
            if not name or not age or not gender or not contact:
                st.error("Please fill required fields (*)!")
            else:
                df = load_data()
                new_patient = pd.DataFrame([{
                    "Name": name, "Age": age, "Gender": gender,
                    "Contact": contact, "Blood Type": blood_type,
                    "Allergies": allergies, "Medical History": medical_history,
                    "FHIR_Patient_ID": fhir_patient_id,
                    "Last_Sync": datetime.now().strftime('%Y-%m-%d %H:%M:%S') if fhir_patient_id else "",
                    "Source": "Manual Entry"
                }])
                df = pd.concat([df, new_patient], ignore_index=True)
                save_data(df)
                st.success("Patient record saved!")
                st.rerun()

def view_patients():
    st.subheader("View Patient Records")
    df = load_data()
    
    # Add filters
    col1, col2, col3 = st.columns(3)
    with col1:
        search_name = st.text_input("Search by Name")
    with col2:
        filter_source = st.selectbox("Filter by Source", ["All", "Manual Entry", "Hospital Integration", "FHIR Server"])
    with col3:
        filter_gender = st.selectbox("Filter by Gender", ["All", "Male", "Female", "Other"])
    
    # Apply filters
    filtered_df = df.copy()
    
    if search_name:
        filtered_df = filtered_df[filtered_df["Name"].str.contains(search_name, case=False, na=False)]
    
    if filter_source != "All":
        filtered_df = filtered_df[filtered_df["Source"] == filter_source]
    
    if filter_gender != "All":
        filtered_df = filtered_df[filtered_df["Gender"] == filter_gender]
    
    # Display stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Patients", len(df))
    with col2:
        st.metric("Manual Entry", len(df[df["Source"] == "Manual Entry"]))
    with col3:
        st.metric("Hospital Integration", len(df[df["Source"] == "Hospital Integration"]))
    with col4:
        st.metric("FHIR Server", len(df[df["Source"] == "FHIR Server"]))
    
    st.dataframe(filtered_df, use_container_width=True)
    
    st.download_button(
        label="Download Data as CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="patients_data.csv",
        mime="text/csv"
    )

def fhir_patient_search():
    st.subheader("🔍 Search FHIR Server Patients")
    
    search_term = st.text_input("Search by Name or ID")
    if st.button("Search FHIR Server") and search_term:
        with st.spinner("Searching FHIR server..."):
            results = fhir_client.search_patients({'name': search_term})
            
            if results and 'entry' in results:
                st.success(f"Found {len(results['entry'])} patients")
                for entry in results['entry']:
                    patient = entry['resource']
                    parsed_data = parse_fhir_patient_data(patient)
                    
                    if parsed_data:
                        with st.expander(f"Patient: {parsed_data['Name']}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Age:** {parsed_data['Age']}")
                                st.write(f"**Gender:** {parsed_data['Gender']}")
                                st.write(f"**Contact:** {parsed_data['Contact']}")
                            with col2:
                                st.write(f"**FHIR ID:** {parsed_data['FHIR_Patient_ID']}")
                            
                            if st.button(f"Import Patient", key=f"import_{parsed_data['FHIR_Patient_ID']}"):
                                df = load_data()
                                new_patient = pd.DataFrame([parsed_data])
                                df = pd.concat([df, new_patient], ignore_index=True)
                                save_data(df)
                                st.success("Patient imported!")
                                st.rerun()
            else:
                st.info("No patients found")

def sync_with_fhir():
    st.subheader("🔄 Sync with FHIR Server")
    
    df = load_data()
    fhir_patients = df[df['FHIR_Patient_ID'].notna() & (df['FHIR_Patient_ID'] != '')]
    
    if fhir_patients.empty:
        st.info("No patients with FHIR IDs found")
    else:
        st.write(f"Found {len(fhir_patients)} patients with FHIR IDs")
        
        for idx, patient in fhir_patients.iterrows():
            with st.expander(f"Sync: {patient['Name']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Last Sync:** {patient['Last_Sync']}")
                    st.write(f"**FHIR ID:** {patient['FHIR_Patient_ID']}")
                
                with col2:
                    if st.button(f"Sync Now", key=f"sync_{idx}"):
                        with st.spinner("Syncing..."):
                            fhir_data = fhir_client.get_patient_details(patient['FHIR_Patient_ID'])
                            if fhir_data:
                                updated_data = parse_fhir_patient_data(fhir_data)
                                if updated_data:
                                    for key, value in updated_data.items():
                                        if key != 'FHIR_Patient_ID':
                                            df.at[idx, key] = value
                                    save_data(df)
                                    st.success("Synced!")
                                    st.rerun()

# Hospital Integration Demo Functions
def hospital_file_integration():
    st.subheader("📄 Hospital File Integration Demo")
    
    st.markdown("""
    **How it works:**
    1. Hospital exports their patient data to CSV file
    2. Hospital uploads file to our system
    3. We import all patients automatically
    4. No manual data entry required!
    """)
    
    # Sample data format
    with st.expander("📋 Required File Format"):
        sample_data = pd.DataFrame([
            {"Name": "John Hospital", "Age": 45, "Gender": "Male", "Contact": "555-1111", "BloodType": "O+", "Allergies": "None", "MedicalHistory": "Diabetes"},
            {"Name": "Mary Medical", "Age": 32, "Gender": "Female", "Contact": "555-2222", "BloodType": "A+", "Allergies": "Penicillin", "MedicalHistory": "Hypertension"},
            {"Name": "Bob Clinic", "Age": 28, "Gender": "Male", "Contact": "555-3333", "BloodType": "B-", "Allergies": "None", "MedicalHistory": "Healthy"}
        ])
        st.dataframe(sample_data)
        
        # Download sample file
        csv_sample = sample_data.to_csv(index=False)
        st.download_button(
            label="📥 Download Sample File",
            data=csv_sample,
            file_name="hospital_sample.csv",
            mime="text/csv"
        )
    
    # File upload
    uploaded_file = st.file_uploader("🏥 Upload Hospital Patient File", type=['csv'])
    
    if uploaded_file:
        try:
            hospital_data = pd.read_csv(uploaded_file)
            st.success(f"✅ File loaded successfully! Found {len(hospital_data)} patients")
            
            st.write("**Preview of Hospital Data:**")
            st.dataframe(hospital_data)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 Import All Patients", type="primary"):
                    with st.spinner("Importing patients..."):
                        df = load_data()
                        imported_count = 0
                        
                        for _, row in hospital_data.iterrows():
                            new_patient = pd.DataFrame([{
                                "Name": row.get('Name', ''),
                                "Age": row.get('Age', 0),
                                "Gender": row.get('Gender', ''),
                                "Contact": row.get('Contact', ''),
                                "Blood Type": row.get('BloodType', ''),
                                "Allergies": row.get('Allergies', ''),
                                "Medical History": row.get('MedicalHistory', ''),
                                "FHIR_Patient_ID": "",
                                "Last_Sync": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                "Source": "Hospital Integration"
                            }])
                            df = pd.concat([df, new_patient], ignore_index=True)
                            imported_count += 1
                        
                        save_data(df)
                        st.success(f"🎉 Successfully imported {imported_count} patients from hospital!")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
            
            with col2:
                if st.button("❌ Cancel Import"):
                    st.info("Import cancelled")
                    
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
            st.info("Please make sure your CSV file has the correct format")

def api_integration_demo():
    st.subheader("🔗 API Integration Demo")
    
    st.markdown("""
    **How it works:**
    1. Hospital system sends patient data via API
    2. Our system receives and processes the data
    3. Patient automatically appears in our database
    4. Real-time integration!
    """)
    
    # Simulate API data
    api_demo_data = {
        "patient_id": f"HOSP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "name": "API Demo Patient",
        "age": 35,
        "gender": "Female",
        "contact": "555-API-DEMO",
        "blood_type": "AB+",
        "allergies": "Shellfish",
        "medical_history": "Annual checkup",
        "hospital": "Demo City Hospital",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    st.write("**Sample API Request from Hospital:**")
    st.code(f"""
POST /api/patients
Content-Type: application/json

{json.dumps(api_demo_data, indent=2)}
    """, language="json")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎯 Simulate API Call", type="primary"):
            with st.spinner("Processing API request..."):
                time.sleep(2)  # Simulate processing
                
                # Add to database
                df = load_data()
                new_patient = pd.DataFrame([{
                    "Name": api_demo_data['name'],
                    "Age": api_demo_data['age'],
                    "Gender": api_demo_data['gender'],
                    "Contact": api_demo_data['contact'],
                    "Blood Type": api_demo_data['blood_type'],
                    "Allergies": api_demo_data['allergies'],
                    "Medical History": api_demo_data['medical_history'],
                    "FHIR_Patient_ID": api_demo_data['patient_id'],
                    "Last_Sync": api_demo_data['timestamp'],
                    "Source": "Hospital Integration"
                }])
                
                df = pd.concat([df, new_patient], ignore_index=True)
                save_data(df)
                
                st.success("✅ API request processed successfully!")
                st.json({"status": "success", "message": "Patient created", "patient_id": api_demo_data['patient_id']})
                st.balloons()
    
    with col2:
        if st.button("📊 View Integration Stats"):
            df = load_data()
            hospital_patients = df[df["Source"] == "Hospital Integration"]
            
            st.metric("Hospital Integrated Patients", len(hospital_patients))
            st.metric("Total API Calls", len(hospital_patients))
            
            if len(hospital_patients) > 0:
                st.write("**Recent Hospital Integrations:**")
                st.dataframe(hospital_patients.tail(5)[["Name", "Last_Sync", "Source"]])

def webhook_demo():
    st.subheader("📡 Webhook Integration Demo")
    
    st.markdown("""
    **How it works:**
    1. Hospital updates patient in their system
    2. Hospital system sends webhook notification to us
    3. We receive notification and fetch updated data
    4. Patient record automatically updated!
    """)
    
    # Webhook simulation
    webhook_data = {
        "event": "patient_updated",
        "patient_id": "HOSP-WEBHOOK-001",
        "hospital": "Demo Medical Center",
        "event_type": "update",
        "timestamp": datetime.now().isoformat(),
        "changes": ["contact", "medical_history"]
    }
    
    st.write("**Webhook Notification Received:**")
    st.json(webhook_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Process Webhook", type="primary"):
            with st.spinner("Processing webhook notification..."):
                time.sleep(1)
                st.info("🔍 Fetching updated patient data from hospital...")
                time.sleep(2)
                
                # Simulate updated patient data
                updated_patient = {
                    "Name": "Webhook Demo Patient",
                    "Age": 42,
                    "Gender": "Male",
                    "Contact": "555-WEBHOOK-NEW",  # Updated
                    "Blood Type": "O-",
                    "Allergies": "None",
                    "Medical History": "Updated: Recent surgery completed successfully",  # Updated
                    "FHIR_Patient_ID": webhook_data['patient_id'],
                    "Last_Sync": webhook_data['timestamp'],
                    "Source": "Hospital Integration"
                }
                
                # Check if patient exists, update or create
                df = load_data()
                existing_patient = df[df['FHIR_Patient_ID'] == webhook_data['patient_id']]
                
                if len(existing_patient) > 0:
                    # Update existing
                    idx = existing_patient.index[0]
                    for key, value in updated_patient.items():
                        df.at[idx, key] = value
                    action = "updated"
                else:
                    # Create new
                    new_patient = pd.DataFrame([updated_patient])
                    df = pd.concat([df, new_patient], ignore_index=True)
                    action = "created"
                
                save_data(df)
                
                st.success(f"✅ Patient record {action} via webhook!")
                st.write("**Updated Patient Data:**")
                st.json(updated_patient)
    
    with col2:
        if st.button("📈 Webhook Logs"):
            st.write("**Recent Webhook Events:**")
            webhook_logs = [
                {"timestamp": "2024-01-15 10:30:00", "event": "patient_created", "status": "success"},
                {"timestamp": "2024-01-15 11:45:00", "event": "patient_updated", "status": "success"},
                {"timestamp": "2024-01-15 14:20:00", "event": "patient_deleted", "status": "success"},
                {"timestamp": "2024-01-15 16:10:00", "event": "patient_updated", "status": "pending"}
            ]
            
            log_df = pd.DataFrame(webhook_logs)
            st.dataframe(log_df)

def hospital_integration_demo():
    st.subheader("🏥 Hospital Integration Demo Center")
    
    # Integration overview
    with st.expander("📋 Integration Overview", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Integration Methods", "3")
            st.write("• File Upload")
            st.write("• API Integration") 
            st.write("• Webhook Notifications")
        
        with col2:
            df = load_data()
            hospital_count = len(df[df["Source"] == "Hospital Integration"])
            st.metric("Integrated Patients", hospital_count)
        
        with col3:
            st.metric("Demo Status", "Active")
            st.success("✅ All systems operational")
    
    # Choose integration type
    integration_type = st.selectbox(
        "Choose Integration Demo Type:",
        ["📄 File Upload Integration", "🔗 API Integration", "📡 Webhook Integration"]
    )
    
    st.markdown("---")
    
    if integration_type == "📄 File Upload Integration":
        hospital_file_integration()
    elif integration_type == "🔗 API Integration":
        api_integration_demo()
    elif integration_type == "📡 Webhook Integration":
        webhook_demo()

# Sidebar menu
menu = st.sidebar.selectbox("Menu", [
    "Add Patient", 
    "View Patients", 
    "FHIR Patient Search",
    "Sync with FHIR",
    "🔗 Hospital Integration Demo"
])

# Main app logic
show_configuration()

if menu == "Add Patient":
    add_patient()
elif menu == "View Patients":
    view_patients()
elif menu == "FHIR Patient Search":
    fhir_patient_search()
elif menu == "Sync with FHIR":
    sync_with_fhir()
elif menu == "🔗 Hospital Integration Demo":
    hospital_integration_demo()

# Status indicator
st.sidebar.markdown("---")
st.sidebar.success("✅ Connected to public FHIR server")
st.sidebar.info("🔗 Integration demos active")

# Demo instructions
with st.sidebar.expander("📖 Demo Instructions"):
    st.markdown("""
    **Hospital Integration Demo:**
    1. Go to Integration Demo section
    2. Try different integration types
    3. Upload sample files or simulate API calls
    4. View integrated patients in "View Patients"
    
    **For Presentations:**
    - Show current patients first
    - Demonstrate integration process
    - Show new patients after integration
    """)

# ROI Calculator
with st.sidebar.expander("💰 ROI Calculator"):
    st.write("**Integration Benefits:**")
    patients = st.number_input("Hospital patients", 100, 10000, 1000)
    time_per_patient = st.slider("Minutes saved per patient", 1, 10, 5)
    hourly_rate = st.number_input("Staff hourly rate ($)", 20, 100, 30)
    
    monthly_savings = (patients * time_per_patient * hourly_rate) / 60
    st.metric("Monthly Savings", f"${monthly_savings:,.0f}")
    st.metric("Annual Savings", f"${monthly_savings * 12:,.0f}")