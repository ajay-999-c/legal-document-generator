# Google Forms and Google Sheets specification

**Regenerated:** 23 September 2026  
**Source of truth for Required/Optional state:** the currently configured Google Forms exported as PDFs.

This specification replaces earlier requiredness assumptions. The red `*` shown in the live Form is treated as authoritative for the current business workflow.

## Final document registry

| Document | Backend key | Google Form title | Worksheet |
| --- | --- | --- | --- |
| NOC | `noc` | NOC Document Details Form | `NOC Responses` |
| Affidavit | `affidavit` | Affidavit Details Form / शपथ पत्र विवरण फॉर्म | `Affidavit Responses` |
| Consent Letter | `consent` | Consent Letter Details Form / सहमति पत्र विवरण फॉर्म | `Consent Responses` |

## Requiredness summary

| Form | Questions | Required | Optional |
| --- | ---: | ---: | ---: |
| NOC | 14 | 12 | 2 |
| Affidavit | 17 | 16 | 1 |
| Consent Letter | 24 | 23 | 1 |
| **Total** | **55** | **51** | **4** |

### Global rules

- `Timestamp` is Google Forms metadata, not a document field.
- Every worksheet must have these four internal columns at the far right:
  - `processing_status`
  - `generated_file`
  - `processed_at`
  - `error_message`
- These four columns are **not** Google Form questions.
- Requiredness in backend validation should match this specification when the combined desktop application is implemented.
- Document Date is optional in all three Forms.
- Backend document keys are `noc`, `affidavit`, and `consent`.
- Use one Google Spreadsheet with three separate response worksheets.
- Do not merge response rows across document types.

---

# NOC Form

## Form identity

**Title:** NOC Document Details Form

**Description:**  
Please fill in the following details carefully for generating the NOC document.  
कृपया NOC दस्तावेज़ तैयार करने हेतु नीचे दी गई जानकारी सही-सही भरें।

## Questions

| # | English Name | Hindi Name | Exact Google Form Question | Form Type | Required? | Backend Parameter | Word Placeholder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Association / Society Name | एसोसिएशन / संस्था का नाम | Association / Society Name / एसोसिएशन / संस्था का नाम | Short answer | Yes — Required | `association_name` | `{{association_name}}` |
| 2 | Association Location / Address | एसोसिएशन का स्थान / पता | Association Location / Address / एसोसिएशन का स्थान / पता | Paragraph | Yes — Required | `association_location` | `{{association_location}}` |
| 3 | Document Date | दस्तावेज़ दिनांक | Document Date / दस्तावेज़ दिनांक | Date | No — Optional | `document_date` | `{{document_date}}` |
| 4 | Recipient Name | प्राप्तकर्ता का नाम | Recipient Name / प्राप्तकर्ता का नाम | Short answer | Yes — Required | `recipient_name` | `{{recipient_name}}` |
| 5 | Developer / Partnership Firm Name | विकासकर्ता / भागीदारी फर्म का नाम | Developer / Partnership Firm Name / विकासकर्ता / भागीदारी फर्म का नाम | Short answer | Yes — Required | `developer_company` | `{{developer_company}}` |
| 6 | Developer / Firm Address | विकासकर्ता / फर्म का पता | Developer / Firm Address / विकासकर्ता / फर्म का पता | Paragraph | Yes — Required | `developer_address` | `{{developer_address}}` |
| 7 | Project Name | परियोजना का नाम | Project Name / परियोजना का नाम | Short answer | Yes — Required | `project_name` | `{{project_name}}` |
| 8 | Khasra Number | खसरा नंबर | Khasra Number / खसरा नंबर | Short answer | Yes — Required | `khasra_number` | `{{khasra_number}}` |
| 9 | Project Location | परियोजना का स्थान | Project Location / परियोजना का स्थान | Short answer | Yes — Required | `project_location` | `{{project_location}}` |
| 10 | RERA Registration Number | रेरा पंजीयन क्रमांक | RERA Registration Number / रेरा पंजीयन क्रमांक | Short answer | Yes — Required | `rera_registration_no` | `{{rera_registration_no}}` |
| 11 | Completion Certificate Number | पूर्णता प्रमाण पत्र क्रमांक | Completion Certificate Number / पूर्णता प्रमाण पत्र क्रमांक | Short answer | Yes — Required | `completion_certificate_no` | `{{completion_certificate_no}}` |
| 12 | Completion Certificate Date | पूर्णता प्रमाण पत्र दिनांक | Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक | Date | Yes — Required | `completion_certificate_date` | `{{completion_certificate_date}}` |
| 13 | Signatory Name | हस्ताक्षरकर्ता का नाम | Signatory Name / हस्ताक्षरकर्ता का नाम | Short answer | Yes — Required | `signatory_name` | `{{signatory_name}}` |
| 14 | Signatory Role / Designation | हस्ताक्षरकर्ता का पद / पदनाम | Signatory Role / Designation / हस्ताक्षरकर्ता का पद / पदनाम | Short answer | No — Optional | `signatory_role` | `{{signatory_role}}` |

## NOC-specific decisions

- `Document Date / दस्तावेज़ दिनांक` is optional. Blank value renders as `..........`.
- `Signatory Role / Designation / हस्ताक्षरकर्ता का पद / पदनाम` is optional.
- All other NOC questions are required in the current Form.
- `{association_name}` is rendered exactly from the Form value after trimming whitespace.
- The NOC template must **not** append a fixed city such as `– इंदौर`.
- Backend logic must not add, remove, or normalize a city suffix in `association_name`.
- `association_location` is a separate field immediately below the association name.
- The current live Form uses:
  `Association Location / Address / एसोसिएशन का स्थान / पता`
- For backward compatibility, the old heading
  `Association Address / एसोसिएशन का  पता`
  may remain a reviewed alias mapping to `association_location`, but the current Form heading above is the primary contract.

## Explicit mapping

| Google Form Question | Google Sheet Column | Backend Parameter | Word Placeholder |
| --- | --- | --- | --- |
| Association / Society Name / एसोसिएशन / संस्था का नाम | Association / Society Name / एसोसिएशन / संस्था का नाम | `association_name` | `{{association_name}}` |
| Association Location / Address / एसोसिएशन का स्थान / पता | Association Location / Address / एसोसिएशन का स्थान / पता | `association_location` | `{{association_location}}` |
| Document Date / दस्तावेज़ दिनांक | Document Date / दस्तावेज़ दिनांक | `document_date` | `{{document_date}}` |
| Recipient Name / प्राप्तकर्ता का नाम | Recipient Name / प्राप्तकर्ता का नाम | `recipient_name` | `{{recipient_name}}` |
| Developer / Partnership Firm Name / विकासकर्ता / भागीदारी फर्म का नाम | Developer / Partnership Firm Name / विकासकर्ता / भागीदारी फर्म का नाम | `developer_company` | `{{developer_company}}` |
| Developer / Firm Address / विकासकर्ता / फर्म का पता | Developer / Firm Address / विकासकर्ता / फर्म का पता | `developer_address` | `{{developer_address}}` |
| Project Name / परियोजना का नाम | Project Name / परियोजना का नाम | `project_name` | `{{project_name}}` |
| Khasra Number / खसरा नंबर | Khasra Number / खसरा नंबर | `khasra_number` | `{{khasra_number}}` |
| Project Location / परियोजना का स्थान | Project Location / परियोजना का स्थान | `project_location` | `{{project_location}}` |
| RERA Registration Number / रेरा पंजीयन क्रमांक | RERA Registration Number / रेरा पंजीयन क्रमांक | `rera_registration_no` | `{{rera_registration_no}}` |
| Completion Certificate Number / पूर्णता प्रमाण पत्र क्रमांक | Completion Certificate Number / पूर्णता प्रमाण पत्र क्रमांक | `completion_certificate_no` | `{{completion_certificate_no}}` |
| Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक | Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक | `completion_certificate_date` | `{{completion_certificate_date}}` |
| Signatory Name / हस्ताक्षरकर्ता का नाम | Signatory Name / हस्ताक्षरकर्ता का नाम | `signatory_name` | `{{signatory_name}}` |
| Signatory Role / Designation / हस्ताक्षरकर्ता का पद / पदनाम | Signatory Role / Designation / हस्ताक्षरकर्ता का पद / पदनाम | `signatory_role` | `{{signatory_role}}` |

## Expected header row — `NOC Responses`

```text
Timestamp
Association / Society Name / एसोसिएशन / संस्था का नाम
Association Location / Address / एसोसिएशन का स्थान / पता
Document Date / दस्तावेज़ दिनांक
Recipient Name / प्राप्तकर्ता का नाम
Developer / Partnership Firm Name / विकासकर्ता / भागीदारी फर्म का नाम
Developer / Firm Address / विकासकर्ता / फर्म का पता
Project Name / परियोजना का नाम
Khasra Number / खसरा नंबर
Project Location / परियोजना का स्थान
RERA Registration Number / रेरा पंजीयन क्रमांक
Completion Certificate Number / पूर्णता प्रमाण पत्र क्रमांक
Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक
Signatory Name / हस्ताक्षरकर्ता का नाम
Signatory Role / Designation / हस्ताक्षरकर्ता का पद / पदनाम
processing_status
generated_file
processed_at
error_message
```

Operational columns: **P:S**

---

# Affidavit Form

## Form identity

**Title:** Affidavit Details Form / शपथ पत्र विवरण फॉर्म

**Description:**  
Please fill in the required details carefully for preparing the affidavit document.  
कृपया शपथ पत्र तैयार करने हेतु आवश्यक जानकारी सही-सही भरें।

## Questions

| # | English Name | Hindi Name | Exact Google Form Question | Form Type | Required? | Backend Parameter | Word Placeholder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Name | नाम | Name / नाम | Short answer | Yes — Required | `name` | `{{NAME}}` |
| 2 | Father’s Name | पिता का नाम | Father’s Name / पिता का नाम | Short answer | Yes — Required | `father_name` | `{{FATHER}}` |
| 3 | Age | उम्र | Age / उम्र | Short answer | Yes — Required | `age` | `{{AGE}}` |
| 4 | Residential Address | निवास का पता | Residential Address / निवास का पता | Paragraph | Yes — Required | `address` | `{{ADDRESS}}` |
| 5 | Project Name | परियोजना का नाम | Project Name / परियोजना का नाम | Short answer | Yes — Required | `project_name` | `{{PROJECT}}` |
| 6 | Khasra Number(s) | खसरा नंबर | Khasra Number(s) / खसरा नंबर | Short answer | Yes — Required | `land_details` | `{{LAND}}` |
| 7 | Project Location | परियोजना का स्थान | Project Location / परियोजना का स्थान | Paragraph | Yes — Required | `project_location` | `{{PROJECT_LOCATION}}` |
| 8 | RERA Registration Number | रेरा पंजीयन क्रमांक | RERA Registration Number / रेरा पंजीयन क्रमांक | Short answer | Yes — Required | `rera_registration_no` | `{{RERA}}` |
| 9 | Developer Name | विकासकर्ता का नाम | Developer Name / विकासकर्ता का नाम | Short answer | Yes — Required | `developer_name` | `{{DEVELOPER}}` |
| 10 | Completion Certificate Number | पूर्णता प्रमाण पत्र क्रमांक | Completion Certificate Number / पूर्णता प्रमाण पत्र क्रमांक | Short answer | Yes — Required | `completion_certificate_no` | `{{CERT_NO}}` |
| 11 | Completion Certificate Date | पूर्णता प्रमाण पत्र दिनांक | Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक | Date | Yes — Required | `completion_certificate_date` | `{{CERT_DATE}}` |
| 12 | Plot Number | भूखंड क्रमांक | Plot Number / भूखंड क्रमांक | Short answer | Yes — Required | `plot_no` | `{{PLOT_NO}}` |
| 13 | Association Name | संघ का नाम | Association Name / संघ का नाम | Short answer | Yes — Required | `association_name` | `{{ASSOCIATION}}` |
| 14 | Designation | पद | Designation / पद | Short answer | Yes — Required | `designation` | `{{DESIGNATION}}` |
| 15 | Authority Location | सक्षम प्राधिकारी का स्थान | Authority Location / सक्षम प्राधिकारी का स्थान | Short answer | Yes — Required | `authority_location` | `{{AUTHORITY_LOCATION}}` |
| 16 | City / Place | शहर / स्थान | City / Place / शहर / स्थान | Short answer | Yes — Required | `city` | `{{CITY}}` |
| 17 | Document Date | दस्तावेज़ दिनांक | Document Date / दस्तावेज़ दिनांक | Date | No — Optional | `document_date` | `{{DATE}}` |

## Affidavit-specific decisions

- The Form now has **17** document questions.
- `Document Date / दस्तावेज़ दिनांक` is the only optional question.
- The old combined Khasra/location input has been split:
  - `Khasra Number(s) / खसरा नंबर` -> `land_details` -> `{{LAND}}`
  - `Project Location / परियोजना का स्थान` -> `project_location` -> `{{PROJECT_LOCATION}}`
- The Affidavit DOCX target contract must contain:
  `{{PROJECT_LOCATION}}`
  immediately after the Khasra/land value in the relevant sentence.
- `Plot Number / भूखंड क्रमांक` is required.
  Recommended help text:
  **Enter plot number only. / केवल भूखंड क्रमांक दर्ज करें। Example / उदाहरण: 26**
- `Age / उम्र` is required. If backend validation is retained, keep the existing valid age range.
- The existing legacy Affidavit generator used uppercase template/context keys. The future Sheets adapter must translate the snake_case backend parameters into the uppercase template variables shown here.

## Explicit mapping

| Google Form Question | Google Sheet Column | Backend Parameter | Word Placeholder |
| --- | --- | --- | --- |
| Name / नाम | Name / नाम | `name` | `{{NAME}}` |
| Father’s Name / पिता का नाम | Father’s Name / पिता का नाम | `father_name` | `{{FATHER}}` |
| Age / उम्र | Age / उम्र | `age` | `{{AGE}}` |
| Residential Address / निवास का पता | Residential Address / निवास का पता | `address` | `{{ADDRESS}}` |
| Project Name / परियोजना का नाम | Project Name / परियोजना का नाम | `project_name` | `{{PROJECT}}` |
| Khasra Number(s) / खसरा नंबर | Khasra Number(s) / खसरा नंबर | `land_details` | `{{LAND}}` |
| Project Location / परियोजना का स्थान | Project Location / परियोजना का स्थान | `project_location` | `{{PROJECT_LOCATION}}` |
| RERA Registration Number / रेरा पंजीयन क्रमांक | RERA Registration Number / रेरा पंजीयन क्रमांक | `rera_registration_no` | `{{RERA}}` |
| Developer Name / विकासकर्ता का नाम | Developer Name / विकासकर्ता का नाम | `developer_name` | `{{DEVELOPER}}` |
| Completion Certificate Number / पूर्णता प्रमाण पत्र क्रमांक | Completion Certificate Number / पूर्णता प्रमाण पत्र क्रमांक | `completion_certificate_no` | `{{CERT_NO}}` |
| Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक | Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक | `completion_certificate_date` | `{{CERT_DATE}}` |
| Plot Number / भूखंड क्रमांक | Plot Number / भूखंड क्रमांक | `plot_no` | `{{PLOT_NO}}` |
| Association Name / संघ का नाम | Association Name / संघ का नाम | `association_name` | `{{ASSOCIATION}}` |
| Designation / पद | Designation / पद | `designation` | `{{DESIGNATION}}` |
| Authority Location / सक्षम प्राधिकारी का स्थान | Authority Location / सक्षम प्राधिकारी का स्थान | `authority_location` | `{{AUTHORITY_LOCATION}}` |
| City / Place / शहर / स्थान | City / Place / शहर / स्थान | `city` | `{{CITY}}` |
| Document Date / दस्तावेज़ दिनांक | Document Date / दस्तावेज़ दिनांक | `document_date` | `{{DATE}}` |

## Expected header row — `Affidavit Responses`

```text
Timestamp
Name / नाम
Father’s Name / पिता का नाम
Age / उम्र
Residential Address / निवास का पता
Project Name / परियोजना का नाम
Khasra Number(s) / खसरा नंबर
Project Location / परियोजना का स्थान
RERA Registration Number / रेरा पंजीयन क्रमांक
Developer Name / विकासकर्ता का नाम
Completion Certificate Number / पूर्णता प्रमाण पत्र क्रमांक
Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक
Plot Number / भूखंड क्रमांक
Association Name / संघ का नाम
Designation / पद
Authority Location / सक्षम प्राधिकारी का स्थान
City / Place / शहर / स्थान
Document Date / दस्तावेज़ दिनांक
processing_status
generated_file
processed_at
error_message
```

Operational columns: **S:V**

---

# Consent Letter Form

## Form identity

**Title:** Consent Letter Details Form / सहमति पत्र विवरण फॉर्म

**Description:**  
Please fill in the required details carefully for preparing the Consent Letter.  
कृपया सहमति पत्र तैयार करने हेतु आवश्यक जानकारी सही-सही भरें।

**Backend key:** `consent`

Do not use `concern` as the new backend document key.

## Questions

| # | English Name | Hindi Name | Exact Google Form Question | Form Type | Required? | Backend Parameter | Word Placeholder |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Society / Association Name | संस्था / एसोसिएशन का नाम | Society / Association Name / संस्था / एसोसिएशन का नाम | Short answer | Yes — Required | `society_name` | `{{ society_name }}` |
| 2 | Society Address | संस्था का पता | Society Address / संस्था का पता | Paragraph | Yes — Required | `society_address` | `{{ society_address }}` |
| 3 | Applicant Name | आवेदक का नाम | Applicant Name / आवेदक का नाम | Short answer | Yes — Required | `applicant_name` | `{{ applicant_name }}` |
| 4 | Applicant Address | आवेदक का पता | Applicant Address / आवेदक का पता | Paragraph | Yes — Required | `applicant_address` | `{{ applicant_address }}` |
| 5 | Project Name | परियोजना का नाम | Project Name / परियोजना का नाम | Short answer | Yes — Required | `project_name` | `{{ project_name }}` |
| 6 | Survey / Khasra Numbers | सर्वे / खसरा नंबर | Survey / Khasra Numbers / सर्वे / खसरा नंबर | Short answer | Yes — Required | `survey_numbers` | `{{ survey_numbers }}` |
| 7 | Project Location | परियोजना का स्थान | Project Location / परियोजना का स्थान | Short answer | Yes — Required | `project_location` | `{{ project_location }}` |
| 8 | RERA Registration Number | रेरा पंजीयन क्रमांक | RERA Registration Number / रेरा पंजीयन क्रमांक | Short answer | Yes — Required | `registration_no` | `{{ registration_no }}` |
| 9 | Completion Certificate Number | पूर्णता प्रमाण पत्र नंबर | Completion Certificate Number / पूर्णता प्रमाण पत्र नंबर | Short answer | Yes — Required | `certificate_no` | `{{ certificate_no }}` |
| 10 | Completion Certificate Date | पूर्णता प्रमाण पत्र दिनांक | Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक | Date | Yes — Required | `certificate_date` | `{{ certificate_date }}` |
| 11 | Plot / Khand Number | प्लॉट / खंड नंबर | Plot / Khand Number / प्लॉट / खंड नंबर | Short answer | Yes — Required | `plot_no` | `{{ plot_no }}` |
| 12 | Member 1 Name | सदस्य 1 का नाम | Member 1 Name / सदस्य 1 का नाम | Short answer | Yes — Required | `member_name_1` | `{{ members[0].name }}` |
| 13 | Member 1 Designation | सदस्य 1 का पद / दायित्व | Member 1 Designation / सदस्य 1 का पद / दायित्व | Short answer | Yes — Required | `member_designation_1` | `{{ members[0].designation }}` |
| 14 | Member 2 Name | सदस्य 2 का नाम | Member 2 Name / सदस्य 2 का नाम | Short answer | Yes — Required | `member_name_2` | `{{ members[1].name }}` |
| 15 | Member 2 Designation | सदस्य 2 का पद / दायित्व | Member 2 Designation / सदस्य 2 का पद / दायित्व | Short answer | Yes — Required | `member_designation_2` | `{{ members[1].designation }}` |
| 16 | Member 3 Name | सदस्य 3 का नाम | Member 3 Name / सदस्य 3 का नाम | Short answer | Yes — Required | `member_name_3` | `{{ members[2].name }}` |
| 17 | Member 3 Designation | सदस्य 3 का पद / दायित्व | Member 3 Designation / सदस्य 3 का पद / दायित्व | Short answer | Yes — Required | `member_designation_3` | `{{ members[2].designation }}` |
| 18 | Member 4 Name | सदस्य 4 का नाम | Member 4 Name / सदस्य 4 का नाम | Short answer | Yes — Required | `member_name_4` | `{{ members[3].name }}` |
| 19 | Member 4 Designation | सदस्य 4 का पद / दायित्व | Member 4 Designation / सदस्य 4 का पद / दायित्व | Short answer | Yes — Required | `member_designation_4` | `{{ members[3].designation }}` |
| 20 | Member 5 Name | सदस्य 5 का नाम | Member 5 Name / सदस्य 5 का नाम | Short answer | Yes — Required | `member_name_5` | `{{ members[4].name }}` |
| 21 | Member 5 Designation | सदस्य 5 का पद / दायित्व | Member 5 Designation / सदस्य 5 का पद / दायित्व | Short answer | Yes — Required | `member_designation_5` | `{{ members[4].designation }}` |
| 22 | Place | स्थान | Place / स्थान | Short answer | Yes — Required | `place` | `{{ place }}` |
| 23 | Document Date | दस्तावेज़ दिनांक | Document Date / दस्तावेज़ दिनांक | Date | No — Optional | `document_date` | `{{ document_date }}` |
| 24 | Signatory Name | हस्ताक्षरकर्ता का नाम | Signatory Name / हस्ताक्षरकर्ता का नाम | Short answer | Yes — Required | `signatory_name` | `{{ signatory_name }}` |

## Consent-specific decisions

- `Document Date / दस्तावेज़ दिनांक` is the **only optional field** in the current Form.
- All other 23 questions are required, including:
  - Society Address
  - Applicant Address
  - Project Location
  - Completion Certificate Number
  - Completion Certificate Date
  - Plot / Khand Number
  - all five member names
  - all five member designations
  - Place
  - Signatory Name
- This requiredness intentionally differs from the older standalone Consent application's looser validation. The combined backend should follow the current Form/business requirement.
- Member fields must be assembled in fixed order:

```text
members[0] = {name: member_name_1, designation: member_designation_1}
members[1] = {name: member_name_2, designation: member_designation_2}
members[2] = {name: member_name_3, designation: member_designation_3}
members[3] = {name: member_name_4, designation: member_designation_4}
members[4] = {name: member_name_5, designation: member_designation_5}
```

- Keep all five member entries; do not collapse/reorder them.
- `Document Date` blank should render as `..........`.
- `Completion Certificate Date` is now required by the live Form.

## Explicit mapping

| Google Form Question | Google Sheet Column | Backend Parameter | Word Placeholder |
| --- | --- | --- | --- |
| Society / Association Name / संस्था / एसोसिएशन का नाम | Society / Association Name / संस्था / एसोसिएशन का नाम | `society_name` | `{{ society_name }}` |
| Society Address / संस्था का पता | Society Address / संस्था का पता | `society_address` | `{{ society_address }}` |
| Applicant Name / आवेदक का नाम | Applicant Name / आवेदक का नाम | `applicant_name` | `{{ applicant_name }}` |
| Applicant Address / आवेदक का पता | Applicant Address / आवेदक का पता | `applicant_address` | `{{ applicant_address }}` |
| Project Name / परियोजना का नाम | Project Name / परियोजना का नाम | `project_name` | `{{ project_name }}` |
| Survey / Khasra Numbers / सर्वे / खसरा नंबर | Survey / Khasra Numbers / सर्वे / खसरा नंबर | `survey_numbers` | `{{ survey_numbers }}` |
| Project Location / परियोजना का स्थान | Project Location / परियोजना का स्थान | `project_location` | `{{ project_location }}` |
| RERA Registration Number / रेरा पंजीयन क्रमांक | RERA Registration Number / रेरा पंजीयन क्रमांक | `registration_no` | `{{ registration_no }}` |
| Completion Certificate Number / पूर्णता प्रमाण पत्र नंबर | Completion Certificate Number / पूर्णता प्रमाण पत्र नंबर | `certificate_no` | `{{ certificate_no }}` |
| Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक | Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक | `certificate_date` | `{{ certificate_date }}` |
| Plot / Khand Number / प्लॉट / खंड नंबर | Plot / Khand Number / प्लॉट / खंड नंबर | `plot_no` | `{{ plot_no }}` |
| Member 1 Name / सदस्य 1 का नाम | Member 1 Name / सदस्य 1 का नाम | `member_name_1` | `{{ members[0].name }}` |
| Member 1 Designation / सदस्य 1 का पद / दायित्व | Member 1 Designation / सदस्य 1 का पद / दायित्व | `member_designation_1` | `{{ members[0].designation }}` |
| Member 2 Name / सदस्य 2 का नाम | Member 2 Name / सदस्य 2 का नाम | `member_name_2` | `{{ members[1].name }}` |
| Member 2 Designation / सदस्य 2 का पद / दायित्व | Member 2 Designation / सदस्य 2 का पद / दायित्व | `member_designation_2` | `{{ members[1].designation }}` |
| Member 3 Name / सदस्य 3 का नाम | Member 3 Name / सदस्य 3 का नाम | `member_name_3` | `{{ members[2].name }}` |
| Member 3 Designation / सदस्य 3 का पद / दायित्व | Member 3 Designation / सदस्य 3 का पद / दायित्व | `member_designation_3` | `{{ members[2].designation }}` |
| Member 4 Name / सदस्य 4 का नाम | Member 4 Name / सदस्य 4 का नाम | `member_name_4` | `{{ members[3].name }}` |
| Member 4 Designation / सदस्य 4 का पद / दायित्व | Member 4 Designation / सदस्य 4 का पद / दायित्व | `member_designation_4` | `{{ members[3].designation }}` |
| Member 5 Name / सदस्य 5 का नाम | Member 5 Name / सदस्य 5 का नाम | `member_name_5` | `{{ members[4].name }}` |
| Member 5 Designation / सदस्य 5 का पद / दायित्व | Member 5 Designation / सदस्य 5 का पद / दायित्व | `member_designation_5` | `{{ members[4].designation }}` |
| Place / स्थान | Place / स्थान | `place` | `{{ place }}` |
| Document Date / दस्तावेज़ दिनांक | Document Date / दस्तावेज़ दिनांक | `document_date` | `{{ document_date }}` |
| Signatory Name / हस्ताक्षरकर्ता का नाम | Signatory Name / हस्ताक्षरकर्ता का नाम | `signatory_name` | `{{ signatory_name }}` |

## Expected header row — `Consent Responses`

```text
Timestamp
Society / Association Name / संस्था / एसोसिएशन का नाम
Society Address / संस्था का पता
Applicant Name / आवेदक का नाम
Applicant Address / आवेदक का पता
Project Name / परियोजना का नाम
Survey / Khasra Numbers / सर्वे / खसरा नंबर
Project Location / परियोजना का स्थान
RERA Registration Number / रेरा पंजीयन क्रमांक
Completion Certificate Number / पूर्णता प्रमाण पत्र नंबर
Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक
Plot / Khand Number / प्लॉट / खंड नंबर
Member 1 Name / सदस्य 1 का नाम
Member 1 Designation / सदस्य 1 का पद / दायित्व
Member 2 Name / सदस्य 2 का नाम
Member 2 Designation / सदस्य 2 का पद / दायित्व
Member 3 Name / सदस्य 3 का नाम
Member 3 Designation / सदस्य 3 का पद / दायित्व
Member 4 Name / सदस्य 4 का नाम
Member 4 Designation / सदस्य 4 का पद / दायित्व
Member 5 Name / सदस्य 5 का नाम
Member 5 Designation / सदस्य 5 का पद / दायित्व
Place / स्थान
Document Date / दस्तावेज़ दिनांक
Signatory Name / हस्ताक्षरकर्ता का नाम
processing_status
generated_file
processed_at
error_message
```

Operational columns: **Z:AC**

---

# Common processing status contract

| Stored status | Action |
| --- | --- |
| blank | Process |
| `ERROR` | Retry |
| `PROCESSING` | Skip |
| `GENERATED` | Skip |
| Any other non-empty value | Skip |

For an eligible row:

1. Set `processing_status` to `PROCESSING`.
2. Validate and map the row for the selected document type.
3. Render the correct DOCX template.
4. Save into that document tab's selected output folder.
5. Set `processing_status` to `GENERATED`.
6. Store the generated filename in `generated_file`.
7. Store `processed_at` as `DD-MM-YYYY HH:MM:SS`.
8. Clear `error_message`.

On failure:
- set `processing_status` to `ERROR`;
- store exception text in `error_message`;
- continue processing remaining eligible rows.

---

# Combined desktop application implications

The future `legal-document-generator` implementation should treat this specification as the Form/Sheet contract.

Each document type must independently define:

- backend key;
- worksheet;
- template;
- heading-to-parameter mapping;
- required fields;
- date behavior;
- filename builder;
- output folder.

Target tabs:

```text
| NOC | Affidavit | Consent | ...future templates |
```

Each tab should have:

- Save Folder
- Browse
- Generate
- Open Generated Folder
- status/result counts

Do **not** display the internal template filename in the UI.

Each tab persists its own output directory.

Templates and worksheet logic must be selected internally from the document registry.

---

# Implementation delta for Codex

When implementing the combined application, Codex must account for these changes from the older projects/specification:

1. **NOC requiredness**
   - Required: 12 fields.
   - Optional: `document_date`, `signatory_role`.

2. **NOC association header**
   - Template title uses only `{{association_name}}`.
   - No hardcoded `– इंदौर`.
   - No backend city-suffix manipulation.

3. **NOC association location heading**
   - Current Form contract:
     `Association Location / Address / एसोसिएशन का स्थान / पता`
   - Preserve legacy heading as an alias if needed.

4. **Affidavit field count**
   - Increase from 16 to 17.

5. **Affidavit Khasra/location split**
   - `land_details` = Khasra numbers only.
   - new `project_location`.
   - new `{{PROJECT_LOCATION}}` template mapping.

6. **Affidavit requiredness**
   - 16 required.
   - only `document_date` optional.

7. **Consent backend naming**
   - backend key = `consent`
   - worksheet = `Consent Responses`

8. **Consent requiredness**
   - 23 required.
   - only `document_date` optional.
   - do not preserve the old standalone app's optional business rules if they conflict with the current Form.

9. **Shared operational columns**
   - exact names:
     `processing_status`, `generated_file`, `processed_at`, `error_message`.

10. **Future scalability**
    - document types should be registry-driven;
    - do not hardcode one UI function per template;
    - adding future templates should require a new document specification/template, not a rewrite of shared processing code.

---

# Manual Sheet setup

Use the same Google Spreadsheet with:

```text
NOC Responses
Affidavit Responses
Consent Responses
```

For each Form:

1. Connect responses to the common spreadsheet.
2. Confirm the Form-created response tab.
3. Rename it to the target worksheet name.
4. Add the four operational columns at the far right.
5. Submit one test response.
6. Confirm that the exact Form question becomes the Sheet header.
7. Confirm required fields cannot be skipped.
8. Test an omitted Document Date.
9. Keep credentials/service-account access unchanged.

---

# Final verified counts

| Backend key | Worksheet | Questions | Required | Optional |
| --- | --- | ---: | ---: | ---: |
| `noc` | `NOC Responses` | 14 | 12 | 2 |
| `affidavit` | `Affidavit Responses` | 17 | 16 | 1 |
| `consent` | `Consent Responses` | 24 | 23 | 1 |
| **Total** |  | **55** | **51** | **4** |

This requiredness reflects the current Google Forms rather than the older standalone application defaults.