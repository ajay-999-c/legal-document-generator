# FORM_SPEC.md — Final Google Forms / Sheets / Backend Contract

**Status:** Current source of truth  
**Scope:** All six document workflows in `legal-document-generator`  
**Purpose:** Give Codex one stable contract for Google Form questions, Google Sheet headers, backend parameters, template semantics, validation, and migration rules.

> This specification supersedes older Form specs, older field names, and legacy standalone-app assumptions wherever they conflict with this file.

---

## 1. Source-of-truth rules

1. **Do not invent fields.**
2. **Do not fuzzy-match headings.**
3. Exact Google Form question text becomes the Google Sheet column header.
4. Existing heading normalization may handle harmless whitespace/newline/case formatting, but different wording requires an explicit reviewed mapping/alias.
5. For implementation/debugging, compare this specification with the **actual live Sheet row-1 headers** using read-only checks before mutation.
6. Preserve the four operational columns in every response worksheet:
   - `processing_status`
   - `generated_file`
   - `processed_at`
   - `error_message`
7. `Timestamp` is Google Forms metadata, not a document field.
8. Do not expose internal template filenames, backend parameters, spreadsheet IDs, or credentials in the office GUI.
9. Keep one shared backend, processor, Sheets service, registry, CLI, and `config.yaml`.

---

# 2. Canonical document registry

| Document | Backend key | Worksheet |
|---|---|---|
| NOC | `noc` | `NOC Responses` |
| Affidavit | `affidavit` | `Affidavit Responses` |
| Consent Letter | `consent` | `Consent Responses` |
| Registration Application | `registration` | `Registration Responses` |
| By-Law | `by_law` | `By-Law Responses` |
| Form-A Registration | `form_a_registration` | `Form A Registration Responses` |

---

# 3. Shared address terminology

The current business contract uses two distinct concepts where required:

### `project_location`
Location only.

Example:

```text
ग्राम बिसनावदा तहसील राऊ जिला इंदौर (म.प्र.)
```

### `association_address`
Complete land/address value entered by the user, including Khasra number + project location.

Example:

```text
खसरा नंबर 343/1, 338/1/2 ग्राम बिसनावदा तहसील राऊ जिला इंदौर (म.प्र.)
```

Rules:

- `association_address` is direct user input.
- Do not parse it.
- Do not derive it from `project_location`.
- Do not recreate a separate `khasra_number` field in workflows where this spec removed it.
- Do not split `association_address` into array/list indexes.

---

# 4. Common processing-status contract

| Stored status | Action |
|---|---|
| blank / whitespace | Process |
| `ERROR` | Retry |
| `PROCESSING` | Skip |
| `GENERATED` | Skip |
| any other non-empty value | Skip |

For a successful eligible row:

1. set `processing_status = PROCESSING`;
2. validate/map row;
3. render DOCX;
4. save file;
5. set `processing_status = GENERATED`;
6. write `generated_file`;
7. write `processed_at`;
8. clear `error_message`.

On failure:

- set `processing_status = ERROR`;
- write the error message;
- continue safely with remaining eligible rows.

---

# 5. NOC

## Form identity

**Form name:** `NOC Document Details Form`

**Description:**  
`Please fill in the required details carefully for preparing the NOC document. / कृपया NOC दस्तावेज़ तैयार करने हेतु आवश्यक जानकारी सही-सही भरें।`

**Worksheet:** `NOC Responses`  
**Backend key:** `noc`

## Final fields

| # | Exact Google Form / Sheet column | Type | Required? | Backend parameter | Template meaning |
|---|---|---|---|---|---|
| 1 | Association Name / संस्था का नाम | Short answer | Yes | `association_name` | Association title/name only |
| 2 | Project Location / परियोजना का स्थान | Paragraph | Yes | `project_location` | Location-only line |
| 3 | Association Address / संस्था का पूरा पता | Paragraph | Yes | `association_address` | Complete Khasra + project location |
| 4 | Document Date / दस्तावेज़ दिनांक | Date | No | `document_date` | Optional date |
| 5 | Recipient Name / प्राप्तकर्ता का नाम | Short answer | Yes | `recipient_name` | Recipient |
| 6 | Developer Company / विकासकर्ता फर्म का नाम | Short answer | Yes | `developer_company` | Developer/firm |
| 7 | Developer Address / विकासकर्ता का पता | Paragraph | Yes | `developer_address` | Developer address |
| 8 | Project Name / परियोजना का नाम | Short answer | Yes | `project_name` | Project |
| 9 | RERA Registration Number / रेरा पंजीयन क्रमांक | Short answer | Yes | `rera_registration_no` | RERA |
| 10 | Completion Certificate Number / पूर्णता प्रमाण पत्र क्रमांक | Short answer | Yes | `completion_certificate_no` | Completion certificate no. |
| 11 | Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक | Date | Yes | `completion_certificate_date` | Completion certificate date |
| 12 | Signatory Name / हस्ताक्षरकर्ता का नाम | Short answer | Yes | `signatory_name` | Signatory |

### Removed legacy NOC fields

Do not require or restore:

- `khasra_number`
- `association_location`
- `signatory_role`

**There is no Signatory Role field in the final NOC contract.**

### NOC template rules

- `association_name` must render without a hardcoded city suffix.
- `project_location` is the location-only header/subheading value.
- `association_address` is the complete Khasra + location text in the body.
- `signatory_role` must not be expected by the template validator or adapter.

## Exact expected header sequence

```text
Timestamp
Association Name / संस्था का नाम
Project Location / परियोजना का स्थान
Association Address / संस्था का पूरा पता
Document Date / दस्तावेज़ दिनांक
Recipient Name / प्राप्तकर्ता का नाम
Developer Company / विकासकर्ता फर्म का नाम
Developer Address / विकासकर्ता का पता
Project Name / परियोजना का नाम
RERA Registration Number / रेरा पंजीयन क्रमांक
Completion Certificate Number / पूर्णता प्रमाण पत्र क्रमांक
Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक
Signatory Name / हस्ताक्षरकर्ता का नाम
processing_status
generated_file
processed_at
error_message
```

---

# 6. Affidavit

## Form identity

**Form name:** `Affidavit Details Form / शपथ पत्र विवरण फॉर्म`

**Description:**  
`Please fill in the required details carefully for preparing the Affidavit document. / कृपया शपथ पत्र तैयार करने हेतु आवश्यक जानकारी सही-सही भरें।`

**Worksheet:** `Affidavit Responses`  
**Backend key:** `affidavit`

## Final fields

| # | Exact Google Form / Sheet column | Type | Required? | Backend parameter | Final template placeholder/meaning |
|---|---|---|---|---|---|
| 1 | Name / नाम | Short answer | Yes | `name` | `{{NAME}}` |
| 2 | Father’s Name / पिता का नाम | Short answer | Yes | `father_name` | `{{FATHER}}` |
| 3 | Age / उम्र | Short answer | Yes | `age` | `{{AGE}}` |
| 4 | Residential Address / निवास का पता | Paragraph | Yes | `address` | `{{ADDRESS}}` |
| 5 | Project Name / परियोजना का नाम | Short answer | Yes | `project_name` | `{{PROJECT}}` |
| 6 | Association Address / संस्था का पूरा पता | Paragraph | Yes | `association_address` | `{{association_address}}` |
| 7 | RERA Registration Number / रेरा पंजीयन क्रमांक | Short answer | Yes | `rera_registration_no` | `{{RERA}}` |
| 8 | Developer Name / विकासकर्ता का नाम | Short answer | Yes | `developer_name` | `{{DEVELOPER}}` |
| 9 | Completion Certificate Number / पूर्णता प्रमाण पत्र क्रमांक | Short answer | Yes | `completion_certificate_no` | `{{CERT_NO}}` |
| 10 | Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक | Date | Yes | `completion_certificate_date` | `{{CERT_DATE}}` |
| 11 | Plot Number / भूखंड क्रमांक | Short answer | Yes | `plot_no` | `{{PLOT_NO}}` |
| 12 | Association Name / संघ का नाम | Short answer | Yes | `association_name` | `{{ASSOCIATION_NAME}}` |
| 13 | Authority Location / सक्षम प्राधिकारी का स्थान | Short answer | Yes | `authority_location` | `{{AUTHORITY_LOCATION}}` |
| 14 | City / Place / शहर / स्थान | Short answer | Yes | `city` | `{{CITY}}` |

### Removed legacy Affidavit fields

Do not require or restore:

- `land_details`
- old Khasra field
- `project_location`
- `designation`
- `document_date`

### Fixed Affidavit content

- Designation is fixed in the document as **कार्यकारिणी कोषाध्यक्ष**.
- There is no Google Form Designation field.
- There is no Google Form Document Date field.
- Manual/fixed blank date markers in the final template must remain fixed.
- `association_address` already contains Khasra + location.

## Exact expected header sequence

```text
Timestamp
Name / नाम
Father’s Name / पिता का नाम
Age / उम्र
Residential Address / निवास का पता
Project Name / परियोजना का नाम
Association Address / संस्था का पूरा पता
RERA Registration Number / रेरा पंजीयन क्रमांक
Developer Name / विकासकर्ता का नाम
Completion Certificate Number / पूर्णता प्रमाण पत्र क्रमांक
Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक
Plot Number / भूखंड क्रमांक
Association Name / संघ का नाम
Authority Location / सक्षम प्राधिकारी का स्थान
City / Place / शहर / स्थान
processing_status
generated_file
processed_at
error_message
```

---

# 7. Consent Letter

## Form identity

**Form name:** `Consent Letter Details Form / सहमति पत्र विवरण फॉर्म`

**Description:**  
`Please fill in the required details carefully for preparing the Consent Letter. Committee Members 1–5 are mandatory; Members 6–11 are optional. / कृपया सहमति पत्र तैयार करने हेतु आवश्यक जानकारी सही-सही भरें। समिति सदस्य 1–5 अनिवार्य हैं तथा सदस्य 6–11 वैकल्पिक हैं।`

**Worksheet:** `Consent Responses`  
**Backend key:** `consent`

## Main fields

| # | Exact Google Form / Sheet column | Type | Required? | Backend parameter |
|---|---|---|---|---|
| 1 | Association Name / संस्था / एसोसिएशन का नाम | Short answer | Yes | `association_name` |
| 2 | Project Location / परियोजना का स्थान | Paragraph | Yes | `project_location` |
| 3 | Applicant Name / आवेदक का नाम | Short answer | Yes | `applicant_name` |
| 4 | Applicant Address / आवेदक का पता | Paragraph | Yes | `applicant_address` |
| 5 | Project Name / परियोजना का नाम | Short answer | Yes | `project_name` |
| 6 | Association Address / संस्था का पूरा पता | Paragraph | Yes | `association_address` |
| 7 | RERA Registration Number / रेरा पंजीयन क्रमांक | Short answer | Yes | `registration_no` |
| 8 | Completion Certificate Number / पूर्णता प्रमाण पत्र नंबर | Short answer | Yes | `certificate_no` |
| 9 | Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक | Date | Yes | `certificate_date` |
| 10 | Plot / Khand Number / प्लॉट / खंड नंबर | Short answer | Yes | `plot_no` |
| 11 | Place / स्थान | Short answer | Yes | `place` |
| 12 | Document Date / दस्तावेज़ दिनांक | Date | No | `document_date` |
| 13 | Signatory Name / हस्ताक्षरकर्ता का नाम | Short answer | Yes | `signatory_name` |

### Removed legacy Consent fields

Do not require or restore:

- `society_address`
- `survey_numbers`

### Consent address behavior

- `project_location` = location only.
- `association_address` = complete Khasra + project location.
- Header/location areas use `project_location`.
- Body land/address sentence uses `association_address`.

## Committee members

Member names may already include father-name text. Do not parse it and do not create a separate father-name field.

### Members 1–5 — required

For each N = 1..5:

- `Member N Name / सदस्य N का नाम`
- `Member N Designation / सदस्य N का पद / दायित्व`

Both required.

Backend:

- `member_N_name`
- `member_N_designation`

### Members 6–11 — optional

For each N = 6..11:

- `Member N Name / सदस्य N का नाम`
- `Member N Designation / सदस्य N का पद / दायित्व`

Rules:

- both blank → ignore;
- either supplied → both required;
- reject non-contiguous optional members;
- minimum populated members = 5;
- maximum populated members = 11.

Backend must construct:

```python
members = [
    {"name": "...", "designation": "..."},
    ...
]
```

The final template dynamically renders only populated members.

## Exact expected header sequence

```text
Timestamp
Association Name / संस्था / एसोसिएशन का नाम
Project Location / परियोजना का स्थान
Applicant Name / आवेदक का नाम
Applicant Address / आवेदक का पता
Project Name / परियोजना का नाम
Association Address / संस्था का पूरा पता
RERA Registration Number / रेरा पंजीयन क्रमांक
Completion Certificate Number / पूर्णता प्रमाण पत्र नंबर
Completion Certificate Date / पूर्णता प्रमाण पत्र दिनांक
Plot / Khand Number / प्लॉट / खंड नंबर
Place / स्थान
Document Date / दस्तावेज़ दिनांक
Signatory Name / हस्ताक्षरकर्ता का नाम
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
Member 6 Name / सदस्य 6 का नाम
Member 6 Designation / सदस्य 6 का पद / दायित्व
Member 7 Name / सदस्य 7 का नाम
Member 7 Designation / सदस्य 7 का पद / दायित्व
Member 8 Name / सदस्य 8 का नाम
Member 8 Designation / सदस्य 8 का पद / दायित्व
Member 9 Name / सदस्य 9 का नाम
Member 9 Designation / सदस्य 9 का पद / दायित्व
Member 10 Name / सदस्य 10 का नाम
Member 10 Designation / सदस्य 10 का पद / दायित्व
Member 11 Name / सदस्य 11 का नाम
Member 11 Designation / सदस्य 11 का पद / दायित्व
processing_status
generated_file
processed_at
error_message
```

---

# 8. Registration Application

## Form identity

**Form name:** `Registration Application Details Form / पंजीयन आवेदन पत्र विवरण फॉर्म`

**Description:**  
`Please fill in the required details carefully for preparing the Registration Application. / कृपया पंजीयन आवेदन पत्र तैयार करने हेतु आवश्यक जानकारी सही-सही भरें।`

**Worksheet:** `Registration Responses`  
**Backend key:** `registration`

## Final fields

| # | Exact Google Form / Sheet column | Type | Required? | Backend parameter |
|---|---|---|---|---|
| 1 | Authority Location / सक्षम प्राधिकारी का स्थान | Short answer | Yes | `authority_location` |
| 2 | Project Name / परियोजना का नाम | Short answer | Yes | `project_name` |
| 3 | Association Address | Paragraph | Yes | `association_address` |
| 4 | Police Station / पुलिस थाना | Short answer | Yes | `police_station` |
| 5 | Association / Society Name / एसोसिएशन / संस्था का नाम | Short answer | Yes | `association_name` |
| 6 | Place / स्थान | Short answer | Yes | `place` |
| 7 | Signatory Name / हस्ताक्षरकर्ता का नाम | Short answer | Yes | `signatory_name` |

### Important Registration rules

- The actual current Sheet header is exactly `Association Address` (English only).
- Do not silently rename it in the adapter.
- Removed:
  - `khasra_number`
  - `project_location`
- No document-date Form field.
- No signatory-designation Form field.
- The template contains fixed designation/date wording.

## Exact expected header sequence

```text
Timestamp
Authority Location / सक्षम प्राधिकारी का स्थान
Project Name / परियोजना का नाम
Association Address
Police Station / पुलिस थाना
Association / Society Name / एसोसिएशन / संस्था का नाम
Place / स्थान
Signatory Name / हस्ताक्षरकर्ता का नाम
processing_status
generated_file
processed_at
error_message
```

---

# 9. By-Law

## Form identity

**Form name:** `By-Law Details Form / उपविधि विवरण फॉर्म`

**Description:**  
`Please fill in the required details carefully for preparing the Association By-Law document. / कृपया संस्था की उपविधि तैयार करने हेतु आवश्यक जानकारी सही-सही भरें।`

**Worksheet:** `By-Law Responses`  
**Backend key:** `by_law`

## Final fields

| # | Exact Google Form / Sheet column | Type | Required? | Backend parameter |
|---|---|---|---|---|
| 1 | Association Name / संस्था का नाम | Short answer | Yes | `association_name` |
| 2 | Association Address / संस्था का पंजीकृत पता | Paragraph | Yes | `association_address` |
| 3 | Work Area / संस्था का कार्यक्षेत्र | Paragraph | Yes | `work_area` |

`association_address` is the complete Khasra + location address.

## Exact expected header sequence

```text
Timestamp
Association Name / संस्था का नाम
Association Address / संस्था का पंजीकृत पता
Work Area / संस्था का कार्यक्षेत्र
processing_status
generated_file
processed_at
error_message
```

---

# 10. Form-A Registration

## Form identity

**Form name:** `Form-A Association Registration Details / संस्था पंजीयन प्रारूप-क विवरण फॉर्म`

**Description:**  
`Please fill in the required details carefully for preparing Form-A registration documents and proceedings. Committee Members 1–5 are mandatory; Members 6–11 are optional. / कृपया संस्था पंजीयन प्रारूप-क एवं कार्यवाही दस्तावेज़ तैयार करने हेतु आवश्यक जानकारी सही-सही भरें। समिति सदस्य 1–5 अनिवार्य हैं तथा सदस्य 6–11 वैकल्पिक हैं।`

**Worksheet:** `Form A Registration Responses`  
**Backend key:** `form_a_registration`

## Main fields

| # | Exact Google Form / Sheet column | Type | Required? | Backend parameter |
|---|---|---|---|---|
| 1 | Association Name / प्रस्तावित संस्था का नाम | Short answer | Yes | `association_name` |
| 2 | Association Address / संस्था का पता | Paragraph | Yes | `association_address` |
| 3 | Work Area / कार्यक्षेत्र | Paragraph | Yes | `work_area` |
| 4 | Share Capital / अंश पूंजी | Short answer | Yes | `share_capital` |
| 5 | Price Per Share / प्रति अंश कीमत | Short answer | Yes | `price_per_share` |
| 6 | Number of Members / सदस्यों की संख्या | Short answer | Yes | `member_count` |
| 7 | Association Email / संस्था ईमेल | Short answer | No | `association_email` |
| 8 | Project Name / परियोजना का नाम | Short answer | Yes | `project_name` |
| 9 | Completion Certificate Number / पूर्णता प्रमाण-पत्र क्रमांक | Short answer | Yes | `completion_certificate_no` |
| 10 | Completion Certificate Date / पूर्णता प्रमाण-पत्र दिनांक | Date | Yes | `completion_certificate_date` |
| 11 | District / जिला | Short answer | Yes | `district_name` |
| 12 | Management Committee Address / प्रबंध कार्यकारिणी का पता | Paragraph | Yes | `management_committee_address` |
| 13 | Meeting Chairperson Name / बैठक अध्यक्ष का नाम | Short answer | Yes | `meeting_chairperson_name` |
| 14 | Proposed By / प्रस्ताव रखने वाले का नाम | Short answer | Yes | `proposed_by` |
| 15 | Approved By / अनुमोदन करने वाले का नाम | Short answer | Yes | `approved_by` |

### Removed Form-A fields

Do not require or restore:

- `khasra_number`
- `project_location`
- `meeting_date`

Meeting date is fixed in the template as exactly:

```text
.............
```

(13 dots)

### Committee members

Each member has four fields:

- Name
- Designation
- Plot Number
- Mobile Number

No separate father-name field. The Name value may already contain father-name text.

No committee-member email field.

#### Members 1–5 — required

For each N = 1..5:

- `Committee Member N Name / समिति सदस्य N का नाम`
- `Committee Member N Designation / समिति सदस्य N का पद`
- `Committee Member N Plot Number / समिति सदस्य N भूखंड क्रमांक`
- `Committee Member N Mobile Number / समिति सदस्य N मोबाइल नंबर`

All four required.

#### Members 6–11 — optional

Same four fields, optional with backend completeness rules:

- all four blank → ignore;
- any field supplied → all four required;
- reject non-contiguous optional members.

Backend constructs:

```python
committee_members = [
    {
        "name": "...",
        "designation": "...",
        "plot_no": "...",
        "mobile": "..."
    },
    ...
]
```

### Derived Form-A values

Do not create duplicate Form questions for:

```text
First Signatory Name
→ committee_members[0].name

First Signatory Mobile
→ committee_members[0].mobile

Authorized Committee President
→ committee_members[0].name
```

### Final association-member table

`member_count` controls the total number of rows.

Validation:

```text
5 <= len(committee_members) <= 11
member_count >= len(committee_members)
```

Rows:

- first `len(committee_members)` rows → committee data;
- remaining rows until `member_count` → blank ordinary-member rows;
- blank rows use designation `सदस्य`.

`share_capital` and `price_per_share` are direct inputs. Do not calculate one from the other.

## Exact expected header sequence

```text
Timestamp
Association Name / प्रस्तावित संस्था का नाम
Association Address / संस्था का पता
Work Area / कार्यक्षेत्र
Share Capital / अंश पूंजी
Price Per Share / प्रति अंश कीमत
Number of Members / सदस्यों की संख्या
Association Email / संस्था ईमेल
Project Name / परियोजना का नाम
Completion Certificate Number / पूर्णता प्रमाण-पत्र क्रमांक
Completion Certificate Date / पूर्णता प्रमाण-पत्र दिनांक
District / जिला
Management Committee Address / प्रबंध कार्यकारिणी का पता
Meeting Chairperson Name / बैठक अध्यक्ष का नाम
Proposed By / प्रस्ताव रखने वाले का नाम
Approved By / अनुमोदन करने वाले का नाम
Committee Member 1 Name / समिति सदस्य 1 का नाम
Committee Member 1 Designation / समिति सदस्य 1 का पद
Committee Member 1 Plot Number / समिति सदस्य 1 भूखंड क्रमांक
Committee Member 1 Mobile Number / समिति सदस्य 1 मोबाइल नंबर
Committee Member 2 Name / समिति सदस्य 2 का नाम
Committee Member 2 Designation / समिति सदस्य 2 का पद
Committee Member 2 Plot Number / समिति सदस्य 2 भूखंड क्रमांक
Committee Member 2 Mobile Number / समिति सदस्य 2 मोबाइल नंबर
Committee Member 3 Name / समिति सदस्य 3 का नाम
Committee Member 3 Designation / समिति सदस्य 3 का पद
Committee Member 3 Plot Number / समिति सदस्य 3 भूखंड क्रमांक
Committee Member 3 Mobile Number / समिति सदस्य 3 मोबाइल नंबर
Committee Member 4 Name / समिति सदस्य 4 का नाम
Committee Member 4 Designation / समिति सदस्य 4 का पद
Committee Member 4 Plot Number / समिति सदस्य 4 भूखंड क्रमांक
Committee Member 4 Mobile Number / समिति सदस्य 4 मोबाइल नंबर
Committee Member 5 Name / समिति सदस्य 5 का नाम
Committee Member 5 Designation / समिति सदस्य 5 का पद
Committee Member 5 Plot Number / समिति सदस्य 5 भूखंड क्रमांक
Committee Member 5 Mobile Number / समिति सदस्य 5 मोबाइल नंबर
Committee Member 6 Name / समिति सदस्य 6 का नाम
Committee Member 6 Designation / समिति सदस्य 6 का पद
Committee Member 6 Plot Number / समिति सदस्य 6 भूखंड क्रमांक
Committee Member 6 Mobile Number / समिति सदस्य 6 मोबाइल नंबर
Committee Member 7 Name / समिति सदस्य 7 का नाम
Committee Member 7 Designation / समिति सदस्य 7 का पद
Committee Member 7 Plot Number / समिति सदस्य 7 भूखंड क्रमांक
Committee Member 7 Mobile Number / समिति सदस्य 7 मोबाइल नंबर
Committee Member 8 Name / समिति सदस्य 8 का नाम
Committee Member 8 Designation / समिति सदस्य 8 का पद
Committee Member 8 Plot Number / समिति सदस्य 8 भूखंड क्रमांक
Committee Member 8 Mobile Number / समिति सदस्य 8 मोबाइल नंबर
Committee Member 9 Name / समिति सदस्य 9 का नाम
Committee Member 9 Designation / समिति सदस्य 9 का पद
Committee Member 9 Plot Number / समिति सदस्य 9 भूखंड क्रमांक
Committee Member 9 Mobile Number / समिति सदस्य 9 मोबाइल नंबर
Committee Member 10 Name / समिति सदस्य 10 का नाम
Committee Member 10 Designation / समिति सदस्य 10 का पद
Committee Member 10 Plot Number / समिति सदस्य 10 भूखंड क्रमांक
Committee Member 10 Mobile Number / समिति सदस्य 10 मोबाइल नंबर
Committee Member 11 Name / समिति सदस्य 11 का नाम
Committee Member 11 Designation / समिति सदस्य 11 का पद
Committee Member 11 Plot Number / समिति सदस्य 11 भूखंड क्रमांक
Committee Member 11 Mobile Number / समिति सदस्य 11 मोबाइल नंबर
processing_status
generated_file
processed_at
error_message
```

---

# 11. Requiredness summary

| Document | Document-input fields | Required | Optional |
|---|---:|---:|---:|
| NOC | 12 | 11 | 1 |
| Affidavit | 14 | 14 | 0 |
| Consent | 35 | 22 | 13 |
| Registration | 7 | 7 | 0 |
| By-Law | 3 | 3 | 0 |
| Form-A Registration | 59 | 34 | 25 |

Notes:

- Consent optional count = Document Date + Member 6–11 pairs.
- Form-A optional count = Association Email + all four fields for Members 6–11.
- Optional grouped-member fields are conditionally complete: partial member rows are invalid.

---

# 12. Migration / removed-field matrix

| Document | Removed old fields | New/current replacement |
|---|---|---|
| NOC | `khasra_number`, `association_location`, `signatory_role` | `association_address`, `project_location`; no signatory role |
| Affidavit | `land_details`, `project_location`, `designation`, `document_date` | `association_address`; fixed designation/date behavior |
| Consent | `society_address`, `survey_numbers` | `project_location`, `association_address`; members expanded to 1–11 |
| Registration | `khasra_number`, `project_location` | `association_address` |
| By-Law | none in current contract | keep three-field contract |
| Form-A | `khasra_number`, `project_location`, `meeting_date` | `association_address`; meeting date fixed as 13 dots |

---

# 13. Codex implementation rules

When implementing or migrating against this specification:

1. Run the complete existing test suite first.
2. Inspect the current template placeholder inventory before changing mappings.
3. Read the live Sheet headers in read-only mode.
4. Implement one document migration at a time.
5. Run focused tests, then the full suite after each document.
6. Do not mutate live Sheets until exact-row approval.
7. Use dry-run before live generation.
8. Do not keep removed fields as required.
9. Do not add new fields for convenience.
10. Do not change By-Law or Form-A behavior unless this spec explicitly says so.
11. Keep registry keys and worksheet names exactly as defined above.
12. Preserve template fonts, spacing, page breaks, tables, and fixed wording.
13. Unknown/unresolved template variables must fail loudly.
14. Dynamic member rows must be validated before rendering.
15. Existing CLI, processor, status contract, and shared Sheets service must be reused.

---

# 14. Read-only validation commands

```bash
.venv/bin/python main.py check-sheets --document noc
.venv/bin/python main.py check-sheets --document affidavit
.venv/bin/python main.py check-sheets --document consent
.venv/bin/python main.py check-sheets --document registration
.venv/bin/python main.py check-sheets --document by_law
.venv/bin/python main.py check-sheets --document form_a_registration
```

After exact candidate rows are identified, use dry-run only until explicitly approved:

```bash
.venv/bin/python main.py generate --document <document-key> --rows <row> --dry-run
```

---

# 15. Final acceptance condition

A document workflow is complete only when all of these are true:

```text
Google Form
→ correct Sheet headers
→ read-only mapping check
→ dry-run
→ approved exact-row live generation
→ generated DOCX visual review
→ correct Sheet status update
→ full offline regression suite passes
```

Do not treat an adapter as production-complete from unit tests alone.
